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


# ── Param helpers ─────────────────────────────────────────────────────────────

def _has_integer_solution_constraint(schema: dict) -> bool:
    """Return True if the schema declares a solution_constraint requiring integer answers."""
    sol = schema.get("solution_constraint", "")
    return isinstance(sol, str) and "integer" in sol.lower()


def _solution_is_integer(template_id: str, params: dict) -> bool:
    """
    Pre-verify that params produce an exact integer solution, without calling
    the main verifier (which truncates non-integers silently via int(sol[0])).
    Currently handles T-8A-02 (ax ± b = cx ± d).  Returns True for all other
    templates so the caller can pass through without disruption.
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


def build_question(template: dict, params: dict, difficulty: str) -> QuestionObject | None:
    """
    Construct a single verified QuestionObject from a template + params dict.
    Returns None if verification or Pydantic validation fails — caller should skip/retry.
    """
    template_id = template["id"]

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

    if not parametric:
        raise ValueError(
            f"No parametric templates available for Year {year_level} {strand}"
        )

    # Distribute count across templates for variety
    selected = random.choices(parametric, k=count)

    # Group by template_id to batch the AI calls
    template_counts = Counter(t["id"] for t in selected)
    template_by_id = {t["id"]: t for t in selected}

    questions: list[QuestionObject] = []

    for template_id, n in template_counts.items():
        template = template_by_id[template_id]

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
            q = build_question(template, dict(raw_params), difficulty)
            if q:
                questions.append(q)
            else:
                # Retry once with fresh fallback params
                q2 = build_question(template, _fallback_params(template, difficulty), difficulty)
                if q2:
                    questions.append(q2)

    random.shuffle(questions)
    return questions[:count]
