"""Tests for the VerificationEngine — covers all verifier functions in the registry."""
import pytest
from services.verification import VerificationEngine

engine = VerificationEngine()


# ── Year 7 Number ──────────────────────────────────────────────────────────────

def test_sqrt_perfect():
    assert engine.verify("T-7N-01", {"n": 64}) == 8
    assert engine.verify("T-7N-01", {"n": 144}) == 12
    assert engine.verify("T-7N-01", {"n": 4}) == 2


def test_prime_factorisation():
    result = engine.verify("T-7N-02", {"n": 12})
    assert result == "2^2 × 3"
    result2 = engine.verify("T-7N-02", {"n": 18})
    assert result2 == "2 × 3^2"


def test_round_decimal():
    assert engine.verify("T-7N-04", {"x": 3.456, "dp": 2}) == 3.46
    assert engine.verify("T-7N-04", {"x": 7.891, "dp": 1}) == 7.9


def test_fraction_multiply():
    result = engine.verify("T-7N-05", {"a": 1, "b": 2, "c": 3, "d": 4, "op": "×"})
    assert result == "3/8"


def test_fraction_divide():
    result = engine.verify("T-7N-05", {"a": 1, "b": 2, "c": 1, "d": 4, "op": "÷"})
    assert result == "2"  # 1/2 ÷ 1/4 = 2


def test_percentage_of_amount():
    assert engine.verify("T-7N-07", {"pct": 25, "amount": 200}) == 50
    assert engine.verify("T-7N-07", {"pct": 10, "amount": 80}) == 8


def test_integer_operation():
    assert engine.verify("T-7N-08", {"a": -5, "b": 3, "op": "+"}) == -2
    assert engine.verify("T-7N-08", {"a": 7, "b": -3, "op": "-"}) == 10


def test_ratio_share():
    assert engine.verify("T-7N-09", {"a": 2, "b": 3, "total": 50}) == 30
    assert engine.verify("T-7N-09", {"a": 1, "b": 4, "total": 20}) == 16


# ── Year 7 Algebra ─────────────────────────────────────────────────────────────

def test_solve_linear_one_var():
    # 2x + 3 = 11 → x = 4
    assert engine.verify("T-7A-02", {"a": 2, "b": 3, "c": 11, "op": "+"}) == 4
    # 3x - 6 = 9 → x = 5
    assert engine.verify("T-7A-02", {"a": 3, "b": 6, "c": 9, "op": "-"}) == 5


def test_arithmetic_sequence_next():
    # t1=2, d=3 → 5th term = 2 + 4×3 = 14
    assert engine.verify("T-7A-03", {"t1": 2, "d": 3}) == 14


# ── Year 7 Measurement ─────────────────────────────────────────────────────────

def test_area_triangle():
    assert engine.verify("T-7M-01", {"shape": "triangle", "b": 10, "h": 6}) == 30


def test_area_parallelogram():
    assert engine.verify("T-7M-01", {"shape": "parallelogram", "b": 8, "h": 5}) == 40


def test_volume_rectangular_prism():
    assert engine.verify("T-7M-02", {"l": 4, "w": 3, "h": 5}) == 60


def test_transversal_angle_corresponding():
    # T-7M-04 now tests transversal relationships (corresponding → equal)
    assert engine.verify("T-7M-04", {"a": 65, "relationship": "corresponding"}) == 65


def test_transversal_angle_alternate():
    assert engine.verify("T-7M-04", {"a": 65, "relationship": "alternate"}) == 65


def test_transversal_angle_co_interior():
    assert engine.verify("T-7M-04", {"a": 65, "relationship": "co-interior (same-side interior)"}) == 115


# T-7M-04b now covers supplementary, complementary, vertically opposite
def test_angle_supplementary():
    assert engine.verify("T-7M-04b", {"a": 65, "relationship": "supplementary"}) == 115


def test_angle_complementary():
    assert engine.verify("T-7M-04b", {"a": 30, "relationship": "complementary"}) == 60


def test_angle_vertically_opposite():
    assert engine.verify("T-7M-04b", {"a": 73, "relationship": "vertically opposite"}) == 73


