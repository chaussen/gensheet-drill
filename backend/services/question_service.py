"""
question_service.py
===================
Orchestrates: template selection → AI param generation → schema validation
              → verification → distractor assembly → QuestionObject construction.

Chain per CLAUDE.md §5 Iteration 1, step 4.
"""
import random
import re
import uuid
import logging
from collections import Counter
from datetime import datetime, timezone

from docs_loader import load_template_meta, get_templates_for
from services.verification import VerificationEngine
from services import ai_service
from services.distractor_service import generate_distractors
from models.schemas import QuestionObject

logger = logging.getLogger(__name__)
_engine = VerificationEngine()


# ── Multi-select template registry ────────────────────────────────────────────

# T-7N-02 is parametric; multi_select question is built from its `n` param.
MULTI_SELECT_PARAMETRIC: set[str] = {"T-7N-02"}

# Curated banks for the 4 curated_bank multi_select templates.
# Each item has 5 pre-authored options, with correct_indices for the multi_select answer.
MULTI_SELECT_BANKS: dict[str, dict] = {
    "T-7SP-01": {
        "vc_code": "VC2M7SP01",
        "year": 7,
        "strand": "Space",
        "topic": "Properties of 2D shapes",
        "items": [
            {
                "question_text": "Which properties does a rhombus have? Select all that apply.",
                "options": [
                    "All sides are equal",
                    "All angles are 90°",
                    "Opposite sides are parallel",
                    "Diagonals are equal in length",
                    "Diagonals are perpendicular",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A rhombus has all sides equal, opposite sides parallel, and perpendicular diagonals. Its angles are not necessarily 90° and its diagonals are not necessarily equal.",
            },
            {
                "question_text": "Which properties does a rectangle have? Select all that apply.",
                "options": [
                    "All angles are 90°",
                    "All sides are equal",
                    "Opposite sides are equal",
                    "Diagonals are perpendicular",
                    "Diagonals are equal in length",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A rectangle has all right angles, equal opposite sides, and equal diagonals. Its sides are not all equal (unless it is a square) and its diagonals are not perpendicular.",
            },
            {
                "question_text": "Which properties does a kite have? Select all that apply.",
                "options": [
                    "Two pairs of consecutive equal sides",
                    "All sides are equal",
                    "Diagonals are perpendicular",
                    "Opposite sides are parallel",
                    "One diagonal bisects the other",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A kite has two pairs of consecutive equal sides, perpendicular diagonals, and one diagonal bisects the other. It does not have all sides equal or parallel opposite sides.",
            },
        ],
    },
    "T-8SP-02": {
        "vc_code": "VC2M8SP02",
        "year": 8,
        "strand": "Space",
        "topic": "Properties of quadrilaterals",
        "items": [
            {
                "question_text": "Select all true statements about a parallelogram.",
                "options": [
                    "Opposite sides are parallel",
                    "All angles are 90°",
                    "Opposite angles are equal",
                    "Diagonals are equal in length",
                    "Diagonals bisect each other",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A parallelogram has parallel opposite sides, equal opposite angles, and diagonals that bisect each other. It does not require right angles or equal-length diagonals.",
            },
            {
                "question_text": "Select all true statements about a square.",
                "options": [
                    "All sides are equal",
                    "Diagonals bisect each other at right angles",
                    "Diagonals are unequal in length",
                    "All angles are 90°",
                    "Opposite sides are not parallel",
                ],
                "correct_indices": [0, 1, 3],
                "explanation": "A square has all sides equal, all angles 90°, and diagonals that bisect each other at right angles. Its diagonals are equal (not unequal) and all sides are parallel.",
            },
            {
                "question_text": "Select all true statements about a trapezium.",
                "options": [
                    "Exactly one pair of parallel sides",
                    "Both pairs of opposite sides are parallel",
                    "Co-interior angles between parallel sides are supplementary",
                    "Diagonals always bisect each other",
                    "May have two equal non-parallel sides",
                ],
                "correct_indices": [0, 2, 4],
                "explanation": "A trapezium has exactly one pair of parallel sides. Co-interior angles between the parallel sides sum to 180°. An isosceles trapezium has two equal non-parallel sides. Diagonals do not generally bisect each other.",
            },
        ],
    },
    "T-9N-01": {
        "vc_code": "VC2M9N01",
        "year": 9,
        "strand": "Number",
        "topic": "Rational and irrational numbers",
        "items": [
            {
                "question_text": "Select all irrational numbers.",
                "options": ["√2", "√9", "π", "0.4", "3/7"],
                "correct_indices": [0, 2],
                "explanation": "√2 and π are irrational — they cannot be expressed as p/q for integers p, q. √9 = 3, 0.4 = 2/5, and 3/7 are all rational.",
            },
            {
                "question_text": "Select all irrational numbers.",
                "options": ["0.333…", "√5", "5/8", "√7", "1.25"],
                "correct_indices": [1, 3],
                "explanation": "√5 and √7 are irrational. 0.333… = 1/3, 5/8, and 1.25 = 5/4 are all rational.",
            },
            {
                "question_text": "Select all irrational numbers.",
                "options": ["√3", "√4", "22/7", "√6", "0.1"],
                "correct_indices": [0, 3],
                "explanation": "√3 and √6 are irrational. √4 = 2, 22/7 is a rational approximation of π, and 0.1 = 1/10 are rational.",
            },
        ],
    },
    "T-9A-05": {
        "vc_code": "VC2M9A05",
        "year": 9,
        "strand": "Algebra",
        "topic": "Identify quadratic equations",
        "items": [
            {
                "question_text": "Select all quadratic equations.",
                "options": ["x² + 3x − 4 = 0", "2x + 5 = 0", "x² = 9", "x³ − 1 = 0", "y = x + 1"],
                "correct_indices": [0, 2],
                "explanation": "x² + 3x − 4 = 0 and x² = 9 are quadratic (highest degree 2). 2x + 5 = 0 and y = x + 1 are linear; x³ − 1 = 0 is cubic.",
            },
            {
                "question_text": "Select all quadratic equations.",
                "options": ["y = x²", "y = 2x + 1", "3x² − 2x + 1 = 0", "y = 1/x", "x³ = 8"],
                "correct_indices": [0, 2],
                "explanation": "y = x² and 3x² − 2x + 1 = 0 are quadratic. y = 2x + 1 is linear, y = 1/x is a hyperbola, and x³ = 8 is cubic.",
            },
            {
                "question_text": "Select all quadratic equations.",
                "options": ["x² − 5x + 6 = 0", "x = 4", "2x² + x = 0", "y = 3/x", "4x − 1 = 0"],
                "correct_indices": [0, 2],
                "explanation": "x² − 5x + 6 = 0 and 2x² + x = 0 are quadratic. x = 4 is a constant equation, y = 3/x is a hyperbola, and 4x − 1 = 0 is linear.",
            },
        ],
    },
}

MULTI_SELECT_TEMPLATE_IDS: set[str] = set(MULTI_SELECT_BANKS) | MULTI_SELECT_PARAMETRIC

_T7N02_PRIME_POOL: list[int] = [2, 3, 5, 7, 11, 13, 17, 19]


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
                    val = random.randint(int(lo), int(hi))
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
            logger.debug("Could not derive %s from rule '%s': %s", key, rule, e)

    # Top-level "derived" dict (e.g. T-7A-03)
    for key, rule in template.get("derived", {}).items():
        if key in params:
            continue
        expr = str(rule).replace("×", "*").replace("÷", "/")
        try:
            params[key] = _safe_eval(expr, params)
        except Exception as e:
            logger.debug("Could not derive top-level %s from '%s': %s", key, rule, e)

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
    """Minimal step-by-step explanation placeholder."""
    topic = template.get("topic", template["id"])
    answer_str = _format_answer(correct_answer)
    return f"The correct answer is {answer_str}. ({topic})"


# ── Question builder ──────────────────────────────────────────────────────────

def _render_question_text(template: dict, params: dict) -> str:
    """Substitute params into a randomly chosen context variant or the base template."""
    candidates = template.get("context_variants", []) + [template.get("question_template", "")]
    candidates = [c for c in candidates if c]
    template_str = random.choice(candidates)
    try:
        return template_str.format(**params)
    except (KeyError, ValueError):
        try:
            return template.get("question_template", "").format(**params)
        except Exception:
            return template.get("question_template", "")


def _build_multi_select_question(
    template_id: str, params: dict, difficulty: str
) -> QuestionObject | None:
    """Build a multi_select QuestionObject. Called for advanced difficulty only."""
    if template_id == "T-7N-02":
        return _build_t7n02_multi_select(params, difficulty)

    bank = MULTI_SELECT_BANKS.get(template_id)
    if not bank:
        return None

    item = random.choice(bank["items"])
    indexed = list(enumerate(item["options"]))
    random.shuffle(indexed)
    shuffled_options = [opt for _, opt in indexed]
    old_to_new = {old_i: new_i for new_i, (old_i, _) in enumerate(indexed)}
    shuffled_correct = sorted(old_to_new[i] for i in item["correct_indices"])

    try:
        return QuestionObject(
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
        return QuestionObject(
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
    except Exception as e:
        logger.warning("T-7N-02 multi_select build failed: %s", e)
        return None


def build_question(template: dict, params: dict, difficulty: str) -> QuestionObject | None:
    """
    Construct a single verified QuestionObject from a template + params dict.
    Returns None if verification or Pydantic validation fails — caller should skip/retry.
    """
    template_id = template["id"]

    if template_id in MULTI_SELECT_TEMPLATE_IDS and difficulty == "advanced":
        return _build_multi_select_question(template_id, params, difficulty)

    if template.get("generation_mode") == "curated_bank":
        # TODO: implement curated_bank question assembly when bank data is available
        logger.debug("Skipping curated_bank template %s", template_id)
        return None

    # Resolve derived params (t2/t3, op from expr_template, etc.)
    params = _resolve_derived_params(template, params)

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

    correct_str = _format_answer(correct_answer)

    # 2. Distractors
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

    # 3. Shuffle options, record correct_index
    options = [correct_str] + distractors
    random.shuffle(options)
    correct_index = options.index(correct_str)

    # 4. Render question text
    question_text = _render_question_text(template, params)

    # 5. Explanation
    explanation = _build_explanation(template, params, correct_answer)

    # 6. Validate with Pydantic
    try:
        return QuestionObject(
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

    available = parametric + curated_multi

    if not available:
        raise ValueError(
            f"No parametric templates available for Year {year_level} {strand}"
        )

    # Distribute count across templates for variety
    selected = random.choices(available, k=count)

    # Group by template_id to batch the AI calls
    template_counts = Counter(t["id"] for t in selected)
    template_by_id = {t["id"]: t for t in selected}

    questions: list[QuestionObject] = []

    for template_id, n in template_counts.items():
        template = template_by_id[template_id]

        if template_id in MULTI_SELECT_BANKS:
            params_list = [{} for _ in range(n)]
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

        for raw_params in params_list[:n]:
            params = dict(raw_params)

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

            q = build_question(template, params, difficulty)
            if q:
                questions.append(q)
            else:
                # Retry once with fresh fallback params
                q2 = build_question(template, _fallback_params(template, difficulty), difficulty)
                if q2:
                    questions.append(q2)

    random.shuffle(questions)
    return questions[:count]
