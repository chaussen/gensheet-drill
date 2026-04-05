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
    _to_latex_inner,
    _math_wrap_option,
    _math_wrap_text,
    _clean_math_coefficients,
    _wrap_question_math,
    _build_explanation,
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
    _fallback_params(template, "advanced")  # verify no crash for advanced tier
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


def test_build_question_curated_bank_populated_returns_question():
    """T-7N-03 uses rational_ordering_bank which is populated — must return a valid question."""
    template = load_template_meta("T-7N-03")
    q = build_question(template, {}, "standard")
    assert q is not None
    assert len(q.options) == 4
    assert 0 <= q.correct_index <= 3
    assert q.strand == "Number"


def test_build_question_curated_bank_empty_returns_none():
    """A curated-bank template whose bank has no items must return None gracefully."""
    from unittest.mock import patch
    template = load_template_meta("T-7N-03")
    with patch("services.question_service.load_curated_bank", return_value=[]):
        q = build_question(template, {}, "standard")
    assert q is None


def test_build_question_bad_params_returns_none():
    """If params cause verification to fail, build_question returns None gracefully."""
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
    assert correct_option == r"$\frac{-10}{7}$", \
        f"Expected '$\\frac{{-10}}{{7}}$' as correct option, got '{correct_option}'"
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


# ── Math wrapping unit tests ──────────────────────────────────────────────────

class TestToLatexInner:
    """_to_latex_inner converts plain/sympy notation to LaTeX (no surrounding $)."""

    def test_plain_integer(self):
        assert _to_latex_inner("5") == "5"

    def test_plain_negative(self):
        assert _to_latex_inner("-3") == "-3"

    def test_fraction_positive(self):
        assert _to_latex_inner("3/4") == r"\frac{3}{4}"

    def test_fraction_negative_numerator(self):
        assert _to_latex_inner("-10/7") == r"\frac{-10}{7}"

    def test_fraction_negative_numerator_no_space(self):
        assert _to_latex_inner("-1/2") == r"\frac{-1}{2}"

    def test_fraction_positive_large(self):
        assert _to_latex_inner("22/7") == r"\frac{22}{7}"

    def test_plain_float_unchanged(self):
        # floats are not converted to fractions
        result = _to_latex_inner("1.5")
        assert result == "1.5"

    def test_variable_expression_unchanged(self):
        # expressions without fractions pass through
        result = _to_latex_inner("x + 3")
        assert result == "x + 3"


class TestMathWrapOption:
    """_math_wrap_option wraps option strings that contain math; leaves plain values."""

    def test_plain_integer_unchanged(self):
        assert _math_wrap_option("5") == "5"

    def test_plain_negative_integer_unchanged(self):
        assert _math_wrap_option("-3") == "-3"

    def test_plain_float_unchanged(self):
        assert _math_wrap_option("1.5") == "1.5"

    def test_fraction_wrapped(self):
        assert _math_wrap_option("3/4") == r"$\frac{3}{4}$"

    def test_negative_fraction_wrapped(self):
        assert _math_wrap_option("-10/7") == r"$\frac{-10}{7}$"

    def test_unit_measurement_unchanged(self):
        # "50 cm²" should not be wrapped — it's a measurement
        result = _math_wrap_option("50 cm²")
        assert result == "50 cm²"

    def test_algebraic_expression_wrapped(self):
        # "x + 3" contains a variable so should be wrapped
        result = _math_wrap_option("x + 3")
        assert result.startswith("$") and result.endswith("$")

    def test_already_wrapped_not_double_wrapped(self):
        # If somehow already wrapped, should not add another layer
        already = r"$\frac{-10}{7}$"
        result = _math_wrap_option(already)
        assert result == already


