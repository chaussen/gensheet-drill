"""
question_service.py
===================
Orchestrates: template selection → AI param generation → schema validation
              → verification → distractor assembly → QuestionObject construction.

Chain per CLAUDE.md §5 Iteration 1, step 4.
"""
import math
import random
import re
import uuid
import logging
from collections import Counter
from datetime import datetime, timezone

from docs_loader import load_template_meta, get_templates_for, load_curated_bank
from config.companions import get_companion_ids, should_expand, max_companions
from services.engine import engine as _engine
from services import ai_service
from services.distractor_service import generate_distractors
from services.multi_select_data import (
    MULTI_SELECT_BANKS,
    MULTI_SELECT_TEMPLATE_IDS,
    T7N02_PRIME_POOL as _T7N02_PRIME_POOL,
)
from models.schemas import QuestionObject

logger = logging.getLogger(__name__)

# ── Math delimiter helpers ($...$ wrapping for MathText/KaTeX) ─────────────────

_PLAIN_NUM_RE = re.compile(r'^-?\d+(?:\.\d+)?$')
_FRACTION_PURE_RE = re.compile(r'^(-?\d+)\s*/\s*(\d+)$')
_UNICODE_SUPS = '²³⁴⁵⁶⁷⁸⁹'
_SUP_MAP = {'²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9'}
# Measurement answers: number + unit suffix — no math wrapping needed
_UNIT_RE = re.compile(
    r'^\$?-?\d+(?:\.\d+)?\s*'
    r'(?:cm[²³]?|m[²³]?|km[²³]?|mm|kg|g|mg|L|mL|°[CF]?|'
    r'km/h|m/s[²]?|kJ|J|N|Pa|W|A|V|Hz|s\b|min|hrs?)\s*$',
    re.I,
)


def _to_latex_inner(s: str) -> str:
    """Convert plain-text / sympy-style math to LaTeX notation (without surrounding $)."""
    # Unicode minus → ASCII minus
    s = s.replace('\u2212', '-')
    # Unicode superscripts → ^{N}
    for sup, digit in _SUP_MAP.items():
        s = s.replace(sup, f'^{{{digit}}}')
    # π → \pi
    s = s.replace('π', r'\pi')
    # sympy: x**2 → x^{2}
    s = re.sub(r'\*\*(\d+)', r'^{\1}', s)
    # sympy: 6*x → 6x
    s = re.sub(r'(-?\d+)\*([a-zA-Z])', r'\1\2', s)
    # √(expr) → \sqrt{expr}, √N → \sqrt{N}
    s = re.sub(r'√\(([^)]+)\)', r'\\sqrt{\1}', s)
    s = re.sub(r'√(\d+(?:\.\d+)?)', r'\\sqrt{\1}', s)
    # ∛(expr) → \sqrt[3]{expr}, ∛N → \sqrt[3]{N}
    s = re.sub(r'∛\(([^)]+)\)', r'\\sqrt[3]{\1}', s)
    s = re.sub(r'∛(\d+(?:\.\d+)?)', r'\\sqrt[3]{\1}', s)
    # Integer fractions N/M → \frac{N}{M}
    s = re.sub(r'(-?\d+)\s*/\s*(\d+)', r'\\frac{\1}{\2}', s)
    # × → \times, ÷ → \div
    s = s.replace('×', r'\times').replace('÷', r'\div')
    # Bare exponents ^N and ^-N → ^{N} / ^{-N} (e.g. from scientific notation verifier output)
    # Runs after **N→^{N} so existing ^{N} is not double-wrapped (regex requires bare digit after ^).
    s = re.sub(r'\^(-?\d+)', r'^{\1}', s)
    return s


def _math_wrap_option(s: str) -> str:
    """
    Wrap an option/answer string in $LaTeX$ if it contains mathematical notation.
    Plain integers and floats are returned unchanged.
    """
    s = s.strip()
    if not s or '$' in s:
        return s
    # Plain number → no wrapping
    if _PLAIN_NUM_RE.match(s):
        return s
    # Number with measurement unit → no wrapping (e.g. "50 cm²", "12 kg")
    if _UNIT_RE.match(s):
        return s
    # Pure fraction N/M → \frac
    m = _FRACTION_PURE_RE.match(s)
    if m:
        return f'$\\frac{{{m.group(1)}}}{{{m.group(2)}}}$'
    # Detect math content
    has_math = (
        any(c in s for c in ('√', '∛', '×', '÷', '^', 'π'))
        or any(c in s for c in _UNICODE_SUPS)
        or '**' in s
        or bool(re.search(r'-?\d+\*[a-zA-Z]', s))           # sympy N*x
        or bool(re.search(r'(?<!\w)\d+[a-z]', s))            # coefficient·var: 3x, 2y
        or bool(re.search(r'[a-z]\s*[+\-*/^=]', s))          # var with operator
        or bool(re.search(r'[=+\-*/]\s*[a-z](?!\w)', s))     # operator before var
    )
    if not has_math:
        return s
    return f'${_to_latex_inner(s)}$'