# T-7M-05: interior angle sum of triangle
def test_interior_angle_sum_triangle():
    assert engine.verify("T-7M-05", {"a": 55, "b": 70}) == 55
    assert engine.verify("T-7M-05", {"a": 90, "b": 45}) == 45


def test_interior_angle_sum_triangle_degenerate_raises():
    with pytest.raises(ValueError, match="Degenerate"):
        engine.verify("T-7M-05", {"a": 90, "b": 91})


# ── Year 7 Probability ────────────────────────────────────────────────────────

def test_simple_probability():
    result = engine.verify("T-7P-01", {"r": 3, "b": 7})
    assert result == "3/10"


def test_complementary_probability():
    result = engine.verify("T-7P-03", {"p_numerator": 1, "p_denominator": 4})
    assert result == "3/4"


# ── Year 8 Number ─────────────────────────────────────────────────────────────

def test_hcf():
    assert engine.verify("T-8N-03", {"a": 12, "b": 18, "measure": "HCF"}) == 6


def test_lcm():
    assert engine.verify("T-8N-03", {"a": 4, "b": 6, "measure": "LCM"}) == 12


def test_percentage_change_increase():
    result = engine.verify("T-8N-05", {"original": 200, "pct": 10, "change_type": "increased"})
    assert result == 220


def test_percentage_change_decrease():
    result = engine.verify("T-8N-05", {"original": 100, "pct": 25, "change_type": "decreased"})
    assert result == 75


# ── Year 8 Algebra ─────────────────────────────────────────────────────────────

def test_expand_simplify():
    # 2(3x + 5) = 6*x + 10
    result = engine.verify("T-8A-01", {"a": 2, "b": 3, "c": 5, "op": "+"})
    assert "6" in result and "10" in result


def test_solve_linear_both_sides():
    # 3x + 2 = x + 8 → x = 3
    assert engine.verify("T-8A-02", {"a": 3, "b": 2, "c": 1, "d": 8, "op1": "+", "op2": "+"}) == 3


def test_solve_linear_both_sides_fractional_returns_rational():
    """
    Regression for the int()-truncation bug: 1x + 3 = 8x + 13 → x = -10/7.
    Before the fix, int(Rational(-10, 7)) = -1 was returned silently.
    After the fix, the verifier returns sympy.Rational(-10, 7) so the caller
    can decide how to render it.
    """
    from sympy import Rational
    result = engine.verify("T-8A-02", {"a": 1, "b": 3, "c": 8, "d": 13, "op1": "+", "op2": "+"})
    assert result == Rational(-10, 7), f"Expected -10/7, got {result!r}"
    # Must NOT silently truncate to -1
    assert result != -1


def test_solve_linear_both_sides_with_subtraction_op():
    # 5x - 4 = 2x + 5 → x = 3
    assert engine.verify("T-8A-02", {"a": 5, "b": 4, "c": 2, "d": 5, "op1": "-", "op2": "+"}) == 3


def test_gradient_two_points():
    # (1,2) to (3,8): rise=6, run=2, gradient=3
    result = engine.verify("T-8A-03", {"x1": 1, "y1": 2, "x2": 3, "y2": 8})
    assert str(result) == "3"


# ── Year 8 Measurement ────────────────────────────────────────────────────────

def test_pythagoras_hypotenuse():
    result = engine.verify("T-8M-06", {"triple_family": [3, 4, 5], "scale": 2, "unknown_side": "hypotenuse"})
    assert result == 10


def test_circle_circumference():
    import math
    result = engine.verify("T-8M-03", {"dimension_type": "radius", "value": 5, "measure": "circumference"})
    assert abs(result - 2 * math.pi * 5) < 0.01


def test_circle_area():
    import math
    result = engine.verify("T-8M-03", {"dimension_type": "radius", "value": 4, "measure": "area"})
    assert abs(result - math.pi * 16) < 0.01


# ── Year 9 ───────────────────────────────────────────────────────────────────

def test_simultaneous_equations():
    # y = 2x + 1, y = -x + 7 → x = 2
    result = engine.verify("T-9A-04", {"a": 2, "b": 1, "c": -1, "d": 7})
    assert result == 2