class TestMathWrapText:
    """_math_wrap_text adds $...$ around math in prose question_text / explanation."""

    def test_plain_sentence_unchanged(self):
        text = "What is the value of the expression?"
        assert _math_wrap_text(text) == text

    def test_sqrt_symbol_wrapped(self):
        result = _math_wrap_text("Evaluate √16")
        assert r"$\sqrt{16}$" in result

    def test_cube_root_wrapped(self):
        result = _math_wrap_text("Evaluate ∛8")
        assert r"$\sqrt[3]{8}$" in result

    def test_pi_standalone_wrapped(self):
        result = _math_wrap_text("The area is π times radius squared.")
        assert r"$\pi$" in result

    def test_equation_line_wrapped(self):
        result = _math_wrap_text("Solve: y = 3x + 5")
        assert "$" in result
        assert "3x" in result

    def test_fraction_in_prose_wrapped(self):
        result = _math_wrap_text("Find the value of 3/4 + 1/4.")
        assert r"\frac" in result

    def test_no_double_wrapping(self):
        # Applying twice should not produce nested $...$
        text = "Find √9 and √16."
        once = _math_wrap_text(text)
        twice = _math_wrap_text(once)
        assert once == twice

    def test_times_symbol_wrapped(self):
        result = _math_wrap_text("Calculate 3 × 4.")
        assert r"\times" in result


class TestBuildQuestionMathWrapping:
    """Integration: build_question returns options/question_text with $ wrapping applied."""

    def test_fractional_answer_wrapped(self):
        """T-8A-02 fractional answer becomes $\\frac{...}$."""
        template = load_template_meta("T-8A-02")
        q = build_question(template, {"a": 1, "b": 3, "c": 8, "d": 13, "op1": "+", "op2": "+"}, "standard")
        assert q is not None
        correct = q.options[q.correct_index]
        assert correct == r"$\frac{-10}{7}$"

    def test_integer_answer_plain(self):
        """Integer answers must not be wrapped in dollar signs."""
        template = load_template_meta("T-8A-02")
        q = build_question(template, {"a": 3, "b": 2, "c": 1, "d": 8, "op1": "+", "op2": "+"}, "standard")
        assert q is not None
        correct = q.options[q.correct_index]
        assert correct == "3"
        assert "$" not in correct

    def test_question_text_contains_math(self):
        """question_text for an equation-solve template should contain $...$ math."""
        template = load_template_meta("T-8A-02")
        q = build_question(template, {"a": 3, "b": 2, "c": 1, "d": 8, "op1": "+", "op2": "+"}, "standard")
        assert q is not None
        assert "$" in q.question_text


def test_response_item_validation_neither_is_skipped():
    """ResponseItem with neither selected_index nor selected_indices is valid — represents a skipped question."""
    from models.schemas import ResponseItem
    item = ResponseItem(question_id="abc")
    assert item.selected_index is None
    assert item.selected_indices is None


def test_response_item_validation_both_raises():
    """ResponseItem rejects both selected_index and selected_indices being set simultaneously."""
    from pydantic import ValidationError
    from models.schemas import ResponseItem
    with pytest.raises(ValidationError):
        ResponseItem(question_id="abc", selected_index=0, selected_indices=[1, 2])


# ── New patch templates — build_question ──────────────────────────────────────

def test_build_question_t8n01b_curated_bank():
    """T-8N-01b irrational_recognition_bank is populated — must return a valid question."""
    template = load_template_meta("T-8N-01b")
    q = build_question(template, {}, "standard")
    assert q is not None
    assert q.template_id == "T-8N-01b"
    assert q.strand == "Number"
    assert q.year_level == 8
    # Single-select items have 4 options; multi-select items have 5
    assert len(q.options) in (4, 5)


def test_build_question_t7m05_interior_angle():
    """T-7M-05 interior angle sum of triangle — parametric, verifier must compute 180-a-b."""
    template = load_template_meta("T-7M-05")
    q = build_question(template, {"a": 55, "b": 70}, "standard")
    assert q is not None
    assert q.options[q.correct_index] == "55"


def test_build_question_t9a04b_midpoint():
    """T-9A-04b midpoint formula — correct answer must be formatted as '(x, y)'."""
    template = load_template_meta("T-9A-04b")
    q = build_question(template, {"x1": 2, "y1": 1, "x2": 8, "y2": 7}, "standard")
    assert q is not None
    assert q.options[q.correct_index] == "(5, 4)"


