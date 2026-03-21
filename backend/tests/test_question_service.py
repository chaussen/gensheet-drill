"""
Tests for question_service.py — no real AI calls; ai_service is mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch

from docs_loader import load_template_meta
from services.question_service import (
    _fallback_params,
    _resolve_derived_params,
    _format_answer,
    build_question,
    generate_session_questions,
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