def test_simultaneous_equations_fractional_returns_rational():
    """
    Same truncation bug as T-8A-02: y = 3x + 1, y = x + 2 → x = 1/2.
    Must return Rational(1, 2), not the truncated 0.
    """
    from sympy import Rational
    result = engine.verify("T-9A-04", {"a": 3, "b": 1, "c": 1, "d": 2})
    assert result == Rational(1, 2), f"Expected 1/2, got {result!r}"
    assert result != 0


def test_trigonometry():
    result = engine.verify("T-9M-03", {
        "theta": 30, "value": 10,
        "known_side": "hypotenuse", "unknown_side": "opposite side"
    })
    assert abs(result - 5.0) < 0.1


def test_similar_figures():
    # Scale factor 2: side 3 → 6
    result = engine.verify("T-9M-04", {"a": 3, "b": 6, "c": 5})
    assert result == 10


# ── T-8P-01: complementary events ────────────────────────────────────────────

def test_complementary_events_prob():
    assert engine.verify("T-8P-01", {"p_numerator": 3, "p_denominator": 5}) == "2/5"
    assert engine.verify("T-8P-01", {"p_numerator": 1, "p_denominator": 4}) == "3/4"
    assert engine.verify("T-8P-01", {"p_numerator": 7, "p_denominator": 10}) == "3/10"


def test_complementary_events_prob_invalid_raises():
    with pytest.raises(ValueError, match="not a valid probability"):
        engine.verify("T-8P-01", {"p_numerator": 5, "p_denominator": 5})


# ── T-9A-04b: midpoint formula ────────────────────────────────────────────────

def test_midpoint_formula():
    assert engine.verify("T-9A-04b", {"x1": 2, "y1": 1, "x2": 8, "y2": 7}) == "(5, 4)"
    assert engine.verify("T-9A-04b", {"x1": -4, "y1": 2, "x2": 6, "y2": -8}) == "(1, -3)"
    assert engine.verify("T-9A-04b", {"x1": 0, "y1": 0, "x2": 10, "y2": 6}) == "(5, 3)"


# ── T-9A-04c: distance formula ────────────────────────────────────────────────

def test_distance_formula():
    result = engine.verify("T-9A-04c", {
        "x1": 0, "y1": 0, "x2": 3, "y2": 4,
        "scale": 1, "pythagorean_triple": [3, 4, 5]
    })
    assert result == 5

    result2 = engine.verify("T-9A-04c", {
        "x1": 0, "y1": 0, "x2": 6, "y2": 8,
        "scale": 2, "pythagorean_triple": [3, 4, 5]
    })
    assert result2 == 10

    result3 = engine.verify("T-9A-04c", {
        "x1": 1, "y1": 1, "x2": 6, "y2": 13,
        "scale": 1, "pythagorean_triple": [5, 12, 13]
    })
    assert result3 == 13


# ── T-9M-04b: percentage error ────────────────────────────────────────────────

def test_percentage_error():
    assert engine.verify("T-9M-04b", {"measured": 210, "actual": 200, "direction": "over"}) == 5.0
    assert engine.verify("T-9M-04b", {"measured": 95, "actual": 100, "direction": "under"}) == 5.0
    assert engine.verify("T-9M-04b", {"measured": 88, "actual": 80, "direction": "over"}) == 10.0


def test_percentage_error_zero_actual_raises():
    with pytest.raises(ValueError, match="cannot be zero"):
        engine.verify("T-9M-04b", {"measured": 5, "actual": 0, "direction": "over"})


# ── Curated template IDs set ──────────────────────────────────────────────────

def test_curated_template_ids_includes_t8n01b():
    assert "T-8N-01b" in engine.curated_template_ids


# ── T-9SP-01: similar triangles — missing corresponding side ─────────────────

def test_similar_triangles_integer_answer():
    """ab=4, de=8 (scale=2), bc=6 → ef=12."""
    result = engine.verify("T-9SP-01", {"ab": 4, "de": 8, "bc": 6})
    assert result == "12"


def test_similar_triangles_decimal_answer():
    """ab=4, de=6 (scale=1.5), bc=8 → ef=12.0 → '12'."""
    result = engine.verify("T-9SP-01", {"ab": 4, "de": 6, "bc": 8})
    assert result == "12"