def test_build_question_t9a04c_distance():
    """T-9A-04c distance formula — answer must be a clean integer from Pythagorean triple."""
    template = load_template_meta("T-9A-04c")
    params = {"x1": 0, "y1": 0, "x2": 3, "y2": 4, "scale": 1, "pythagorean_triple": [3, 4, 5]}
    q = build_question(template, params, "standard")
    assert q is not None
    assert q.options[q.correct_index] == "5"


def test_build_question_t9m04b_percentage_error():
    """T-9M-04b percentage error — verifier returns 5.0, _format_answer renders as '5'."""
    template = load_template_meta("T-9M-04b")
    params = {"actual": 200, "error_pct": 5, "direction": "over", "measured": 210}
    q = build_question(template, params, "standard")
    assert q is not None
    # _format_answer converts whole-number floats (5.0) to "5"
    assert q.options[q.correct_index] == "5"


def test_build_question_t7m04_transversal():
    """T-7M-04 now verifies transversal angles — co-interior must give 180-a."""
    template = load_template_meta("T-7M-04")
    q = build_question(template, {"a": 65, "relationship": "co-interior (same-side interior)"}, "standard")
    assert q is not None
    assert q.options[q.correct_index] == "115"

    q2 = build_question(template, {"a": 65, "relationship": "corresponding"}, "standard")
    assert q2 is not None
    assert q2.options[q2.correct_index] == "65"


# ── No-repeat bank item selection ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_curated_bank_no_repeats_within_session():
    """
    When a curated_bank template is selected multiple times in a session,
    different bank items should be used (no item repeated until the pool is exhausted).
    """
    template_t7n03 = load_template_meta("T-7N-03")

    # Pin the template pool to only T-7N-03 so we can count item usage.
    with patch("services.question_service.ai_service.generate_questions",
               new=AsyncMock(return_value=[])), \
         patch("services.question_service.get_templates_for",
               return_value=[template_t7n03]):
        questions = await generate_session_questions(7, "Number", "standard", 5)

    # If we got ≥2 questions from this bank, verify they differ in question_text or options
    if len(questions) >= 2:
        texts = [q.question_text + str(q.options) for q in questions]
        # At least some pairs should differ (bank has >5 items, so all should be unique)
        assert len(set(texts)) == len(texts), \
            "Curated bank produced duplicate questions within the same session"


@pytest.mark.asyncio
async def test_curated_bank_cycles_when_pool_smaller_than_count():
    """
    When the session requests more questions than a bank has items, the service
    cycles through the pool rather than crashing or silently repeating.
    """
    template_t7n03 = load_template_meta("T-7N-03")
    small_bank = [
        {"question_text": "Q1", "correct_answer": "A", "wrong_answers": ["B", "C", "D"]},
        {"question_text": "Q2", "correct_answer": "A", "wrong_answers": ["B", "C", "D"]},
    ]

    with patch("services.question_service.ai_service.generate_questions",
               new=AsyncMock(return_value=[])), \
         patch("services.question_service.get_templates_for",
               return_value=[template_t7n03]), \
         patch("services.question_service.load_curated_bank", return_value=small_bank):
        # Request 5 questions from a 2-item bank
        questions = await generate_session_questions(7, "Number", "standard", 5)

    assert isinstance(questions, list)
    # Should not crash; may produce up to 5 questions (some repeated due to cycling)
    assert len(questions) <= 5


def test_build_question_bank_item_passed_directly():
    """When a specific bank_item is provided, _build_curated_bank_question uses it."""
    template = load_template_meta("T-7N-03")
    specific_item = {
        "question_text": "Which is ascending?",
        "correct_answer": "1/5, 1/4, 1/3",
        "wrong_answers": ["1/3, 1/4, 1/5", "1/4, 1/5, 1/3", "1/3, 1/5, 1/4"],
    }
    q = build_question(template, {}, "standard", bank_item=specific_item)
    assert q is not None
    assert q.question_text == "Which is ascending?"
    assert q.options[q.correct_index] == "1/5, 1/4, 1/3"