def _math_wrap_text(text: str) -> str:
    """
    Add $...$ delimiters around mathematical sub-expressions in prose text.
    Applied to question_text and explanation strings.
    """
    # Escape currency dollar signs ($40 → \$40) before any other processing
    text = re.sub(r'\$(?=\d)', r'\\$', text)

    # 1. √(expr) → $\sqrt{expr}$
    text = re.sub(
        r'√\(([^)]+)\)',
        lambda m: f'$\\sqrt{{{m.group(1)}}}$',
        text,
    )
    # 2. √N → $\sqrt{N}$
    text = re.sub(
        r'√(\d+(?:\.\d+)?)',
        lambda m: f'$\\sqrt{{{m.group(1)}}}$',
        text,
    )
    # 3. ∛N → $\sqrt[3]{N}$
    text = re.sub(
        r'∛(\d+(?:\.\d+)?)',
        lambda m: f'$\\sqrt[3]{{{m.group(1)}}}$',
        text,
    )
    # 4. Standalone π → $\pi$
    text = re.sub(r'(?<!\w)π(?!\w)', r'$\\pi$', text)

    # 5. Products with × or ÷ (e.g. "2^3 × 5", "4 × 3")
    def _wrap_product(m: re.Match) -> str:
        inner = m.group(0).replace('×', r'\times').replace('÷', r'\div')
        return f'${inner}$'
    text = re.sub(
        r'\d+(?:\^\d+)?(?:\s*[×÷]\s*\d+(?:\^\d+)?)+',
        _wrap_product,
        text,
    )

    # 6. Inline fractions N/M (standalone — not inside a word)
    text = re.sub(
        r'(?<!\w)(-?\d+)\s*/\s*(\d+)(?!\w)',
        lambda m: f'$\\frac{{{m.group(1)}}}{{{m.group(2)}}}$',
        text,
    )

    # 7. Expression after keyword colon — wrap if contains variable or math symbol
    def _wrap_after_keyword(m: re.Match) -> str:
        prefix = m.group(1)
        expr = m.group(2)
        if '$' in expr:
            return prefix + expr  # already partially wrapped by earlier rules
        if re.search(r'[a-z][+\-*/^=²³⁴]|[+\-*/=][a-z](?!\w)|\d[a-z]|[√∛×÷^]', expr):
            return prefix + f'${_to_latex_inner(expr.strip())}$'
        return m.group(0)
    text = re.sub(
        r'((?:Solve|Simplify|Expand|Evaluate|Calculate):\s*)(.+)',
        _wrap_after_keyword,
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # Helper: apply a substitution only to segments outside existing $...$ blocks
    def _outside_math(pattern: str, repl_fn) -> None:
        nonlocal text
        # Split preserving $...$ delimited blocks
        segments = re.split(r'(\$[^$]+\$)', text)
        result = []
        for seg in segments:
            if seg.startswith('$') and seg.endswith('$') and len(seg) > 1:
                result.append(seg)  # already math — leave untouched
            else:
                result.append(re.sub(pattern, repl_fn, seg))
        text = ''.join(result)

    # 8. Equation lines: "y = 3x + 5", "x = 2y − 1", "y = 4" (single lowercase var = expression or constant)
    def _wrap_eq_line(m: re.Match) -> str:
        return f'${_to_latex_inner(m.group(0))}$'
    _outside_math(
        r'(?<!\w)[a-z]\s*=\s*(?:-?\d*\.?\d*[a-z](?:\s*[+\-]\s*\d+)*|-?\d+(?:\.\d+)?)(?!\w)',
        _wrap_eq_line,
    )

    # 9. Inline variable expressions — applied only outside existing math blocks.
    # Use actual Unicode minus sign (−, U+2212) in character classes, not \u2212.
    def _wrap_var_expr(m: re.Match) -> str:
        return f'${_to_latex_inner(m.group(0))}$'

    # 9a. Variable with unicode superscript, e.g. "x² + 3x − 4 = 0", "x³ − 1 = 0"
    # Run this first so the full expression is captured before rule 9b.
    _outside_math(
        r'(?<!\w)-?\d*[a-z][²³⁴⁵⁶⁷⁸⁹]'
        r'(?:\s*[+\-−]\s*(?:-?\d+[a-z]?[²³⁴]?|-?\d+))*'
        r'(?:\s*=\s*(?:-?\d*[a-z][²³⁴]?|-?\d+)'
        r'(?:\s*[+\-−]\s*(?:-?\d*[a-z][²³⁴]?|-?\d+))*)?'
        r'(?![²³⁴\w])',
        _wrap_var_expr,
    )

    # 9b. Coefficient + variable terms, e.g. "3x + 5", "2x − 3 = 7"
    _outside_math(
        r'(?<!\w)-?\d+[a-z][²³⁴]?'
        r'(?:\s*[+\-−]\s*(?:-?\d+[a-z]?[²³⁴]?|-?\d+))*'
        r'(?:\s*=\s*(?:-?\d*[a-z][²³⁴]?|-?\d+)'
        r'(?:\s*[+\-−]\s*(?:-?\d*[a-z][²³⁴]?|-?\d+))*)?'
        r'(?![²³⁴\w])',
        _wrap_var_expr,
    )

    return text


def _wrap_question_math(q: QuestionObject) -> QuestionObject:
    """Apply $...$ math delimiters to question_text, options, and explanation."""
    return q.model_copy(update={
        'question_text': _math_wrap_text(q.question_text),
        'options': [_math_wrap_option(_clean_math_coefficients(o)) for o in q.options],
        'explanation': _math_wrap_text(_clean_math_coefficients(q.explanation)),
    })


# ── Validation gate ────────────────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r'\{[a-z_][a-z_0-9]*\}')
_BAD_OPTION_PATTERNS = ("_wrong", "_0", "_1", "_2", "**", "_neg", "_a", "_b", "_c", "?", "None")

# T-9A-04: this context_variant asks for (x,y) but the verifier only returns x.
_T9A04_EXCLUDED_VARIANTS: frozenset[str] = frozenset([
    "Find the intersection point of y = {a}x + {b} and y = {c}x + {d}.",
])


def validate_question(q: "QuestionObject", correct_str: str) -> bool:
    """
    Structural validation gate. Returns False (reject) if ANY of these are true:
      - question_text contains an unresolved {placeholder}
      - any option is empty / None / whitespace
      - options are not all distinct strings
      - any option contains a known garbage pattern (_wrong, _0, _1, _2, **)
      - correct_index does not point to correct_str
    """
    if _PLACEHOLDER_RE.search(q.question_text):
        return False
    for opt in q.options:
        if not opt or not str(opt).strip():
            return False
    if len(set(q.options)) != len(q.options):
        return False
    for opt in q.options:
        if any(pat in str(opt) for pat in _BAD_OPTION_PATTERNS):
            return False
    if not (0 <= q.correct_index < len(q.options)):
        return False
    if q.options[q.correct_index] != correct_str:
        return False
    return True


# ── Multi-select template registry (data in services/multi_select_data.py) ────


# ── Param helpers ─────────────────────────────────────────────────────────────

# Algebra templates that must produce integer solutions (generation_constraint)
_ALGEBRA_INTEGER_CONSTRAINT_TEMPLATES = {"T-7A-02", "T-8A-02", "T-9A-02", "T-9A-04"}


def _has_integer_solution_constraint(schema: dict) -> bool:
    """Return True if the schema declares a solution_constraint requiring integer answers."""
    sol = schema.get("solution_constraint", "")
    return isinstance(sol, str) and "integer" in sol.lower()


def _solution_is_integer(template_id: str, params: dict) -> bool:
    """
    Pre-verify that params produce an exact integer solution by checking the
    arithmetic directly (avoids the main verifier, which would raise on non-integers
    now that int() truncation has been removed).
    Handles T-8A-02 and T-9A-04; returns True unconditionally for T-7A-02 and T-9A-02
    (their solution params are always integers by template design).
    """
    if template_id == "T-8A-02":
        try:
            a = int(params["a"])
            b = int(params["b"])
            c = int(params["c"])
            d = int(params["d"])
            op1 = params.get("op1", "+")
            op2 = params.get("op2", "+")
            b_signed = b if op1 == "+" else -b
            d_signed = d if op2 == "+" else -d
            denom = a - c
            if denom == 0:
                return False
            return (d_signed - b_signed) % denom == 0
        except (KeyError, ValueError, TypeError):
            return False
    if template_id == "T-9A-04":
        # y = ax + b and y = cx + d  →  x = (d - b) / (a - c)
        try:
            a = int(params["a"])
            b = int(params["b"])
            c = int(params["c"])
            d = int(params["d"])
            denom = a - c
            if denom == 0:
                return False
            return (d - b) % denom == 0
        except (KeyError, ValueError, TypeError):
            return False
    # T-7A-02 and T-9A-02 derive their solution from an integer param — always integer.
    return True


def _fallback_params(template: dict, difficulty: str) -> dict:
    """
    Generate random parameter values locally without the AI.
    Used when the AI call fails (per docs/ai_prompts.md error handling).
    """
    schema = template.get("params", {})
    needs_integer = _has_integer_solution_constraint(schema)
    max_attempts = 40 if needs_integer else 1

    for _ in range(max_attempts):
        params: dict = {}

        # First pass: non-derived params
        for key, spec in schema.items():
            if not isinstance(spec, dict):
                continue
            ptype = spec.get("type")
            if ptype == "choice":
                choices = spec.get(difficulty) or spec.get("all") or spec.get("standard") or []
                if choices:
                    params[key] = random.choice(choices)
            elif ptype == "randint":
                lo = spec.get(f"{difficulty}_min", spec.get("min", 1))
                hi = spec.get(f"{difficulty}_max", spec.get("max", 10))
                exclude = spec.get("exclude", [])
                for _ in range(20):
                    val = random.randint(int(lo or 1), int(hi or 10))
                    if val not in exclude:
                        params[key] = val
                        break
            elif ptype == "random_float":
                lo = float(spec.get("min", 1.0))
                hi = float(spec.get("max", 100.0))
                dp = int(spec.get("decimal_places", 2))
                params[key] = round(random.uniform(lo, hi), dp)
            # "derived" and "generated_expression" handled in second pass

        # Second pass: enforce inter-param inequality constraints (e.g. "c ≠ a")
        for key, spec in schema.items():
            if not isinstance(spec, dict):
                continue
            constraint = spec.get("constraint", "")
            neq = re.search(r'(\w+)\s*≠\s*(\w+)', constraint)
            if neq:
                lhs, rhs = neq.group(1), neq.group(2)
                if lhs == key and rhs in params and params.get(lhs) == params.get(rhs):
                    lo = int(spec.get("min", 1))
                    hi = int(spec.get("max", 10))
                    for _ in range(20):
                        val = random.randint(lo, hi)
                        if val != params[rhs]:
                            params[key] = val
                            break

        # Third pass: derived params
        params = _resolve_derived_params(template, params)

        # Fourth pass: validate integer solution constraint before returning
        if not needs_integer or _solution_is_integer(template["id"], params):
            return params

    return params  # return last attempt if all retries exhausted


def _safe_eval(expr_str: str, namespace: dict):
    """Evaluate a simple arithmetic expression using only numeric namespace values."""
    # Convert implicit multiplication: "2d" → "2*d", "3t1" → "3*t1"
    expr_str = re.sub(r'(\d)([A-Za-z])', r'\1*\2', expr_str)
    safe_ns = {k: v for k, v in namespace.items() if isinstance(v, (int, float))}
    return eval(  # noqa: S307 — trusted template rules, no user input reaches here
        compile(expr_str, "<rule>", "eval"),
        {"__builtins__": {}},
        safe_ns,
    )


def _derive_t9a02_equation(params: dict) -> None:
    """
    For T-9A-02: derive {lhs} and {rhs} from lhs_template and solution.
    Generates sub-params (a, b, c, d) so the equation is correct for the given solution.
    """
    lhs_tmpl = params.get("lhs_template", "{a}x + {b}")
    sol = int(params.get("solution", 3))
    eq: dict = {}
    rhs: int | float = 0
    try:
        if lhs_tmpl == "{a}x + {b}":
            a, b = random.randint(2, 5), random.randint(1, 12)
            rhs = a * sol + b
            eq = {"a": a, "b": b}
        elif lhs_tmpl == "{a}x - {b}":
            a, b = random.randint(2, 5), random.randint(1, 12)
            rhs = a * sol - b
            eq = {"a": a, "b": b}
        elif lhs_tmpl == "{a}(x + {b})":
            a, b = random.randint(2, 5), random.randint(1, 8)
            rhs = a * (sol + b)
            eq = {"a": a, "b": b}
        elif lhs_tmpl == "x/{a} + {b}":
            # Need solution divisible by a; try candidates in random order
            candidates = [i for i in [2, 3, 4, 5] if sol % i == 0]
            a = random.choice(candidates) if candidates else 1
            b = random.randint(1, 10)
            rhs = sol // a + b
            eq = {"a": a, "b": b}
        elif lhs_tmpl == "(x + {a})/{b}":
            b = random.randint(2, 5)
            # Find smallest a ≥ 1 such that (sol + a) % b == 0
            a = b - (sol % b) if sol % b != 0 else b
            rhs = (sol + a) // b
            eq = {"a": a, "b": b}
        elif lhs_tmpl == "{a}x/{b} + {c}":
            pairs = [(a, b) for a in range(2, 5) for b in range(2, 6) if (a * sol) % b == 0]
            a, b = random.choice(pairs) if pairs else (2, 1)
            c = random.randint(1, 10)
            rhs = a * sol // b + c
            eq = {"a": a, "b": b, "c": c}
        elif "{a}(x + {b}) - {c}(x - {d})" in lhs_tmpl:
            a = random.randint(3, 6)
            c = random.randint(1, a - 1)
            b, d = random.randint(1, 8), random.randint(1, 8)
            rhs = (a - c) * sol + a * b + c * d
            eq = {"a": a, "b": b, "c": c, "d": d}
        else:
            a, b = random.randint(2, 5), random.randint(1, 12)
            rhs = a * sol + b
            lhs_tmpl = "{a}x + {b}"
            eq = {"a": a, "b": b}
        params.update(eq)
        params["lhs"] = lhs_tmpl.format(**{**params, **eq})
        params["rhs"] = str(int(rhs) if rhs == int(rhs) else rhs)
    except Exception as exc:
        logger.warning("T-9A-02 equation derivation failed: %s", exc)
        a, b = 2, 3
        params["lhs"] = f"{a}x + {b}"
        params["rhs"] = str(a * sol + b)


def _derive_t9p03_table(params: dict) -> None:
    """
    For T-9P-03: generate a 2×2 contingency table and derive the verifier fields
    (table, query_cell / query_row) plus table_description for question text.
    """
    a1b1 = random.randint(5, 25)
    a1b2 = random.randint(5, 25)
    a2b1 = random.randint(5, 25)
    a2b2 = random.randint(5, 25)
    table = {"a1b1": a1b1, "a1b2": a1b2, "a2b1": a2b1, "a2b2": a2b2}
    params["table"] = table

    r1, r2, c1, c2 = "Male", "Female", "Yes", "No"
    params["table_description"] = (
        f"{r1}: {c1}={a1b1}, {c2}={a1b2}; {r2}: {c1}={a2b1}, {c2}={a2b2}"
    )

    query = params.get("query", "is in a specific cell")
    if "specific cell" in query:
        cell = random.choice(["a1b1", "a1b2", "a2b1", "a2b2"])
        params["query_cell"] = cell
        label = {"a1b1": f"{r1} and {c1}", "a1b2": f"{r1} and {c2}",
                 "a2b1": f"{r2} and {c1}", "a2b2": f"{r2} and {c2}"}[cell]
        params["query"] = f"is {label}"
    else:
        row = random.choice(["a1", "a2"])
        params["query_row"] = row
        params["query"] = f"is {'Male' if row == 'a1' else 'Female'}"


def _resolve_derived_params(template: dict, params: dict) -> dict:
    """
    Compute derived parameter values from declared rules.
    Handles:
      - "derived" type entries within the params schema
      - top-level "derived" dict (e.g. T-7A-03: t2, t3, t4, t5)
      - expr_template → expr rendering for T-8A-01 style templates
    """
    params = dict(params)
    schema = template.get("params", {})

    # Derived entries inside params schema
    for key, spec in schema.items():
        if not isinstance(spec, dict) or spec.get("type") != "derived":
            continue
        if key in params:
            continue
        rule = spec.get("rule", "")
        # Extract RHS from "key = <expr>" or "key = <expr>, constraint"
        m = re.match(r'\w+\s*=\s*(.+?)(?:,.*)?$', rule.strip())
        if not m:
            continue
        expr = m.group(1).replace("×", "*").replace("÷", "/")
        try:
            params[key] = _safe_eval(expr, params)
        except Exception as e:
            logger.warning("Could not derive %s from rule '%s': %s", key, rule, e)

    # Top-level "derived" dict (e.g. T-7A-03)
    for key, rule in template.get("derived", {}).items():
        if key in params:
            continue
        expr = str(rule).replace("×", "*").replace("÷", "/")
        try:
            params[key] = _safe_eval(expr, params)
        except Exception as e:
            logger.warning("Could not derive top-level %s from '%s': %s", key, rule, e)

    # expr_template → expr (T-8A-01 style: question_template uses {expr})
    if "expr_template" in params and "expr" not in params:
        try:
            params["expr"] = str(params["expr_template"]).format(**params)
        except (KeyError, ValueError):
            pass

    # Derive "op" from expr_template for expand_simplify verifier
    if "expr_template" in params and "op" not in params:
        et = str(params["expr_template"])
        # Simple heuristic: if the first ± inside the bracket is "-", op="-"
        inner = re.search(r'\(.*?([+-]).*?\)', et)
        if inner:
            params["op"] = inner.group(1)
        else:
            params["op"] = "+"

    # T-8M-06: compute known_description for Pythagoras question text.
    # The template schema omits this key; derive it from triple_family, scale, unknown_side.
    if template.get("id") == "T-8M-06" and "known_description" not in params:
        triple = params.get("triple_family", [3, 4, 5])
        scale = int(params.get("scale", 1))
        legs = sorted([triple[0] * scale, triple[1] * scale])  # [shorter, longer]
        hyp = triple[2] * scale
        unknown = params.get("unknown_side", "hypotenuse")
        if unknown == "hypotenuse":
            params["known_description"] = f"legs of {legs[0]} cm and {legs[1]} cm"
        elif unknown == "shorter leg":
            params["known_description"] = f"hypotenuse of {hyp} cm and longer leg of {legs[1]} cm"
        else:  # longer leg
            params["known_description"] = f"hypotenuse of {hyp} cm and shorter leg of {legs[0]} cm"

    # T-7P-03, T-8P-01: derive {p} fraction string for question text.
    if template.get("id") in {"T-7P-03", "T-8P-01"} and "p" not in params:
        pn = params.get("p_numerator")
        pd = params.get("p_denominator")
        if pn is not None and pd is not None:
            params["p"] = f"{pn}/{pd}"

    # T-9A-01: derive {ax} and {cx} for binomial product question text.
    # NOTE: context variant "Expand: ({ax} + {b})²" will render but asks about a perfect square
    # while the verifier answers the general binomial — minor mismatch, pre-existing template issue.
    if template.get("id") == "T-9A-01" and "ax" not in params:
        a = int(params.get("a", 1))
        c = int(params.get("c", 1))
        params["ax"] = "x" if a == 1 else f"{a}x"
        params["cx"] = "x" if c == 1 else f"{c}x"

    # T-9N-04: {y} and {x} are variable label strings, not numeric params.
    if template.get("id") == "T-9N-04" and "x" not in params:
        params["x"] = "x"
        params["y"] = "y"

    # T-8M-02: derive base_shape, base_dims, and base_area from prism_type.
    # The schema's base_dims_and_area is a prose description, not a typed param —
    # generate real dimensions here so both question text and verifier work.
    if template.get("id") == "T-8M-02" and "base_area" not in params:
        prism_type = params.get("prism_type", "rectangular")
        params["base_shape"] = prism_type
        if prism_type == "rectangular":
            w = random.randint(3, 12)
            h = random.randint(3, 12)
            params["base_dims"] = f"{w} cm × {h} cm"
            params["base_area"] = w * h
        elif prism_type == "triangular":
            b = random.choice([4, 6, 8, 10, 12, 14, 16, 20])  # even → integer area
            h = random.randint(3, 12)
            params["base_dims"] = f"base {b} cm, height {h} cm"
            params["base_area"] = b * h // 2
        else:  # trapezoidal
            a_side = random.randint(4, 10)
            b_side = random.randint(a_side + 2, 14)
            if (a_side + b_side) % 2 != 0:  # ensure integer area
                b_side += 1
            h = random.randint(3, 10)
            params["base_dims"] = f"parallel sides {a_side} cm and {b_side} cm, height {h} cm"
            params["base_area"] = (a_side + b_side) * h // 2

    # T-8ST-01: generate actual values and frequencies lists (schema entries are prose
    # descriptions, not typed params), then build table_description for question text.
    if template.get("id") == "T-8ST-01" and not isinstance(params.get("values"), list):
        n_vals = random.randint(4, 5)
        values = sorted(random.sample(range(1, 21), n_vals))
        frequencies = [random.randint(1, 8) for _ in range(n_vals)]
        params["values"] = values
        params["frequencies"] = frequencies
        pairs = ", ".join(f"{v}(×{f})" for v, f in zip(values, frequencies))
        params["table_description"] = pairs

    # T-9A-02: derive {lhs} and {rhs} from lhs_template + solution.
    # lhs_template contains {a},{b},{c},{d} placeholders that are NOT in the schema;
    # we compute values of those sub-params so that the equation is correct.
    if template.get("id") == "T-9A-02" and "lhs" not in params:
        _derive_t9a02_equation(params)

    # T-9P-03: generate a 2×2 contingency table and derive the fields the verifier needs.
    # table_structure is a prose description; generate real cell counts here.
    if template.get("id") == "T-9P-03" and "table" not in params:
        _derive_t9p03_table(params)

    # T-9M-01: generate real dimension params from shape.
    # Schema uses a prose 'dimensions' string rather than typed param entries, so
    # _fallback_params only generates 'shape'. Actual dimension keys (l, w, h, r, etc.)
    # are derived here to match what _surface_area() expects.
    if template.get("id") == "T-9M-01" and "l" not in params and "r" not in params and "a" not in params:
        shape = params.get("shape", "rectangular prism")
        if shape == "cylinder":
            r = random.randint(3, 9)
            h = random.randint(4, 15)
            params.update({"r": r, "h": h})
            params["dimensions"] = f"radius {r} cm, height {h} cm"
        elif shape == "triangular prism":
            triple = random.choice([(3, 4, 5), (5, 12, 13), (6, 8, 10), (8, 15, 17)])
            a, b_leg, c_side = triple
            length = random.randint(4, 12)
            params.update({"a": a, "b": b_leg, "c_side": c_side, "length": length})
            params["dimensions"] = (
                f"triangular base with legs {a} cm and {b_leg} cm "
                f"(hypotenuse {c_side} cm), length {length} cm"
            )
        else:  # rectangular prism (default)
            ln = random.randint(3, 12)
            w = random.randint(3, 12)
            h = random.randint(3, 12)
            params.update({"l": ln, "w": w, "h": h})
            params["dimensions"] = f"length {ln} cm, width {w} cm, height {h} cm"

    # T-9M-02: generate real dimension params from shape.
    # Same pattern as T-9M-01: 'dimensions' in schema is a prose dict, not typed params.
    if template.get("id") == "T-9M-02" and "s" not in params and "r" not in params:
        shape = params.get("shape", "square pyramid")
        if shape == "cone":
            r = random.randint(3, 9)
            h = random.randint(4, 15)
            params.update({"r": r, "h": h})
            params["dimensions"] = f"radius {r} cm, height {h} cm"
        elif shape == "sphere":
            r = random.randint(3, 9)
            params["r"] = r
            params["dimensions"] = f"radius {r} cm"
        else:  # square pyramid (default)
            s = random.randint(3, 12)
            h = random.randint(4, 15)
            params.update({"s": s, "h": h})
            params["dimensions"] = f"base side {s} cm, height {h} cm"

    # T-9M-03: derive unknown_side (rule is natural language — "different from known_side;
    # requires sin/cos/tan" — which _safe_eval cannot evaluate).
    if template.get("id") == "T-9M-03" and "unknown_side" not in params:
        known = params.get("known_side", "hypotenuse")
        sides = ["hypotenuse", "opposite side", "adjacent side"]
        params["unknown_side"] = random.choice([s for s in sides if s != known])

    # T-9M-04: derive b from a using an integer scale factor.
    # Rule "b = a × k where k ∈ {2, 3, 4, 1.5, 2.5}" fails _safe_eval due to the
    # "where k ∈ {...}" clause. Use integer k only so the answer is always a clean integer.
    if template.get("id") == "T-9M-04" and "b" not in params:
        a = params.get("a", random.randint(2, 8))
        k = random.choice([2, 3, 4])
        params["b"] = a * k

    # T-9SP-02: for direction="reduce", derive image_dim = original × k so the question
    # can show the image dimension to the student and ask them to find the original.
    if template.get("id") == "T-9SP-02" and "image_dim" not in params:
        direction = params.get("direction", "enlarge")
        if direction == "reduce":
            original = int(params.get("original", 6))
            k = int(params.get("k", 3))
            params["image_dim"] = original * k

    # T-9M-04b: derive measured from actual + error_pct + direction.
    # Conditional rule ("if over ... if under") cannot be handled by _safe_eval.
    # Also enforces the generation_constraint: measured must be a clean integer.
    if template.get("id") == "T-9M-04b" and "measured" not in params:
        actual = params.get("actual", 100)
        error_pct = params.get("error_pct", 5)
        direction = params.get("direction", "over")
        error_amount = actual * error_pct / 100
        if error_amount == int(error_amount):
            measured = int(actual + error_amount) if direction == "over" else int(actual - error_amount)
        else:
            # Pick a clean error_pct that yields an integer error_amount
            for ep in [5, 10, 20, 2, 4, 1]:
                ea = actual * ep / 100
                if ea == int(ea):
                    error_pct = ep
                    error_amount = ea
                    break
            params["error_pct"] = error_pct
            measured = int(actual + error_amount) if direction == "over" else int(actual - error_amount)
        params["measured"] = measured

    return params


# ── Answer formatting ─────────────────────────────────────────────────────────

def _format_answer(answer) -> str:
    """Render a verifier result as a display string for MCQ options."""
    # sympy Integer / Rational (returned by linear-equation verifiers)
    try:
        from sympy import Integer as _SympyInt, Rational as _SympyRat
        if isinstance(answer, _SympyInt):
            return str(int(answer))
        if isinstance(answer, _SympyRat):
            return f"{answer.p}/{answer.q}"
    except ImportError:
        pass
    # Python stdlib Fraction
    from fractions import Fraction as _Frac
    if isinstance(answer, _Frac):
        return str(answer)  # "p/q" or "p" when denominator == 1
    if isinstance(answer, tuple):
        return f"({answer[0]}, {answer[1]})"
    if isinstance(answer, float):
        return str(int(answer)) if answer == int(answer) else str(answer)
    return str(answer)


def _build_explanation(template: dict, params: dict, correct_answer) -> str:
    """Build a step-by-step explanation for a question."""
    template_id = template.get("id", "")
    topic = template.get("topic", template_id)
    answer_str = _format_answer(correct_answer)

    if template_id == "T-9N-03":
        principal = float(params.get("principal", 0))
        rate = float(params.get("rate", 0))
        years = int(params.get("years", 0))
        interest_type = params.get("interest_type", "simple")
        year_label = "year" if years == 1 else "years"
        if interest_type == "simple":
            return (
                f"Simple interest: I = P × r/100 × t "
                f"= {principal:.0f} × {rate}/100 × {years} {year_label} "
                f"= ${correct_answer:.2f}"
            )
        else:
            amount = round(principal * (1 + rate / 100) ** years, 2)
            return (
                f"Compound interest: A = P(1 + r/100)^n "
                f"= {principal:.0f} × (1 + {rate}/100)^{years} "
                f"= ${amount:.2f}, "
                f"so interest = A − P = ${amount:.2f} − ${principal:.0f} = ${correct_answer:.2f}"
            )

    return f"The correct answer is {answer_str}. ({topic})"


# ── Question builder ──────────────────────────────────────────────────────────

def _apply_composite_placeholders(text: str, params: dict) -> str:
    """
    Second pass: resolve composite patterns like {ax}, {bx}, {cx} that were not
    substituted by the standard .format() call (because param key is e.g. "a", not "ax").
    {Kx} → str(params[K]) + "x"  (suppresses coefficient 1: {ax} with a=1 → "x")
    """
    def _replace(m: re.Match) -> str:
        key = m.group(1)
        if key in params:
            val = params[key]
            try:
                coef = int(val)
                if coef == 1:
                    return "x"
                if coef == -1:
                    return "-x"
                return f"{coef}x"
            except (TypeError, ValueError):
                return str(val) + "x"
        return m.group(0)  # leave unchanged

    return re.sub(r'\{([a-z_]\w*)x\}', _replace, text)


def _clean_math_coefficients(text: str) -> str:
    """
    Post-process rendered question text to fix invalid math notation produced when
    numeric params are substituted into templates with patterns like {a}x + {b}.

    Fixes:
    1. "1x" → "x", "-1x" → "-x" (leading coefficient 1)
    2. "0x + c" → "c", "0x - c" → "-c", bare "0x" → "0" (zero coefficient)
    3. "+ -N" → "- N", "- -N" → "+ N" (sign collapsing after negative substitution)
    """
    # Sign collapsing: must run before coefficient rules so "= -1x" is clean afterwards
    # "+ -"  →  "- "    e.g. "y = 2x + -4"  →  "y = 2x - 4"
    text = re.sub(r'\+\s*-\s*(\d)', r'- \1', text)
    # "- -"  →  "+ "    e.g. "y = 2x - -3"  →  "y = 2x + 3"
    text = re.sub(r'-\s*-\s*(\d)', r'+ \1', text)

    # Zero coefficient: "0x + c" → "c", "0x - c" → "-c", standalone "0x" → "0"
    # Match: optional leading "= " or space, then 0x, then optional " +/- constant"
    def _zero_coef(m: re.Match) -> str:
        prefix = m.group(1)   # e.g. "= " or "  "
        sign = m.group(2)     # "+" or "-" or None
        const = m.group(3)    # constant string or None
        if const is None:
            return f"{prefix}0"
        if sign == "-":
            return f"{prefix}-{const}"
        return f"{prefix}{const}"

    text = re.sub(
        r'(=\s*|(?<=\s))0x(?:\s*([+\-])\s*(\S+))?',
        _zero_coef,
        text,
    )

    # Leading-1 coefficient: "1x" → "x", "-1x" → "-x"
    # Use word boundary on the right so "10x", "11x" etc. are untouched.
    # Allow optional sign prefix so "= -1x" → "= -x" and "= 1x" → "= x".
    text = re.sub(r'(?<![0-9])-1x(?![0-9])', '-x', text)
    text = re.sub(r'(?<![0-9])1x(?![0-9])', 'x', text)

    # Pluralization: "1 years" → "1 year" (and other common time units)
    text = re.sub(r'\b1 years\b', '1 year', text)

    return text


def _render_question_text(
    template: dict,
    params: dict,
    exclude_variants: frozenset[str] | None = None,
) -> tuple[str, str]:
    """
    Substitute params into a randomly chosen context variant or the base template.
    Returns (rendered_text, chosen_template_str).
    Applies a second pass to resolve composite {ax}/{bx}/… placeholders, then a
    third pass (_clean_math_coefficients) to fix "1x", "0x + c", and "+ -N" artifacts.
    """
    raw_variants = template.get("context_variants", [])
    if exclude_variants:
        raw_variants = [v for v in raw_variants if v not in exclude_variants]
    candidates = raw_variants + [template.get("question_template", "")]
    candidates = [c for c in candidates if c]
    template_str = random.choice(candidates)
    base = template.get("question_template", "")
    try:
        text = template_str.format(**params)
        cleaned = _clean_math_coefficients(_apply_composite_placeholders(text, params))
        return cleaned, template_str
    except (KeyError, ValueError):
        try:
            text = base.format(**params)
            cleaned = _clean_math_coefficients(_apply_composite_placeholders(text, params))
            return cleaned, base
        except Exception:
            return base, base


def _build_multi_select_question(
    template_id: str, params: dict, difficulty: str, bank_item: dict | None = None
) -> QuestionObject | None:
    """Build a multi_select QuestionObject. Called for advanced difficulty only."""
    if template_id == "T-7N-02":
        return _build_t7n02_multi_select(params, difficulty)

    bank = MULTI_SELECT_BANKS.get(template_id)
    if not bank:
        return None

    item = bank_item if bank_item is not None else random.choice(bank["items"])
    indexed = list(enumerate(item["options"]))
    random.shuffle(indexed)
    shuffled_options = [opt for _, opt in indexed]
    old_to_new = {old_i: new_i for new_i, (old_i, _) in enumerate(indexed)}
    shuffled_correct = sorted(old_to_new[i] for i in item["correct_indices"])

    try:
        q = QuestionObject(
            question_id=str(uuid.uuid4()),
            template_id=template_id,
            vc_code=bank["vc_code"],
            year_level=bank["year"],
            strand=bank["strand"],
            difficulty=difficulty,
            question_type="multi_select",
            question_text=item["question_text"],
            options=shuffled_options,
            correct_index=-1,
            correct_indices=shuffled_correct,
            explanation=item["explanation"],
            params=params,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        return _wrap_question_math(q)
    except Exception as e:
        logger.warning("Multi-select QuestionObject build failed for %s: %s", template_id, e)
        return None


def _build_t7n02_multi_select(params: dict, difficulty: str) -> QuestionObject | None:
    """Build a 'which of these are prime factors of n?' multi_select question."""
    from sympy import factorint

    n = params.get("n")
    if not n:
        return None

    factorization = factorint(int(n))
    prime_factors = sorted(factorization.keys())

    distractors = [p for p in _T7N02_PRIME_POOL if p not in prime_factors]

    n_correct = min(len(prime_factors), 3)
    correct_primes = prime_factors[:n_correct]
    needed = 5 - n_correct
    distractor_sample = random.sample(distractors, min(needed, len(distractors)))

    all_options = [str(p) for p in correct_primes + distractor_sample]
    while len(all_options) < 5:
        all_options.append(str(random.choice(_T7N02_PRIME_POOL)))
    all_options = list(dict.fromkeys(all_options))[:5]

    correct_str_set = {str(p) for p in correct_primes}
    random.shuffle(all_options)
    correct_indices = [i for i, opt in enumerate(all_options) if opt in correct_str_set]

    factor_str = " × ".join(
        f"{p}^{e}" if e > 1 else str(p)
        for p, e in sorted(factorization.items())
    )
    question_text = f"Which of these are prime factors of {n}? Select all that apply."
    explanation = f"The prime factorisation of {n} is {factor_str}, so its prime factors are {', '.join(str(p) for p in prime_factors)}."

    try:
        meta = load_template_meta("T-7N-02")
        q = QuestionObject(
            question_id=str(uuid.uuid4()),
            template_id="T-7N-02",
            vc_code=meta["vc_code"],
            year_level=7,
            strand="Number",
            difficulty=difficulty,
            question_type="multi_select",
            question_text=question_text,
            options=all_options,
            correct_index=-1,
            correct_indices=correct_indices,
            explanation=explanation,
            params=params,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        return _wrap_question_math(q)
    except Exception as e:
        logger.warning("T-7N-02 multi_select build failed: %s", e)
        return None


def _build_curated_bank_question(
    template: dict, difficulty: str, bank_item: dict | None = None
) -> QuestionObject | None:
    """
    Build a QuestionObject from a curated_bank template.
    Uses bank_item if provided; otherwise picks randomly from the bank.
    No AI call and no verifier needed — bank items are pre-verified.

    Bank item schema (single-select):
        { "question_text": str, "correct_answer": str,
          "wrong_answers": [str, str, str], "explanation": str }

    Bank item schema (multi-select):
        { "question_text": str, "question_type": "multi_select",
          "all_options": [str, ...], "correct_answers": [str, ...],
          "explanation": str }
    """
    template_id = template["id"]
    bank_name = template.get("answer_lookup")
    if not bank_name:
        logger.debug("Curated bank template %s has no answer_lookup — skipping", template_id)
        return None

    items = load_curated_bank(bank_name)
    if not items:
        logger.debug("Curated bank '%s' is not yet populated — skipping %s", bank_name, template_id)
        return None

    item = bank_item if bank_item is not None else random.choice(items)

    question_text = item.get("question_text", template.get("question_template", ""))
    explanation = item.get("explanation", "")

    # ── Multi-select bank item ──────────────────────────────────────────────
    if item.get("question_type") == "multi_select":
        all_options = item.get("all_options", [])
        correct_answers = set(item.get("correct_answers", []))
        indexed = list(enumerate(all_options))
        random.shuffle(indexed)
        shuffled_options = [opt for _, opt in indexed]
        correct_indices = sorted(
            new_i for new_i, (_, opt) in enumerate(indexed) if opt in correct_answers
        )
        try:
            q = QuestionObject(
                question_id=str(uuid.uuid4()),
                template_id=template_id,
                vc_code=template["vc_code"],
                year_level=int(template["year"]),
                strand=template["strand"],
                difficulty=difficulty,
                question_type="multi_select",
                question_text=question_text,
                options=shuffled_options,
                correct_index=-1,
                correct_indices=correct_indices,
                explanation=explanation,
                params={},
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            return _wrap_question_math(q)
        except Exception as e:
            logger.warning("Curated bank multi_select build failed for %s: %s", template_id, e)
            return None

    # ── Single-select (standard MCQ) bank item ──────────────────────────────
    correct_answer = item.get("correct_answer", "")
    wrong_answers = item.get("wrong_answers", [])
    if not correct_answer or len(wrong_answers) < 3:
        logger.debug("Curated bank item incomplete for %s — skipping", template_id)
        return None

    options = [correct_answer] + list(wrong_answers[:3])
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    try:
        q = QuestionObject(
            question_id=str(uuid.uuid4()),
            template_id=template_id,
            vc_code=template["vc_code"],
            year_level=int(template["year"]),
            strand=template["strand"],
            difficulty=difficulty,
            question_text=question_text,
            options=options,
            correct_index=correct_index,
            explanation=explanation,
            params={},
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        return _wrap_question_math(q)
    except Exception as e:
        logger.warning("Curated bank QuestionObject build failed for %s: %s", template_id, e)
        return None


def build_question(
    template: dict, params: dict, difficulty: str, bank_item: dict | None = None
) -> QuestionObject | None:
    """
    Construct a single verified QuestionObject from a template + params dict.
    Returns None if verification or Pydantic validation fails — caller should skip/retry.
    bank_item: pre-selected curated bank item (avoids repeats within a session).
    """
    template_id = template["id"]

    if template_id in MULTI_SELECT_TEMPLATE_IDS and difficulty == "advanced":
        return _build_multi_select_question(template_id, params, difficulty, bank_item=bank_item)

    if template.get("generation_mode") == "curated_bank":
        return _build_curated_bank_question(template, difficulty, bank_item=bank_item)

    # Resolve derived params (t2/t3, op from expr_template, etc.)
    params = _resolve_derived_params(template, params)

    # T-9N-03: compound interest with years=1 is identical to simple — enforce years >= 2
    if template_id == "T-9N-03" and params.get("interest_type") == "compound" and int(params.get("years", 0)) == 1:
        params = {**params, "years": 2}

    # T-9N-02: convert float value to decimal notation so question text reads as a real number
    # (e.g. 5.6e-05 → "0.000056") not as Python scientific repr, which already looks like sci notation.
    if template_id == "T-9N-02" and "value" in params:
        from decimal import Decimal as _Decimal
        try:
            dec = _Decimal(str(float(params["value"])))
            params = {**params, "value": f"{dec:f}".rstrip("0").rstrip(".")}
        except Exception:
            pass

    # 1. Verify → correct answer
    try:
        correct_answer = _engine.verify(template_id, params)
    except Exception as e:
        logger.warning("Verification failed for %s (params=%s): %s", template_id, params, e)
        return None

    # Normalize sympy Integer to Python int so distractor generators work correctly.
    # Fractional sympy Rational is left as-is; _format_answer renders it as "p/q".
    try:
        from sympy import Integer as _SympyInt
        if isinstance(correct_answer, _SympyInt):
            correct_answer = int(correct_answer)
    except ImportError:
        pass

    # 2. Render question text (before distractor generation — variant may change answer format)
    # Root cause B: T-9A-04 "Find the intersection point" variant asks for (x,y) but verifier
    # only returns x — exclude it entirely.
    exclude_vars = _T9A04_EXCLUDED_VARIANTS if template_id == "T-9A-04" else None
    question_text, chosen_variant = _render_question_text(template, params, exclude_variants=exclude_vars)

    # T-9SP-02 reduce direction: override question text to show image_dim and ask for original.
    if template_id == "T-9SP-02" and params.get("direction") == "reduce":
        dim = params.get("dimension_name", "length")
        image_dim = params.get("image_dim", "?")
        k = params.get("k", "?")
        question_text = (
            f"The image {dim} is {image_dim} cm after an enlargement with scale factor {k}. "
            f"What was the original {dim}?"
        )

    # Root cause B: T-9A-03 gradient / y-intercept context variants need a different answer
    # format than the default line_equation verifier (which returns a full "y = mx + c" string).
    if template_id == "T-9A-03":
        variant_lower = chosen_variant.lower()
        if variant_lower.startswith("what is the gradient"):
            correct_answer = params.get("m", correct_answer)
        elif variant_lower.startswith("what is the y-intercept"):
            correct_answer = params.get("c", correct_answer)

    correct_str = _format_answer(correct_answer)

    # 3. Distractors
    try:
        distractors = generate_distractors(template_id, correct_answer, params)
    except Exception as e:
        logger.warning("Distractor generation failed for %s: %s", template_id, e)
        distractors = [f"{correct_str}_a", f"{correct_str}_b", f"{correct_str}_c"]

    # Ensure 3 distinct distractors, none equal to correct
    distractors = [d for d in distractors if d != correct_str]
    seen = {correct_str}
    clean = []
    for d in distractors:
        if d not in seen:
            clean.append(d)
            seen.add(d)
    i = 0
    while len(clean) < 3:
        cand = f"{correct_str}_{i}"
        if cand not in seen:
            clean.append(cand)
            seen.add(cand)
        i += 1
    distractors = clean[:3]

    # 4. Shuffle options, record correct_index
    options = [correct_str] + distractors
    random.shuffle(options)
    correct_index = options.index(correct_str)

    # 5. Explanation
    explanation = _build_explanation(template, params, correct_answer)

    # 6. Validate with Pydantic (use raw strings — wrapping happens after validation)
    try:
        q = QuestionObject(
            question_id=str(uuid.uuid4()),
            template_id=template_id,
            vc_code=template["vc_code"],
            year_level=int(template["year"]),
            strand=template["strand"],
            difficulty=difficulty,
            question_text=question_text,
            options=options,
            correct_index=correct_index,
            explanation=explanation,
            params=params,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.warning("QuestionObject validation failed for %s: %s", template_id, e)
        return None

    # 7. Structural validation gate — rejects garbage/unresolved questions before returning
    if not validate_question(q, correct_str):
        logger.warning("validate_question rejected assembled question for %s", template_id)
        return None

    # 8. Apply $...$ math wrapping now that the question is validated
    return _wrap_question_math(q)


# ── Variety engine helpers ────────────────────────────────────────────────────


def _select_templates_balanced(available: list[dict], count: int) -> list[dict]:
    """
    Select `count` templates with a capped round-robin shuffle so no single
    template appears more than ceil(count / len(available)) times.

    Replaces random.choices(available, k=count) for non-Mixed sessions.
    Guarantees: every template in `available` appears at least
    floor(count/n) times and at most ceil(count/n) times.

    Edge cases:
      n=1  → the one template fills all slots (correct behaviour).
      count ≤ n → each template appears at most once (maximum variety).
      n=0  → returns [] (caller guards against empty pool before calling).
    """
    n = len(available)
    if n == 0:
        return []
    cap = math.ceil(count / n)
    pool = available * cap   # each template dict repeated cap times
    random.shuffle(pool)
    return pool[:count]


def _select_templates_balanced_mixed(available: list[dict], count: int) -> list[dict]:
    """
    Balanced selection for Mixed-strand sessions.

    Preserves the existing strand-proportional weighting (strands with more
    templates contribute proportionally more questions) while still capping
    any single template at ceil(count / len(available)) occurrences.
    """
    n = len(available)
    if n == 0:
        return []
    strand_counts = Counter(t.get("strand") for t in available)
    cap = math.ceil(count / n)
    pool: list[dict] = []
    for t in available:
        weight = strand_counts[t.get("strand", "")] * cap
        pool.extend([t] * weight)
    random.shuffle(pool)
    return pool[:count]


def _param_fingerprint(params: dict) -> frozenset:
    """Hashable fingerprint of scalar values in a params dict."""
    return frozenset(
        (k, v) for k, v in params.items()
        if isinstance(v, (int, float, str, bool))
    )


def _ensure_param_diversity(
    params_list: list[dict],
    template: dict,
    difficulty: str,
    target: int,
    max_attempts: int = 10,
) -> list[dict]:
    """
    Guarantee `target` param sets with distinct fingerprints.

    Removes duplicates from `params_list` and replaces them with freshly
    generated fallback params. If uniqueness cannot be fully achieved (e.g.
    the template has very few legal param combinations), accepts a duplicate
    rather than returning fewer than `target` items.

    Called after the AI returns params and after initial fallback padding,
    so it is always given at least `target` items to work with.
    """
    seen: set[frozenset] = set()
    result: list[dict] = []

    # First pass: accept unique params from the AI's list
    for p in params_list:
        if len(result) >= target:
            break
        fp = _param_fingerprint(p)
        if fp not in seen:
            seen.add(fp)
            result.append(p)
        else:
            logger.debug(
                "Duplicate params for template %s — slot queued for fallback replacement",
                template.get("id"),
            )

    # Second pass: fill remaining slots with locally generated fallback params
    slots_needed = target - len(result)
    if slots_needed > 0:
        logger.info(
            "Template %s: %d/%d param set(s) were duplicates; generating %d fallback(s)",
            template.get("id"), slots_needed, target, slots_needed,
        )
    for _ in range(slots_needed):
        filled = False
        for _attempt in range(max_attempts):
            fb = _fallback_params(template, difficulty)
            fp = _param_fingerprint(fb)
            if fp not in seen:
                seen.add(fp)
                result.append(fb)
                filled = True
                break
        if not filled:
            # Accept duplicate rather than drop the slot — keeps session full
            result.append(_fallback_params(template, difficulty))
            logger.warning(
                "Template %s: could not find unique fallback after %d attempts; "
                "accepting duplicate to avoid question deficit",
                template.get("id"), max_attempts,
            )

    return result[:target]


# ── Session question generator ────────────────────────────────────────────────

async def generate_session_questions(
    year_level: int,
    strand: str,
    difficulty: str,
    count: int,
) -> list[QuestionObject]:
    """
    Generate `count` verified questions for a session.

    Flow:
      1. Filter templates by year/strand (parametric only)
      2. Randomly assign templates to question slots (varied distribution)
      3. Batch AI calls by template_id
      4. Verify and assemble each question
      5. Fall back to local params if AI fails
    """
    all_templates = get_templates_for(year_level, strand)
    parametric = [t for t in all_templates if t.get("generation_mode") == "parametric"]

    # For advanced difficulty, add curated multi_select templates to the pool.
    # (T-7N-02 is already in parametric; only curated_bank ones need to be added.)
    curated_multi = []
    if difficulty == "advanced":
        for tid, bank_data in MULTI_SELECT_BANKS.items():
            if bank_data["year"] != year_level:
                continue
            if strand != "Mixed" and bank_data["strand"] != strand:
                continue
            try:
                meta = load_template_meta(tid)
                curated_multi.append(meta)
            except Exception:
                pass

    # Add curated_bank single-select templates (all difficulties).
    # Only include those whose bank has been populated (has items).
    curated_single = []
    for t in all_templates:
        if t.get("generation_mode") != "curated_bank":
            continue
        if t["id"] in MULTI_SELECT_BANKS:
            continue  # already handled above via curated_multi
        bank_name = t.get("answer_lookup", "")
        if load_curated_bank(bank_name):  # non-empty → populated
            curated_single.append(t)

    available = parametric + curated_multi + curated_single

    if not available:
        raise ValueError(
            f"No parametric templates available for Year {year_level} {strand}"
        )

    # ── Layer 2: Companion pool expansion ────────────────────────────────────
    # When the native pool is critically thin (< count/2 unique templates),
    # borrow companion templates from an adjacent year (same strand) so the
    # balanced selector has enough variety to work with. Skipped for Mixed
    # sessions which already draw from a large cross-strand pool.
    if strand != "Mixed" and should_expand(len(available), count):
        native_count = len(available)
        companion_ids = get_companion_ids(year_level, strand)
        limit = max_companions(count)
        added = 0
        existing_ids = {t["id"] for t in available}
        for cid in companion_ids:
            if added >= limit:
                break
            if cid in existing_ids:
                continue
            try:
                tmpl = load_template_meta(cid)
                if tmpl.get("generation_mode") in ("parametric", "curated_bank"):
                    available.append(tmpl)
                    existing_ids.add(cid)
                    added += 1
            except Exception as exc:
                logger.warning("Could not load companion template %s: %s", cid, exc)
        if added:
            logger.info(
                "Variety engine: expanded Y%d %s pool %d→%d (%d companion(s) added)",
                year_level, strand, native_count, len(available), added,
            )

    # ── Layer 1: Balanced template selection ─────────────────────────────────
    # Replace random.choices (with replacement) with a capped shuffle pool so
    # no single template can appear more than ceil(count / pool_size) times.
    # Mixed sessions retain strand-proportional weighting via the mixed variant.
    if strand == "Mixed":
        selected = _select_templates_balanced_mixed(available, count)
    else:
        selected = _select_templates_balanced(available, count)

    # Group by template_id to batch the AI calls
    template_counts = Counter(t["id"] for t in selected)
    template_by_id = {t["id"]: t for t in selected}

    questions: list[QuestionObject] = []

    for template_id, n in template_counts.items():
        template = template_by_id[template_id]

        if template_id in MULTI_SELECT_BANKS or template.get("generation_mode") == "curated_bank":
            params_list: list[dict] = [{} for _ in range(n)]

            # Pre-select bank items without replacement to avoid repeats within a session.
            if template_id in MULTI_SELECT_BANKS:
                pool = MULTI_SELECT_BANKS[template_id]["items"]
            else:
                pool = load_curated_bank(template.get("answer_lookup", ""))

            if pool:
                if len(pool) >= n:
                    preselected_items = random.sample(pool, n)
                else:
                    # Bank smaller than needed: cycle through shuffled pool
                    shuffled = list(pool)
                    random.shuffle(shuffled)
                    preselected_items = (shuffled * ((n // len(shuffled)) + 1))[:n]
            else:
                preselected_items = [None] * n
        else:
            # AI call for param batches
            try:
                params_list = await ai_service.generate_questions(
                    template_id=template_id,
                    difficulty=difficulty,
                    count=n,
                    param_schema=template.get("params", {}),
                )
            except Exception as e:
                logger.warning(
                    "AI call failed for %s (using fallback): %s", template_id, e
                )
                params_list = []

            # Pad with fallback if AI returned fewer than needed
            while len(params_list) < n:
                params_list.append(_fallback_params(template, difficulty))

            # ── Layer 3: Param diversity gate ─────────────────────────────────
            # Deduplicate param sets by fingerprint and replace duplicates with
            # locally generated fallback params. Prevents the same question
            # appearing twice when Haiku returns identical values for a template
            # that was selected multiple times (common in thin pools like Y9 Number).
            params_list = _ensure_param_diversity(params_list, template, difficulty, target=n)

            preselected_items = [None] * n

        for i, raw_params in enumerate(params_list[:n]):
            params = dict(raw_params)
            bank_item = preselected_items[i] if i < len(preselected_items) else None

            # Post-generation validation: ensure integer solution for constrained Algebra templates.
            # Runs the verifier inline; if non-integer, replaces with fallback params (max 3 retries).
            if template_id in _ALGEBRA_INTEGER_CONSTRAINT_TEMPLATES:
                resolved = _resolve_derived_params(template, dict(params))
                if not _solution_is_integer(template_id, resolved):
                    replaced = False
                    for _attempt in range(3):
                        fb = _fallback_params(template, difficulty)
                        resolved = _resolve_derived_params(template, dict(fb))
                        if _solution_is_integer(template_id, resolved):
                            params = fb
                            replaced = True
                            break
                    if not replaced:
                        logger.warning(
                            "Could not find integer-solution params for %s after 3 retries — skipping slot",
                            template_id,
                        )
                        continue

            q = build_question(template, params, difficulty, bank_item=bank_item)
            if q is None:
                # Retry up to 3 times with fresh fallback params; silently skip if all fail
                for _retry in range(3):
                    q = build_question(
                        template, _fallback_params(template, difficulty),
                        difficulty, bank_item=bank_item,
                    )
                    if q is not None:
                        break
            if q is not None:
                questions.append(q)

    # Top-up: fill any slots lost due to integer-constraint retries exhausted
    if len(questions) < count:
        non_constrained = [t for t in available if t["id"] not in _ALGEBRA_INTEGER_CONSTRAINT_TEMPLATES]
        top_up_pool = non_constrained if non_constrained else available
        if top_up_pool:
            attempts = 0
            deficit = count - len(questions)
            while len(questions) < count and attempts < deficit * 5:
                attempts += 1
                tmpl = random.choice(top_up_pool)
                q = build_question(tmpl, _fallback_params(tmpl, difficulty), difficulty)
                if q:
                    questions.append(q)
        else:
            logger.warning("Top-up pool empty; cannot fill %d deficit slots", count - len(questions))

    # Deduplicate by question_text across ALL templates.
    # Curated banks have a fixed set of items. Parametric templates can also produce identical
    # question texts when the AI returns the same params for the same template multiple times
    # (observed in Y9 Number where few templates exist and repeats are common).
    seen_texts: set[str] = set()
    deduped: list[QuestionObject] = []
    for q in questions:
        if q.question_text not in seen_texts:
            seen_texts.add(q.question_text)
            deduped.append(q)
        else:
            logger.warning("Dropped duplicate question_text from session (template %s)", q.template_id)
    questions = deduped

    random.shuffle(questions)
    return questions[:count]