def test_similar_triangles_half_scale():
    """ab=6, de=3 (scale=0.5), bc=10 → ef=5."""
    result = engine.verify("T-9SP-01", {"ab": 6, "de": 3, "bc": 10})
    assert result == "5"


def test_similar_triangles_one_dp_answer():
    """ab=4, de=6 (scale=1.5), bc=3 → ef=4.5 (1 dp)."""
    result = engine.verify("T-9SP-01", {"ab": 4, "de": 6, "bc": 3})
    assert result == "4.5"


# ── T-9SP-02: enlargement / reduction ─────────────────────────────────────────

def test_enlargement_basic():
    """original=5, k=3, direction=enlarge → answer=15."""
    result = engine.verify("T-9SP-02", {"original": 5, "k": 3, "direction": "enlarge"})
    assert result == "15"


def test_enlargement_default_direction():
    """Omitting direction defaults to 'enlarge': original=4, k=4 → 16."""
    result = engine.verify("T-9SP-02", {"original": 4, "k": 4})
    assert result == "16"


def test_enlargement_reduce_returns_original():
    """direction='reduce': image_dim=original×k is shown; answer=original."""
    result = engine.verify("T-9SP-02", {"original": 6, "k": 3, "direction": "reduce"})
    assert result == "6"


def test_enlargement_large_scale():
    """original=12, k=10, direction=enlarge → 120."""
    result = engine.verify("T-9SP-02", {"original": 12, "k": 10, "direction": "enlarge"})
    assert result == "120"


# ── T-7A-04: relationship type curated bank ───────────────────────────────────

def test_t7a04_in_curated_template_ids():
    """T-7A-04 is a curated_bank template — must not have a verifier registration."""
    assert "T-7A-04" in engine.curated_template_ids


# ── T-9N-03: simple and compound interest ────────────────────────────────────

def test_simple_interest_basic():
    """500 at 5% for 3 years simple interest = 75.0."""
    result = engine.verify("T-9N-03", {
        "principal": 500, "rate": 5, "years": 3, "interest_type": "simple"
    })
    assert result == 75.0


def test_simple_interest_one_year():
    """Simple interest for 1 year: 1000 at 10% = 100.0."""
    result = engine.verify("T-9N-03", {
        "principal": 1000, "rate": 10, "years": 1, "interest_type": "simple"
    })
    assert result == 100.0


def test_compound_interest_two_years():
    """1000 at 10% for 2 years compound: A = 1210, I = 210.0."""
    result = engine.verify("T-9N-03", {
        "principal": 1000, "rate": 10, "years": 2, "interest_type": "compound"
    })
    assert result == 210.0


def test_compound_interest_three_years():
    """1000 at 6% for 3 years compound: A = 1000*(1.06)^3 ≈ 1191.02, I ≈ 191.02."""
    result = engine.verify("T-9N-03", {
        "principal": 1000, "rate": 6, "years": 3, "interest_type": "compound"
    })
    assert abs(result - 191.02) < 0.01


def test_compound_vs_simple_differ_for_multi_year():
    """For years > 1, compound interest must exceed simple interest on the same principal."""
    simple = engine.verify("T-9N-03", {
        "principal": 2000, "rate": 8, "years": 3, "interest_type": "simple"
    })
    compound = engine.verify("T-9N-03", {
        "principal": 2000, "rate": 8, "years": 3, "interest_type": "compound"
    })
    assert compound > simple, "Compound interest must exceed simple interest over multiple years"


def test_compound_equals_simple_for_one_year():
    """For exactly 1 year, compound and simple interest are numerically equal."""
    simple = engine.verify("T-9N-03", {
        "principal": 1000, "rate": 10, "years": 1, "interest_type": "simple"
    })
    compound = engine.verify("T-9N-03", {
        "principal": 1000, "rate": 10, "years": 1, "interest_type": "compound"
    })
    assert simple == compound, (
        "1-year compound interest must equal simple interest — "
        "this is why build_question overrides years=1 for compound questions"
    )


# ── Unknown template raises ───────────────────────────────────────────────────

def test_unknown_template_raises():
    with pytest.raises(ValueError, match="No verifier registered"):
        engine.verify("T-FAKE-99", {})