def test_build_multi_select_bank_item_passed_directly():
    """When bank_item is provided for a MULTI_SELECT_BANKS template, it uses that item."""
    from services.question_service import _build_multi_select_question
    specific_item = MULTI_SELECT_BANKS["T-8SP-02"]["items"][0]
    q = _build_multi_select_question("T-8SP-02", {}, "advanced", bank_item=specific_item)
    assert q is not None
    assert q.question_type == "multi_select"
    # The question text should match the pinned item
    # (options are shuffled so we can't check order, but the text is fixed)
    assert q.question_text == specific_item["question_text"]


# ── _clean_math_coefficients ─────────────────────────────────────────────────

class TestCleanMathCoefficients:
    """_clean_math_coefficients fixes 1x, -1x, 0x and double-sign artifacts."""

    def test_leading_one_coefficient_removed(self):
        assert _clean_math_coefficients("y = 1x + 4") == "y = x + 4"

    def test_leading_minus_one_coefficient_removed(self):
        assert _clean_math_coefficients("y = -1x + 4") == "y = -x + 4"

    def test_leading_one_in_isolation(self):
        assert _clean_math_coefficients("1x") == "x"

    def test_leading_one_coefficient_not_stripped_from_10x(self):
        # "10x" must not become "0x"
        assert _clean_math_coefficients("10x + 3") == "10x + 3"

    def test_zero_coefficient_with_positive_constant(self):
        assert _clean_math_coefficients("y = 0x + 5") == "y = 5"

    def test_zero_coefficient_with_negative_constant(self):
        assert _clean_math_coefficients("y = 0x - 3") == "y = -3"

    def test_double_negative_sign_collapsed(self):
        assert _clean_math_coefficients("y = 2x - -3") == "y = 2x + 3"

    def test_plus_negative_sign_collapsed(self):
        assert _clean_math_coefficients("y = 2x + -4") == "y = 2x - 4"

    def test_no_change_for_clean_expression(self):
        assert _clean_math_coefficients("y = 3x + 5") == "y = 3x + 5"


# ── _math_wrap_text — newline rendering (Bug 2) ───────────────────────────────

class TestMathWrapTextNewlines:
    """_math_wrap_text must preserve newlines in question text."""

    def test_simultaneous_equation_newline_preserved(self):
        """Simultaneous equation with embedded newline: newline must survive wrapping."""
        text = "Solve the simultaneous equations:\ny = 3x + 5\ny = x + 1"
        result = _math_wrap_text(text)
        assert "\n" in result, "Newline must be preserved in wrapped text"

    def test_newline_not_stripped_in_plain_text(self):
        text = "Step 1: find x\nStep 2: substitute"
        result = _math_wrap_text(text)
        assert "\n" in result

    def test_constant_equation_wrapped(self):
        """'y = 4' (constant RHS) must be wrapped in $...$."""
        result = _math_wrap_text("Solve: y = 4")
        assert "$" in result


# ── Bug 3: coefficient-1 cleaning in option pipeline ─────────────────────────

class TestOptionPipelineCoefficient1:
    """Options containing '1x' must have the 1 stripped before KaTeX wrapping."""

    def test_1x_plus_4_cleaned(self):
        opt = "y = 1x + 4"
        cleaned = _clean_math_coefficients(opt)
        assert cleaned == "y = x + 4"

    def test_wrap_option_after_cleaning_no_1x(self):
        """Full pipeline: clean then wrap — final option must not contain '1x'."""
        opt = "y = 1x + 4"
        result = _math_wrap_option(_clean_math_coefficients(opt))
        assert "1x" not in result

    def test_wrap_question_math_cleans_options(self):
        """_wrap_question_math applies cleaning to all options including distractors."""
        template = load_template_meta("T-8A-03")
        # Gradient of a line through two points — distractors may contain "1x" forms
        # Use params that guarantee a gradient that produces simple options
        q = build_question(template, {"x1": 0, "y1": 0, "x2": 2, "y2": 4}, "standard")
        if q is not None:
            for opt in q.options:
                assert "1x" not in opt, f"Option '{opt}' still contains '1x' coefficient"


