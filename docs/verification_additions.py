"""
verification_additions.py
=========================
New verifier functions and registry entries to add to docs/verification.py.

HOW TO APPLY:
  1. Add each function below to the VerificationEngine class body,
     after the existing methods (before the _registry property).
  2. Add the registry entries to the _registry dict inside the @property.
  3. Run: python3 docs/verification.py  — all existing + new tests must pass.

NEW TESTS to add to the __main__ block:
    ("T-7M-04",  {"a": 65, "relationship": "corresponding"},     65),
    ("T-7M-04",  {"a": 65, "relationship": "alternate"},         65),
    ("T-7M-04",  {"a": 65, "relationship": "co-interior (same-side interior)"}, 115),
    ("T-7M-04b", {"a": 65, "relationship": "supplementary"},     115),
    ("T-7M-04b", {"a": 40, "relationship": "complementary"},     50),
    ("T-7M-04b", {"a": 73, "relationship": "vertically opposite"}, 73),
    ("T-7M-05",  {"a": 55, "b": 70},                             55),
    ("T-8P-01",  {"p_numerator": 3, "p_denominator": 5},         "2/5"),
    ("T-9A-04b", {"x1": 2, "y1": 1, "x2": 8, "y2": 7},          "(5, 4)"),
    ("T-9A-04c", {"x1": 0, "y1": 0, "x2": 3, "y2": 4, "scale": 1, "pythagorean_triple": [3,4,5]}, 5),
    ("T-9M-04b", {"actual": 200, "error_pct": 5, "direction": "over"}, 5.0),
"""

import math
from fractions import Fraction


# ─── NEW VERIFIER FUNCTIONS ────────────────────────────────────────────────
# Add these methods to the VerificationEngine class.


def _transversal_angle(self, p):
    """
    Angle relationships when parallel lines are cut by a transversal.
    corresponding → equal
    alternate      → equal
    co-interior    → supplementary (180 - a)
    """
    a = int(p["a"])
    rel = p["relationship"].lower()
    if "corresponding" in rel:
        return a
    elif "alternate" in rel:
        return a
    elif "co-interior" in rel or "co interior" in rel or "same-side" in rel:
        return 180 - a
    raise ValueError(f"Unknown transversal relationship: {rel}")


def _interior_angle_sum_triangle(self, p):
    """
    Given two angles of a triangle, return the third.
    Third angle = 180 - a - b.
    Raises if result ≤ 0 (degenerate triangle).
    """
    a, b = int(p["a"]), int(p["b"])
    third = 180 - a - b
    if third <= 0:
        raise ValueError(f"Degenerate triangle: {a} + {b} >= 180")
    return third


def _complementary_events_prob(self, p):
    """
    P(not A) = 1 - P(A).
    Input: p_numerator and p_denominator of P(A) as a fraction.
    Returns simplified fraction string.
    """
    pn = int(p["p_numerator"])
    pd = int(p["p_denominator"])
    if pn >= pd:
        raise ValueError(f"P(A) = {pn}/{pd} is not a valid probability < 1")
    result = Fraction(pd - pn, pd)
    return str(result)


def _midpoint_formula(self, p):
    """
    Midpoint of segment from (x1,y1) to (x2,y2).
    Returns string "(mx, my)".
    Guarantees integer coordinates when (x2-x1) and (y2-y1) are both even.
    """
    x1, y1 = int(p["x1"]), int(p["y1"])
    x2, y2 = int(p["x2"]), int(p["y2"])
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    # Return as integer if clean, else 1dp decimal
    mx_str = str(int(mx)) if mx == int(mx) else f"{mx:.1f}"
    my_str = str(int(my)) if my == int(my) else f"{my:.1f}"
    return f"({mx_str}, {my_str})"


def _distance_formula(self, p):
    """
    Distance between (x1,y1) and (x2,y2) using Pythagorean theorem.
    Uses pre-validated Pythagorean triples so result is always a clean integer.
    """
    x1, y1 = int(p["x1"]), int(p["y1"])
    x2, y2 = int(p["x2"]), int(p["y2"])
    scale = int(p.get("scale", 1))
    triple = p["pythagorean_triple"]
    # The hypotenuse of the triple, scaled
    hypotenuse = triple[2] * scale
    # Verify computation matches (sanity check)
    computed = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if abs(computed - hypotenuse) > 0.01:
        # Fall back to direct computation, rounded
        return round(computed, 2)
    return hypotenuse


