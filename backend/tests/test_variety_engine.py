"""
test_variety_engine.py
======================
Unit tests for the 3-layer variety engine introduced to fix Y9 Number
question repetition.

Layer 1: _select_templates_balanced / _select_templates_balanced_mixed
Layer 2: companions config (get_companion_ids, should_expand, max_companions)
Layer 3: _ensure_param_diversity / _param_fingerprint
"""
import math
import sys
import os
from collections import Counter
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Layer 1: Balanced template selection ─────────────────────────────────────

from services.question_service import (
    _select_templates_balanced,
    _select_templates_balanced_mixed,
    _param_fingerprint,
    _ensure_param_diversity,
    _fallback_params,
)


def make_templates(n: int, strand: str = "Number") -> list[dict]:
    return [{"id": f"T-{i}", "strand": strand} for i in range(n)]


class TestSelectTemplatesBalanced:
    def test_correct_length(self):
        templates = make_templates(4)
        result = _select_templates_balanced(templates, 10)
        assert len(result) == 10

    def test_cap_invariant_over_many_runs(self):
        """No template should appear more than ceil(10/4)=3 times in a 10-Q session."""
        templates = make_templates(4)
        cap = math.ceil(10 / 4)  # 3
        for _ in range(300):
            selected = _select_templates_balanced(templates, 10)
            counts = Counter(t["id"] for t in selected)
            assert max(counts.values()) <= cap, (
                f"Template exceeded cap={cap}: {dict(counts)}"
            )

    def test_all_templates_represented(self):
        """With 4 templates and count=10, every template must appear at least once."""
        templates = make_templates(4)
        for _ in range(100):
            selected = _select_templates_balanced(templates, 10)
            ids = {t["id"] for t in selected}
            assert ids == {t["id"] for t in templates}, (
                "Not all templates appeared in the selection"
            )

    def test_count_less_than_or_equal_templates_max_one_each(self):
        """count ≤ n: each template should appear at most once."""
        templates = make_templates(6)
        for _ in range(100):
            selected = _select_templates_balanced(templates, 5)
            counts = Counter(t["id"] for t in selected)
            assert max(counts.values()) <= 1

    def test_single_template_fills_all_slots(self):
        templates = make_templates(1)
        result = _select_templates_balanced(templates, 10)
        assert len(result) == 10
        assert all(t["id"] == "T-0" for t in result)

    def test_empty_available_returns_empty(self):
        assert _select_templates_balanced([], 10) == []

    def test_count_equals_templates(self):
        templates = make_templates(10)
        result = _select_templates_balanced(templates, 10)
        assert len(result) == 10
        assert Counter(t["id"] for t in result) == Counter(t["id"] for t in templates)

    def test_result_is_shuffled(self):
        """Results should not be in a fixed order (very likely to differ across runs)."""
        templates = make_templates(4)
        orders = set()
        for _ in range(30):
            selected = _select_templates_balanced(templates, 4)
            orders.add(tuple(t["id"] for t in selected))
        # With 4! = 24 permutations, 30 runs should produce >1 unique order
        assert len(orders) > 1


class TestSelectTemplatesBalancedMixed:
    def test_correct_length(self):
        templates = (
            make_templates(3, "Number")
            + make_templates(2, "Algebra")
            + make_templates(1, "Space")
        )
        result = _select_templates_balanced_mixed(templates, 10)
        assert len(result) == 10

    def test_empty_available_returns_empty(self):
        assert _select_templates_balanced_mixed([], 10) == []

    def test_strand_proportionality(self):
        """Larger strands should dominate in Mixed sessions."""
        # Number has 6 templates; Algebra has 1 — Number should dominate
        templates = make_templates(6, "Number") + make_templates(1, "Algebra")
        strand_counts: Counter = Counter()
        runs = 500
        for _ in range(runs):
            selected = _select_templates_balanced_mixed(templates, 10)
            for t in selected:
                strand_counts[t["strand"]] += 1
        # Number should appear far more than Algebra (ratio ~6:1 in pool)
        number_frac = strand_counts["Number"] / (runs * 10)
        assert number_frac > 0.70, (
            f"Number fraction {number_frac:.2f} unexpectedly low; expected >0.70"
        )


# ── Layer 2: Companion config ─────────────────────────────────────────────────

from config.companions import (
    COMPANION_IDS,
    get_companion_ids,
    should_expand,
    max_companions,
    COMPANION_FRACTION,
    COMPANION_TRIGGER_DIVISOR,
)


class TestShouldExpand:
    def test_triggers_below_threshold(self):
        # count=10, threshold=5: triggers when native < 5
        assert should_expand(4, 10) is True
        assert should_expand(3, 10) is True
        assert should_expand(1, 10) is True

    def test_does_not_trigger_at_or_above_threshold(self):
        assert should_expand(5, 10) is False
        assert should_expand(6, 10) is False
        assert should_expand(10, 10) is False

    def test_count_5(self):
        # count=5, threshold=2: triggers when native < 2
        assert should_expand(1, 5) is True
        assert should_expand(2, 5) is False
        assert should_expand(3, 5) is False