# ── Bug 3 extension: explanation cleaned through coefficient pipeline ─────────

class TestExplanationCleaning:
    """Explanations must also be cleaned through _clean_math_coefficients."""

    def test_wrap_question_math_cleans_explanation(self):
        """_wrap_question_math must apply _clean_math_coefficients to explanation."""
        from models.schemas import QuestionObject
        from datetime import datetime, timezone
        # Construct a QuestionObject with an explanation that has "1x"
        q = QuestionObject(
            question_id="test-id",
            template_id="T-9A-03",
            vc_code="VC2M9A03",
            year_level=9,
            strand="Algebra",
            difficulty="standard",
            question_text="A line has gradient 1 and y-intercept 4. What is the equation?",
            options=["y = x + 4", "y = 2x + 4", "y = x - 4", "y = -x + 4"],
            correct_index=0,
            explanation="The equation is y = 1x + 4.",
            params={"m": 1, "c": 4},
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        wrapped = _wrap_question_math(q)
        assert "1x" not in wrapped.explanation, \
            f"'1x' not cleaned from explanation: {wrapped.explanation!r}"


# ── New templates: T-9SP-01 and T-9SP-02 ─────────────────────────────────────

class TestBuildQuestionT9SP01:
    """T-9SP-01: similar triangles — find missing corresponding side."""

    def test_integer_scale_factor_produces_integer_answer(self):
        template = load_template_meta("T-9SP-01")
        # ab=4, scale=2 → de=8; bc=6 → ef=12
        params = {"ab": 4, "scale_factor": 2, "de": 8, "bc": 6}
        q = build_question(template, params, "standard")
        assert q is not None
        assert q.options[q.correct_index] == "12"
        assert q.template_id == "T-9SP-01"
        assert q.year_level == 9
        assert q.strand == "Space"

    def test_non_integer_scale_produces_decimal_answer(self):
        """ab=4, scale=1.5 → de=6; bc=4 → ef=6."""
        template = load_template_meta("T-9SP-01")
        params = {"ab": 4, "scale_factor": 1.5, "de": 6.0, "bc": 4}
        q = build_question(template, params, "standard")
        assert q is not None
        # ef = 4 × 1.5 = 6 (whole number)
        assert q.options[q.correct_index] == "6"

    def test_four_options_all_distinct(self):
        template = load_template_meta("T-9SP-01")
        params = {"ab": 3, "scale_factor": 2, "de": 6, "bc": 5}
        q = build_question(template, params, "standard")
        assert q is not None
        assert len(q.options) == 4
        assert len(set(q.options)) == 4


class TestBuildQuestionT9SP02:
    """T-9SP-02: enlargement — find image or original dimension."""

    def test_enlarge_direction(self):
        template = load_template_meta("T-9SP-02")
        params = {
            "shape": "rectangle", "dimension_name": "length",
            "original": 5, "k": 3, "direction": "enlarge",
        }
        q = build_question(template, params, "standard")
        assert q is not None
        assert q.options[q.correct_index] == "15"

    def test_reduce_direction_question_text(self):
        """When direction='reduce', question text must mention the image dimension."""
        template = load_template_meta("T-9SP-02")
        params = {
            "shape": "square", "dimension_name": "side",
            "original": 4, "k": 3, "direction": "reduce",
        }
        q = build_question(template, params, "advanced")
        assert q is not None
        # image_dim = 4 × 3 = 12; answer = original = 4
        assert q.options[q.correct_index] == "4"
        assert "12" in q.question_text, \
            f"Question text must show image_dim=12, got: {q.question_text!r}"

    def test_resolve_derived_params_sets_image_dim_for_reduce(self):
        template = load_template_meta("T-9SP-02")
        params = {
            "shape": "rectangle", "dimension_name": "width",
            "original": 6, "k": 4, "direction": "reduce",
        }
        resolved = _resolve_derived_params(template, params)
        assert resolved["image_dim"] == 24

    def test_resolve_derived_params_no_image_dim_for_enlarge(self):
        template = load_template_meta("T-9SP-02")
        params = {
            "shape": "rectangle", "dimension_name": "length",
            "original": 5, "k": 3, "direction": "enlarge",
        }
        resolved = _resolve_derived_params(template, params)
        assert "image_dim" not in resolved


# ── Bug 1: pluralization fix — "1 years" → "1 year" ──────────────────────────

class TestPluralYears:
    """_clean_math_coefficients must fix '1 years' → '1 year'."""

    def test_one_years_singular(self):
        assert _clean_math_coefficients("for 1 years") == "for 1 year"

    def test_one_years_in_full_sentence(self):
        result = _clean_math_coefficients(
            "Calculate the compound interest on $2000 at 10% per annum for 1 years."
        )
        assert "1 year." in result
        assert "1 years" not in result

    def test_two_years_unchanged(self):
        assert _clean_math_coefficients("for 2 years") == "for 2 years"

    def test_five_years_unchanged(self):
        assert _clean_math_coefficients("for 5 years") == "for 5 years"

    def test_pluralization_does_not_affect_11_years(self):
        # "11 years" must not be touched (only "1 years" matches)
        assert _clean_math_coefficients("for 11 years") == "for 11 years"


# ── Bug 2: 1-year compound interest forces years >= 2 ────────────────────────

class TestCompoundInterestYearsOverride:
    """build_question for T-9N-03 must never produce compound interest for 1 year."""

    def test_compound_interest_years_1_overridden(self):
        """Params with years=1, interest_type=compound must be upgraded to years=2."""
        template = load_template_meta("T-9N-03")
        params = {"principal": 1000, "rate": 10, "years": 1, "interest_type": "compound"}
        q = build_question(template, params, "advanced")
        assert q is not None
        # The question text must not contain "1 year" with compound interest
        assert "1 year" not in q.question_text or "compound" not in q.question_text.lower()

    def test_compound_interest_years_2_unaffected(self):
        """years=2 compound is valid and must pass through unchanged."""
        template = load_template_meta("T-9N-03")
        params = {"principal": 1000, "rate": 10, "years": 2, "interest_type": "compound"}
        q = build_question(template, params, "advanced")
        assert q is not None
        assert q.correct_index is not None

    def test_simple_interest_years_1_allowed(self):
        """Simple interest with years=1 is mathematically valid — must not be overridden."""
        template = load_template_meta("T-9N-03")
        params = {"principal": 500, "rate": 5, "years": 1, "interest_type": "simple"}
        q = build_question(template, params, "standard")
        assert q is not None
        assert q.correct_index is not None

    def test_correct_answer_compound_years_2(self):
        """T-9N-03 compound interest: 1000 at 10% for 2 years → I = 210."""
        template = load_template_meta("T-9N-03")
        params = {"principal": 1000, "rate": 10, "years": 2, "interest_type": "compound"}
        q = build_question(template, params, "advanced")
        assert q is not None
        correct = q.options[q.correct_index]
        assert correct == "210"


# ── Bug 4: T-9N-03 explanation shows step-by-step working ────────────────────

class TestBuildExplanationT9N03:
    """_build_explanation for T-9N-03 must show formula, substituted values, result."""

    def _template(self):
        return load_template_meta("T-9N-03")

    def test_simple_interest_explanation_contains_formula(self):
        params = {"principal": 1000, "rate": 6, "years": 3, "interest_type": "simple"}
        explanation = _build_explanation(self._template(), params, 180.0)
        assert "I = P" in explanation
        assert "1000" in explanation
        assert "6" in explanation
        assert "3" in explanation
        assert "$180.00" in explanation

    def test_simple_interest_explanation_not_generic(self):
        params = {"principal": 1000, "rate": 6, "years": 3, "interest_type": "simple"}
        explanation = _build_explanation(self._template(), params, 180.0)
        # Must not be the old generic placeholder
        assert explanation != "The correct answer is 180.0. (Simple and compound interest)"

    def test_compound_interest_explanation_contains_formula(self):
        params = {"principal": 1000, "rate": 10, "years": 2, "interest_type": "compound"}
        explanation = _build_explanation(self._template(), params, 210.0)
        assert "A = P" in explanation
        assert "1000" in explanation
        assert "10" in explanation
        assert "2" in explanation
        assert "$210.00" in explanation
        assert "interest = A" in explanation

    def test_compound_interest_explanation_shows_total_amount(self):
        """Explanation must include the intermediate total amount (A), not just interest."""
        params = {"principal": 1000, "rate": 10, "years": 2, "interest_type": "compound"}
        explanation = _build_explanation(self._template(), params, 210.0)
        # A = 1000 × (1.10)^2 = 1210
        assert "$1210.00" in explanation

    def test_other_template_returns_generic(self):
        """Non-T-9N-03 templates still return the generic explanation."""
        template = load_template_meta("T-7N-01")
        explanation = _build_explanation(template, {"n": 64}, 8)
        assert "The correct answer is 8" in explanation

    def test_explanation_singular_year_label(self):
        """Explanation must use 'year' (not 'years') when years=1."""
        params = {"principal": 500, "rate": 5, "years": 1, "interest_type": "simple"}
        explanation = _build_explanation(self._template(), params, 25.0)
        assert "1 year " in explanation
        assert "1 years" not in explanation


# ── T-9N-03 build_question integration ───────────────────────────────────────

class TestBuildQuestionT9N03:
    """T-9N-03: simple/compound interest question end-to-end."""

    def test_simple_interest_produces_valid_question(self):
        template = load_template_meta("T-9N-03")
        q = build_question(template, {"principal": 500, "rate": 5, "years": 3, "interest_type": "simple"}, "standard")
        assert q is not None
        assert q.year_level == 9
        assert q.strand == "Number"
        assert q.vc_code == "VC2M9N03"
        assert len(q.options) == 4

    def test_simple_interest_correct_answer(self):
        """500 at 5% for 3 years simple interest = 75 (float formatted as plain int)."""
        template = load_template_meta("T-9N-03")
        q = build_question(template, {"principal": 500, "rate": 5, "years": 3, "interest_type": "simple"}, "standard")
        assert q is not None
        assert q.options[q.correct_index] == "75"

    def test_compound_interest_correct_answer(self):
        """1000 at 10% for 2 years compound: A = 1210, I = 210."""
        template = load_template_meta("T-9N-03")
        q = build_question(template, {"principal": 1000, "rate": 10, "years": 2, "interest_type": "compound"}, "advanced")
        assert q is not None
        assert q.options[q.correct_index] == "210"

    def test_explanation_attached_to_question(self):
        """build_question must attach the formula explanation, not a generic placeholder."""
        template = load_template_meta("T-9N-03")
        q = build_question(template, {"principal": 500, "rate": 5, "years": 3, "interest_type": "simple"}, "standard")
        assert q is not None
        assert "I = P" in q.explanation


class TestBuildQuestionT8N05:
    """
    Regression tests for the T-8N-05 variant/change_type mismatch bug.

    Root cause: context_variants for T-8N-05 hard-code a direction ("increases" or
    "discounted") instead of using {change_type}.  When the randomly-selected variant's
    direction differed from params["change_type"], the verifier computed the answer for
    the wrong direction — so the correct answer was absent from the options and three
    wrong-direction distractors appeared instead.
    """

    def _build(self, original, pct, change_type):
        template = load_template_meta("T-8N-05")
        params = {"original": original, "pct": pct, "change_type": change_type}
        return build_question(template, params, "standard")

    # ── Correctness: correct answer must be in options ─────────────────────────

    def test_correct_answer_matches_question_direction(self):
        """
        Core invariant: whatever direction the question text states, the correct answer
        must be consistent with it. Tested over 60 builds to cover all variant paths.

        - "increase" in question → correct > original
        - "discount"/"decrease" in question → correct < original
        - base template with {change_type} already substituted → read direction from text
        """
        template = load_template_meta("T-8N-05")
        original = 200
        mismatches = []
        for change_type in ("increased", "decreased"):
            for _ in range(30):
                q = build_question(template, {"original": original, "pct": 15, "change_type": change_type}, "standard")
                if q is None:
                    continue
                correct_val = float(q.options[q.correct_index])
                text_lower = q.question_text.lower()
                if "increase" in text_lower:
                    if correct_val <= original:
                        mismatches.append(
                            f"text='...increases...' but correct={correct_val} ≤ {original}: {q.options}"
                        )
                elif "discount" in text_lower or "decrease" in text_lower:
                    if correct_val >= original:
                        mismatches.append(
                            f"text='...decreases...' but correct={correct_val} ≥ {original}: {q.options}"
                        )
        assert not mismatches, "Direction/answer mismatches found:\n" + "\n".join(mismatches)

    def test_correct_index_valid_range(self):
        for change_type in ("increased", "decreased"):
            q = self._build(100, 20, change_type)
            assert q is not None
            assert 0 <= q.correct_index < len(q.options)

    def test_four_options_all_distinct(self):
        for original, pct, ct in [(100, 10, "increased"), (200, 25, "decreased"), (50, 50, "increased")]:
            q = self._build(original, pct, ct)
            assert q is not None
            assert len(set(q.options)) == 4, f"Duplicate options: {q.options}"

    # ── Variant reconciliation: question text must match the correct answer ────

    def test_question_text_increase_implies_increase_answer(self):
        """If question text says 'increases', correct answer must be > original."""
        template = load_template_meta("T-8N-05")
        # Force the "increases" context variant by directly passing change_type="decreased"
        # (the bug scenario: params say decrease but variant might say increase).
        # We run build_question 50 times to catch the random variant selection.
        mismatch_found = False
        for _ in range(50):
            q = build_question(template, {"original": 200, "pct": 15, "change_type": "decreased"}, "standard")
            if q is None:
                continue
            if "increase" in q.question_text.lower():
                correct_val = float(q.options[q.correct_index])
                if correct_val < 200:
                    mismatch_found = True
                    break
        assert not mismatch_found, (
            "Question text said 'increases' but correct answer was less than original — "
            "variant/change_type reconciliation is not working."
        )

    # ── Distractor quality: test the distractor engine directly ──────────────
    # (Testing through build_question is fragile because variant selection is random
    #  and changes which direction is "correct". Call the engine directly instead.)

    def test_op_swap_distractor_is_opposite_direction(self):
        """For 200 increases 15% (correct=230), op-swap distractor must be 170."""
        from services.verification import VerificationEngine
        eng = VerificationEngine()
        distractors = eng.generate_distractors(
            "T-8N-05", 230, {"original": 200, "pct": 15, "change_type": "increased"}
        )
        assert "170" in distractors, (
            f"Expected op-swap distractor '170', got: {distractors}"
        )

    def test_raw_arithmetic_distractor_present(self):
        """For 200 increases 15% (correct=230), raw-arithmetic distractor must be 215 (200+15)."""
        from services.verification import VerificationEngine
        eng = VerificationEngine()
        distractors = eng.generate_distractors(
            "T-8N-05", 230, {"original": 200, "pct": 15, "change_type": "increased"}
        )
        assert "215" in distractors, (
            f"Expected raw-arithmetic distractor '215' (200+15), got: {distractors}"
        )

    def test_distractors_no_collision_when_original_is_100(self):
        """original=100 causes raw_arith (100+20=120) to equal correct (120). Must not duplicate."""
        from services.verification import VerificationEngine
        eng = VerificationEngine()
        distractors = eng.generate_distractors(
            "T-8N-05", 120, {"original": 100, "pct": 20, "change_type": "increased"}
        )
        assert len(set(distractors)) == 3, f"Duplicate distractors: {distractors}"
        assert "120" not in distractors, f"Correct answer '120' appeared as distractor: {distractors}"
