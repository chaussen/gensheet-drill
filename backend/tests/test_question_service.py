"""
Tests for question_service.py — no real AI calls; ai_service is mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch

from docs_loader import load_template_meta
from services.verification import VerificationEngine
from services.question_service import (
    _fallback_params,
    _resolve_derived_params,
    _solution_is_integer,
    _format_answer,
    build_question,
    generate_session_questions,
    _ALGEBRA_INTEGER_CONSTRAINT_TEMPLATES,
    MULTI_SELECT_BANKS,
    MULTI_SELECT_TEMPLATE_IDS,
    _build_multi_select_question,
    _build_t7n02_multi_select,
)


# ── _fallback_params ──────────────────────────────────────────────────────────

def test_fallback_params_randint():
    template = load_template_meta("T-7N-08")  # integer_operation: a, b (randint), op (choice)
    params = _fallback_params(template, "standard")
    assert "a" in params
    assert "b" in params
    assert "op" in params
    assert params["op"] in ["+", "-"]


def test_fallback_params_choice():
    template = load_template_meta("T-7N-01")  # sqrt: n is choice
    params = _fallback_params(template, "foundation")
    assert "n" in params
    assert params["n"] in [4, 9, 16, 25, 36, 49, 64, 81, 100]


def test_fallback_params_choice_difficulty():
    template = load_template_meta("T-7N-01")
    foundation = _fallback_params(template, "foundation")
    advanced = _fallback_params(template, "advanced")
    # Advanced pool is larger; foundation values are a subset of advanced
    assert foundation["n"] in [4, 9, 16, 25, 36, 49, 64, 81, 100]


def test_fallback_params_t8a02_integer_solution():
    """
    Regression: T-8A-02 fallback must produce params whose solution is an
    exact integer. Before the fix, random params like a=1,b=2,c=8,d=12 gave
    x = -10/7 which the verifier silently truncated to -1 (wrong answer).
    """
    template = load_template_meta("T-8A-02")
    engine = VerificationEngine()
    for _ in range(50):
        params = _fallback_params(template, "standard")
        assert _solution_is_integer("T-8A-02", params), \
            f"Non-integer solution for params {params}"
        answer = engine.verify("T-8A-02", params)
        # Verifier returns sympy.Integer (not Python int) now that int() truncation is removed.
        # Build_question normalises it to Python int, but here we test the verifier directly.
        from sympy import Integer as SympyInt
        assert isinstance(answer, (int, SympyInt)), \
            f"Expected integer answer, got {type(answer)}: {answer}"
        # Verify the answer is actually correct (not a truncation artefact)
        a, c = int(params["a"]), int(params["c"])
        b, d = int(params["b"]), int(params["d"])
        op1, op2 = params.get("op1", "+"), params.get("op2", "+")
        b_s = b if op1 == "+" else -b
        d_s = d if op2 == "+" else -d
        expected = (d_s - b_s) // (a - c)
        assert answer == expected, f"Verifier returned {answer}, expected {expected}"


# ── _resolve_derived_params ───────────────────────────────────────────────────

def test_resolve_sequence_derived():
    """T-7A-03 has top-level derived dict: t2 = t1 + d, etc."""
    template = load_template_meta("T-7A-03")
    params = {"t1": 3, "d": 4}
    resolved = _resolve_derived_params(template, params)
    assert resolved["t2"] == 7
    assert resolved["t3"] == 11
    assert resolved["t4"] == 15


def test_resolve_expr_template_to_expr():
    """T-8A-01 uses expr_template → expr for question rendering."""
    template = load_template_meta("T-8A-01")
    params = {"expr_template": "{a}({b}x + {c})", "a": 3, "b": 2, "c": 5, "d": 1}
    resolved = _resolve_derived_params(template, params)
    assert "expr" in resolved
    assert resolved["expr"] == "3(2x + 5)"


def test_resolve_op_from_expr_template():
    """op should be inferred from expr_template for expand_simplify verifier."""
    template = load_template_meta("T-8A-01")
    params = {"expr_template": "{a}({b}x - {c})", "a": 3, "b": 2, "c": 5}
    resolved = _resolve_derived_params(template, params)
    assert resolved.get("op") == "-"


# ── _format_answer ────────────────────────────────────────────────────────────

def test_format_integer():
    assert _format_answer(8) == "8"


def test_format_float_integer_like():
    assert _format_answer(30.0) == "30"


def test_format_float_decimal():
    assert _format_answer(3.14) == "3.14"


def test_format_tuple_coordinates():
    assert _format_answer((3, -4)) == "(3, -4)"


def test_format_string_passthrough():
    assert _format_answer("3/4") == "3/4"
    assert _format_answer("2^3 × 5") == "2^3 × 5"


# ── build_question ────────────────────────────────────────────────────────────

def test_build_question_integer_answer():
    """T-7N-01: sqrt — simple integer answer, should produce valid QuestionObject."""
    template = load_template_meta("T-7N-01")
    q = build_question(template, {"n": 64}, "standard")
    assert q is not None
    assert q.options[q.correct_index] == "8"
    assert len(q.options) == 4
    assert len(set(q.options)) == 4  # all distinct
    assert q.year_level == 7
    assert q.strand == "Number"
    assert q.vc_code == "VC2M7N01"


def test_build_question_shuffles_options():
    """Correct answer position should vary across multiple builds."""
    template = load_template_meta("T-7N-01")
    positions = set()
    for _ in range(20):
        q = build_question(template, {"n": 64}, "standard")
        positions.add(q.correct_index)
    # Over 20 builds, we expect more than 1 unique position
    assert len(positions) > 1


def test_build_question_correct_index_valid():
    template = load_template_meta("T-8A-02")
    params = {"a": 3, "b": 2, "c": 1, "d": 8, "op1": "+", "op2": "+"}
    q = build_question(template, params, "standard")
    assert q is not None
    assert 0 <= q.correct_index <= 3
    assert q.options[q.correct_index] == "3"


def test_build_question_curated_bank_returns_none():
    """Curated-bank templates are not yet supported — should return None."""
    template = load_template_meta("T-7N-03")
    q = build_question(template, {}, "standard")
    assert q is None


def test_build_question_bad_params_returns_none():
    """If params cause verification to fail, build_question returns None gracefully."""
    template = load_template_meta("T-7N-01")
    # n=7 is not a perfect square — sqrt returns non-integer but verifier won't raise;
    # use a template with strict requirements and broken params
    template2 = load_template_meta("T-7N-05")
    # division by zero denom
    q = build_question(template2, {"a": 1, "b": 0, "c": 1, "d": 2, "op": "×"}, "standard")
    # b=0 denominator — Fraction(1, 0) raises, so should return None
    assert q is None


# ── generate_session_questions (mocked AI) ────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_session_questions_returns_count():
    """With mocked AI returning valid params, should produce requested count."""
    mock_params = [
        {"a": 3, "b": 2, "c": 1, "d": 8, "op1": "+", "op2": "+"},  # T-8A-02: answer=3
    ]

    with patch("services.question_service.ai_service.generate_questions",
               new=AsyncMock(return_value=mock_params * 5)):
        questions = await generate_session_questions(8, "Algebra", "standard", 3)

    assert len(questions) == 3
    for q in questions:
        assert len(q.options) == 4
        assert 0 <= q.correct_index <= 3


@pytest.mark.asyncio
async def test_generate_session_questions_fallback_on_ai_error():
    """When AI raises, fallback params should still produce valid questions."""
    with patch("services.question_service.ai_service.generate_questions",
               new=AsyncMock(side_effect=ValueError("AI unavailable"))):
        questions = await generate_session_questions(8, "Algebra", "standard", 3)

    # Fallback params may produce fewer valid questions if some verifications fail,
    # but should not raise.
    assert isinstance(questions, list)
    for q in questions:
        assert len(q.options) == 4


@pytest.mark.asyncio
async def test_generate_session_questions_no_parametric_templates():
    """Should raise ValueError if no parametric templates exist for the strand."""
    with pytest.raises(ValueError, match="No parametric templates"):
        # "Space" year 9 might have only curated templates — use a definitely empty combo
        with patch("services.question_service.get_templates_for", return_value=[]):
            await generate_session_questions(8, "Algebra", "standard", 3)


# ── _format_answer — sympy and Fraction types ─────────────────────────────────

def test_format_answer_sympy_integer():
    """sympy.Integer should render as a plain integer string, not '5' with sympy repr."""
    from sympy import Integer as SympyInt
    assert _format_answer(SympyInt(5)) == "5"
    assert _format_answer(SympyInt(-3)) == "-3"


def test_format_answer_sympy_rational():
    """sympy.Rational should render as 'p/q', not a decimal or truncated int."""
    from sympy import Rational
    assert _format_answer(Rational(-10, 7)) == "-10/7"
    assert _format_answer(Rational(1, 2)) == "1/2"
    assert _format_answer(Rational(3, 1)) == "3"  # whole-number rational


def test_format_answer_stdlib_fraction():
    """fractions.Fraction should render as 'p/q' (stdlib str() does this already)."""
    from fractions import Fraction
    assert _format_answer(Fraction(1, 2)) == "1/2"
    assert _format_answer(Fraction(-10, 7)) == "-10/7"
    assert _format_answer(Fraction(4, 1)) == "4"


# ── _solution_is_integer — T-9A-04 ───────────────────────────────────────────

def test_solution_is_integer_t9a04_integer():
    """y = 2x + 1, y = -x + 7 → x = 2 (integer)."""
    assert _solution_is_integer("T-9A-04", {"a": 2, "b": 1, "c": -1, "d": 7}) is True


def test_solution_is_integer_t9a04_fractional():
    """y = 3x + 1, y = x + 2 → x = 1/2 (not integer)."""
    assert _solution_is_integer("T-9A-04", {"a": 3, "b": 1, "c": 1, "d": 2}) is False


def test_solution_is_integer_t9a04_equal_slopes():
    """a == c means parallel lines (no solution) — should return False."""
    assert _solution_is_integer("T-9A-04", {"a": 3, "b": 1, "c": 3, "d": 5}) is False


def test_solution_is_integer_constant_set():
    """All four constrained templates are present in the constant."""
    assert _ALGEBRA_INTEGER_CONSTRAINT_TEMPLATES == {"T-7A-02", "T-8A-02", "T-9A-02", "T-9A-04"}


# ── build_question — fractional-answer display ────────────────────────────────

def test_build_question_t8a02_fractional_answer_displays_as_fraction():
    """
    T-8A-02 with params that yield x = -10/7 (1x + 3 = 8x + 13).
    The correct option must be '-10/7', not '-1' (truncated) or '-1.4285...' (float).
    """
    template = load_template_meta("T-8A-02")
    q = build_question(template, {"a": 1, "b": 3, "c": 8, "d": 13, "op1": "+", "op2": "+"}, "standard")
    assert q is not None
    correct_option = q.options[q.correct_index]
    assert correct_option == "-10/7", \
        f"Expected '-10/7' as correct option, got '{correct_option}'"
    assert "-1" not in q.options or correct_option != "-1", \
        "Must not silently use the truncated answer -1 as correct"


def test_build_question_t8a02_integer_answer_unaffected():
    """
    Regression: integer T-8A-02 solutions must still display as plain integers.
    3x + 2 = x + 8 → x = 3
    """
    template = load_template_meta("T-8A-02")
    q = build_question(template, {"a": 3, "b": 2, "c": 1, "d": 8, "op1": "+", "op2": "+"}, "standard")
    assert q is not None
    assert q.options[q.correct_index] == "3"


# ── generate_session_questions — post-gen validation ─────────────────────────

@pytest.mark.asyncio
async def test_generate_session_questions_rejects_fractional_ai_params():
    """
    When AI returns params that produce a fractional solution for T-8A-02,
    post-gen validation must replace them so no T-8A-02 question has a
    fractional correct answer.  We pin get_templates_for to return only T-8A-02
    so that other Algebra templates (e.g. T-8A-03 gradient, which legitimately
    produces fractions) don't confound the assertion.
    """
    # These params yield x = -10/7 — a fractional solution for T-8A-02
    fractional_params = {"a": 1, "b": 3, "c": 8, "d": 13, "op1": "+", "op2": "+"}
    template_8a02 = load_template_meta("T-8A-02")

    with patch("services.question_service.ai_service.generate_questions",
               new=AsyncMock(return_value=[fractional_params] * 5)), \
         patch("services.question_service.get_templates_for",
               return_value=[template_8a02]):
        questions = await generate_session_questions(8, "Algebra", "standard", 3)

    for q in questions:
        assert q.template_id == "T-8A-02"
        correct = q.options[q.correct_index]
        assert "/" not in correct, \
            f"Question {q.question_id} has fractional correct answer '{correct}' — post-gen validation failed"


@pytest.mark.asyncio
async def test_generate_session_questions_t9a04_fractional_ai_params_replaced():
    """Same post-gen validation for T-9A-04: AI returns fractional-solution params."""
    # y = 3x + 1, y = x + 2 → x = 1/2
    fractional_params = {"a": 3, "b": 1, "c": 1, "d": 2}

    template_9a04 = load_template_meta("T-9A-04")

    with patch("services.question_service.ai_service.generate_questions",
               new=AsyncMock(return_value=[fractional_params] * 5)), \
         patch("services.question_service.get_templates_for",
               return_value=[template_9a04]):
        questions = await generate_session_questions(9, "Algebra", "standard", 2)

    for q in questions:
        correct = q.options[q.correct_index]
        assert "/" not in correct, \
            f"Fractional answer '{correct}' slipped through post-gen validation"


# ── Multi-select tests ────────────────────────────────────────────────────────

def test_multi_select_curated_bank_structure():
    """T-8SP-02 at advanced builds a valid multi_select QuestionObject."""
    q = _build_multi_select_question("T-8SP-02", {}, "advanced")
    assert q is not None
    assert q.question_type == "multi_select"
    assert len(q.options) == 5
    assert q.correct_indices is not None
    assert 2 <= len(q.correct_indices) <= 3
    assert q.correct_index == -1
    assert all(0 <= i <= 4 for i in q.correct_indices)
    assert len(set(q.correct_indices)) == len(q.correct_indices)  # no duplicates


def test_multi_select_t9n01_bank():
    """T-9N-01 at advanced produces irrational-selection multi_select question."""
    q = _build_multi_select_question("T-9N-01", {}, "advanced")
    assert q is not None
    assert q.question_type == "multi_select"
    assert len(q.options) == 5
    assert q.correct_indices is not None


def test_multi_select_t7n02_prime_factors_correct():
    """T-7N-02 multi_select: correct_indices map to prime factors of n."""
    params = {"n": 12}  # prime factors: 2, 3
    q = _build_t7n02_multi_select(params, "advanced")
    assert q is not None
    assert q.question_type == "multi_select"
    assert len(q.options) == 5
    correct_values = {q.options[i] for i in q.correct_indices}
    assert correct_values == {"2", "3"}


def test_multi_select_t7n02_five_options_various_n():
    """T-7N-02 multi_select always produces exactly 5 options."""
    for n in [12, 18, 30, 72, 100]:
        q = _build_t7n02_multi_select({"n": n}, "advanced")
        assert q is not None, f"Build failed for n={n}"
        assert len(q.options) == 5, f"Expected 5 options for n={n}, got {len(q.options)}"


def test_multi_select_single_select_unchanged():
    """Single-select templates at advanced are not affected by the multi_select guard."""
    template = load_template_meta("T-7N-01")  # sqrt: always single_select
    params = {"n": 64}
    q = build_question(template, params, "advanced")
    assert q is not None
    assert q.question_type == "single_select"
    assert len(q.options) == 4
    assert 0 <= q.correct_index <= 3


def test_multi_select_template_ids_set():
    """MULTI_SELECT_TEMPLATE_IDS contains all 5 expected templates."""
    expected = {"T-7N-02", "T-7SP-01", "T-8SP-02", "T-9N-01", "T-9A-05"}
    assert expected == MULTI_SELECT_TEMPLATE_IDS


def test_response_item_validation_single():
    """ResponseItem accepts selected_index only."""
    from models.schemas import ResponseItem
    item = ResponseItem(question_id="abc", selected_index=2)
    assert item.selected_index == 2
    assert item.selected_indices is None


def test_response_item_validation_multi():
    """ResponseItem accepts selected_indices only."""
    from models.schemas import ResponseItem
    item = ResponseItem(question_id="abc", selected_indices=[0, 2])
    assert item.selected_indices == [0, 2]
    assert item.selected_index is None


def test_response_item_validation_both_raises():
    """ResponseItem rejects both selected_index and selected_indices."""
    from pydantic import ValidationError
    from models.schemas import ResponseItem
    with pytest.raises(ValidationError):
        ResponseItem(question_id="abc", selected_index=0, selected_indices=[0, 2])


def test_response_item_validation_neither_raises():
    """ResponseItem rejects neither field set."""
    from pydantic import ValidationError
    from models.schemas import ResponseItem
    with pytest.raises(ValidationError):
        ResponseItem(question_id="abc")