class TestMaxCompanions:
    def test_count_10(self):
        assert max_companions(10) == 4   # floor(0.4 * 10) = 4

    def test_count_5(self):
        assert max_companions(5) == 2    # floor(0.4 * 5) = 2

    def test_count_15(self):
        assert max_companions(15) == 6   # floor(0.4 * 15) = 6

    def test_minimum_is_one(self):
        # count=1 → floor(0.4*1)=0, but minimum is 1
        assert max_companions(1) >= 1


class TestGetCompanionIds:
    def test_y9_number_returns_y8_templates(self):
        cids = get_companion_ids(9, "Number")
        assert len(cids) > 0
        assert all(cid.startswith("T-8N-") for cid in cids)

    def test_unknown_combo_returns_empty(self):
        assert get_companion_ids(9, "Algebra") == []
        assert get_companion_ids(6, "Number") == []

    def test_all_strands_in_y9(self):
        # Y9 Number, Probability, Space, Statistics all have companions defined
        for strand in ("Number", "Probability", "Space", "Statistics"):
            assert len(get_companion_ids(9, strand)) > 0, (
                f"Y9 {strand} should have companion templates"
            )


class TestCompanionIdsExistInTemplates:
    """All companion IDs must resolve in docs/question_templates.json."""

    def test_all_companion_ids_are_valid(self):
        from docs_loader import load_template_meta
        missing = []
        for (year, strand), cids in COMPANION_IDS.items():
            for cid in cids:
                try:
                    meta = load_template_meta(cid)
                    assert meta["id"] == cid
                except ValueError:
                    missing.append(f"{cid} (for Y{year} {strand})")
        assert not missing, (
            f"Companion IDs not found in question_templates.json:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


# ── Layer 3: Param diversity ──────────────────────────────────────────────────

class TestParamFingerprint:
    def test_identical_dicts_produce_same_fingerprint(self):
        a = {"n": 64, "mode": "square"}
        b = {"n": 64, "mode": "square"}
        assert _param_fingerprint(a) == _param_fingerprint(b)

    def test_different_dicts_produce_different_fingerprint(self):
        a = {"n": 64}
        b = {"n": 81}
        assert _param_fingerprint(a) != _param_fingerprint(b)

    def test_non_scalar_values_ignored(self):
        a = {"n": 5, "nested": {"x": 1}}
        b = {"n": 5, "nested": {"x": 99}}
        # Nested dicts are not scalar — both should produce the same fingerprint
        assert _param_fingerprint(a) == _param_fingerprint(b)

    def test_empty_dict(self):
        assert _param_fingerprint({}) == frozenset()


class TestEnsureParamDiversity:
    """Use a template that has a realistic params schema for _fallback_params."""

    def _get_template(self, template_id: str) -> dict:
        from docs_loader import load_template_meta
        return load_template_meta(template_id)

    def test_identical_params_are_deduplicated(self):
        """3 identical param sets should yield 3 distinct sets after the gate."""
        tmpl = self._get_template("T-9N-02")  # scientific notation, choice params
        dupe_params = [{"mantissa": 5, "exponent": 3}] * 3
        result = _ensure_param_diversity(dupe_params, tmpl, "standard", target=3)
        assert len(result) == 3
        fingerprints = [_param_fingerprint(p) for p in result]
        assert len(set(fingerprints)) == 3, (
            f"Expected 3 distinct fingerprints, got: {fingerprints}"
        )

    def test_already_diverse_params_are_unchanged(self):
        """If params are already unique, no replacement should happen."""
        tmpl = self._get_template("T-9N-02")
        unique_params = [
            {"mantissa": 2, "exponent": 3},
            {"mantissa": 5, "exponent": -2},
            {"mantissa": 8, "exponent": 4},
        ]
        result = _ensure_param_diversity(unique_params, tmpl, "standard", target=3)
        assert len(result) == 3
        # All original params should still be present
        fingerprints_in = {_param_fingerprint(p) for p in unique_params}
        fingerprints_out = {_param_fingerprint(p) for p in result}
        assert fingerprints_in == fingerprints_out

    def test_output_length_equals_target(self):
        tmpl = self._get_template("T-9N-03")  # interest
        params = [{"principal": 1000, "rate": 5, "years": 2}] * 5
        result = _ensure_param_diversity(params, tmpl, "standard", target=5)
        assert len(result) == 5

    def test_partial_duplicates_filled(self):
        """2 of 4 params duplicated → 2 slots should be replaced with fallbacks."""
        tmpl = self._get_template("T-9N-02")
        params = [
            {"mantissa": 3, "exponent": 2},   # unique
            {"mantissa": 7, "exponent": -1},  # unique
            {"mantissa": 3, "exponent": 2},   # duplicate of [0]
            {"mantissa": 7, "exponent": -1},  # duplicate of [1]
        ]
        result = _ensure_param_diversity(params, tmpl, "standard", target=4)
        assert len(result) == 4
        fingerprints = [_param_fingerprint(p) for p in result]
        # Should have at least 3 distinct (may not always hit 4 due to limited choices)
        assert len(set(fingerprints)) >= 3