def _percentage_error(self, p):
    """
    Percentage error = |measured - actual| / actual × 100.
    Returns float rounded to 1dp.
    """
    measured = float(p["measured"])
    actual = float(p["actual"])
    if actual == 0:
        raise ValueError("Actual value cannot be zero")
    pct_error = abs(measured - actual) / actual * 100
    return round(pct_error, 1)


# ─── REGISTRY ADDITIONS ───────────────────────────────────────────────────
# Add these entries to the _registry @property dict.
# Replace the existing entries for T-7M-04 and T-8P-01.

# REGISTRY_ADDITIONS — paste these into the _registry @property dict in verification.py:
#
#   "T-7M-04":   self._transversal_angle,
#   "T-7M-04b":  self._angle_relationship,    # reuses existing function
#   "T-7M-05":   self._interior_angle_sum_triangle,
#   "T-8P-01":   self._complementary_events_prob,
#   "T-9A-04b":  self._midpoint_formula,
#   "T-9A-04c":  self._distance_formula,
#   "T-9M-04b":  self._percentage_error,
#
# T-8N-01b is curated_bank — add "T-8N-01b" to the curated_template_ids set.

# NOTE: T-8N-01b uses curated_bank mode. Add its bank key to the
# curated_template_ids set in VerificationEngine:
#   self.curated_template_ids.add("T-8N-01b")


# ─── QUICK TESTS ──────────────────────────────────────────────────────────
# Run standalone to verify new functions only.
if __name__ == "__main__":

    class MockEngine:
        """Minimal wrapper to test new functions without the full engine."""
        pass

    eng = MockEngine()

    new_tests = [
        (_transversal_angle,          eng, {"a": 65, "relationship": "corresponding"},                  65),
        (_transversal_angle,          eng, {"a": 65, "relationship": "alternate"},                      65),
        (_transversal_angle,          eng, {"a": 65, "relationship": "co-interior (same-side interior)"}, 115),
        (_interior_angle_sum_triangle,eng, {"a": 55, "b": 70},                                          55),
        (_interior_angle_sum_triangle,eng, {"a": 90, "b": 45},                                          45),
        (_complementary_events_prob,  eng, {"p_numerator": 3, "p_denominator": 5},                      "2/5"),
        (_complementary_events_prob,  eng, {"p_numerator": 1, "p_denominator": 4},                      "3/4"),
        (_complementary_events_prob,  eng, {"p_numerator": 7, "p_denominator": 10},                     "3/10"),
        (_midpoint_formula,           eng, {"x1": 2, "y1": 1, "x2": 8, "y2": 7},                       "(5, 4)"),
        (_midpoint_formula,           eng, {"x1": -4, "y1": 2, "x2": 6, "y2": -8},                     "(1, -3)"),
        (_midpoint_formula,           eng, {"x1": 0, "y1": 0, "x2": 10, "y2": 6},                      "(5, 3)"),
        (_distance_formula,           eng, {"x1": 0, "y1": 0, "x2": 3, "y2": 4, "scale": 1, "pythagorean_triple": [3,4,5]}, 5),
        (_distance_formula,           eng, {"x1": 0, "y1": 0, "x2": 6, "y2": 8, "scale": 2, "pythagorean_triple": [3,4,5]}, 10),
        (_distance_formula,           eng, {"x1": 1, "y1": 1, "x2": 6, "y2": 13, "scale": 1, "pythagorean_triple": [5,12,13]}, 13),
        (_percentage_error,           eng, {"measured": 210, "actual": 200, "direction": "over"},       5.0),
        (_percentage_error,           eng, {"measured": 95,  "actual": 100, "direction": "under"},      5.0),
        (_percentage_error,           eng, {"measured": 88,  "actual": 80,  "direction": "over"},       10.0),
    ]

    passed, failed = 0, 0
    for fn, engine, params, expected in new_tests:
        try:
            result = fn(engine, params)
            ok = str(result) == str(expected) or result == expected
        except Exception as e:
            result = f"ERROR: {e}"
            ok = False
        status = "✅" if ok else "❌"
        if ok: passed += 1
        else: failed += 1
        fn_name = fn.__name__
        print(f"{status} {fn_name}({params}) → expected={expected}, got={result}")

    print(f"\n{passed}/{passed+failed} tests passed")
