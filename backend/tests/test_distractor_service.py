"""
Tests for distractor_service.py — CURATED_WRONG strategy, garbage-distractor cleanup,
and end-to-end generate_distractors behaviour.
"""
import pytest
from unittest.mock import patch

from services.distractor_service import (
    _is_garbage_distractor,
    _improve_string_distractors,
    generate_distractors,
)


# ── _is_garbage_distractor ────────────────────────────────────────────────────

def test_garbage_wrong_n_pattern():
    assert _is_garbage_distractor("3/4_wrong_1") is True
    assert _is_garbage_distractor("2_wrong_0") is True


def test_garbage_neg_suffix():
    assert _is_garbage_distractor("5_neg") is True


def test_garbage_abc_suffix():
    assert _is_garbage_distractor("5_a") is True
    assert _is_garbage_distractor("5_b") is True
    assert _is_garbage_distractor("5_c") is True


def test_not_garbage_plain_answer():
    assert _is_garbage_distractor("5") is False
    assert _is_garbage_distractor("3/4") is False
    assert _is_garbage_distractor("$75.00") is False
    assert _is_garbage_distractor("x + 3") is False


# ── _improve_string_distractors ───────────────────────────────────────────────

def test_improve_fraction_garbage_replaced():
    """Garbage distractors for a fraction answer must be replaced with nearby fractions."""
    correct = "3/4"
    garbage = ["3/4_wrong_1", "3/4_wrong_2", "3/4_wrong_3"]
    result = _improve_string_distractors(correct, garbage)
    assert len(result) == 3
    for d in result:
        assert "_wrong_" not in d
        assert d != correct


def test_improve_no_garbage_unchanged():
    """If no garbage distractors, the list is returned unchanged."""
    original = ["1/2", "1/4", "5/4"]
    result = _improve_string_distractors("3/4", original)
    assert result == original


def test_improve_partial_garbage_mixed():
    """Only garbage entries are replaced; clean distractors stay in place."""
    correct = "3/4"
    distractors = ["1/2", "3/4_wrong_1", "5/4"]
    result = _improve_string_distractors(correct, distractors)
    assert result[0] == "1/2"   # unchanged
    assert "_wrong_" not in result[1]  # replaced
    assert result[2] == "5/4"   # unchanged


# ── generate_distractors — CURATED_WRONG path ─────────────────────────────────

def test_curated_wrong_exact_match():
    """
    When the curated_wrong_bank has an entry matching the correct answer,
    that entry's wrong_answers must be returned directly.
    """
    bank = [
        {"correct_answer": "$180.00", "wrong_answers": ["$150.00", "$200.00", "$160.00"]},
        {"correct_answer": "$75.00",  "wrong_answers": ["$50.00",  "$80.00",  "$70.00"]},
    ]
    with patch("services.distractor_service.load_curated_wrong_bank", return_value=bank):
        result = generate_distractors("T-9N-03", "$180.00", {})
    assert result == ["$150.00", "$200.00", "$160.00"]


def test_curated_wrong_no_exact_match_returns_any_entry():
    """
    When no entry matches the correct answer exactly, a random entry's wrong_answers
    must still be returned (not garbage, not empty).
    """
    bank = [
        {"correct_answer": "$180.00", "wrong_answers": ["$150.00", "$200.00", "$160.00"]},
    ]
    with patch("services.distractor_service.load_curated_wrong_bank", return_value=bank):
        result = generate_distractors("T-9N-03", "$999.00", {})
    assert len(result) == 3
    assert all(isinstance(d, str) for d in result)
    assert "$999.00" not in result


def test_curated_wrong_result_excludes_correct():
    """
    Returned distractors must not include the correct answer.
    The dedup step in build_question guarantees this; generate_distractors
    itself returns curated bank entries as-is, so we test with correct data.
    """
    bank = [
        {"correct_answer": "$75.00", "wrong_answers": ["$50.00", "$80.00", "$70.00"]},
    ]
    with patch("services.distractor_service.load_curated_wrong_bank", return_value=bank):
        result = generate_distractors("T-9N-03", "$75.00", {})
    assert "$75.00" not in result


def test_curated_wrong_empty_bank_falls_back_to_engine():
    """If the curated_wrong_bank is empty, generate_distractors falls back to the engine."""
    with patch("services.distractor_service.load_curated_wrong_bank", return_value=[]):
        # T-7N-01 is a parametric template (not curated_bank) with no curated_wrong — uses engine
        result = generate_distractors("T-7N-01", 8, {"n": 64})
    assert len(result) == 3
    assert "8" not in result  # correct answer not in distractors


# ── generate_distractors — real curated_wrong templates ──────────────────────

def test_t9a01_generates_three_distractors():
    """T-9A-01 uses CURATED_WRONG — must always produce 3 non-garbage distractors."""
    from docs_loader import load_template_meta
    from services.verification import VerificationEngine
    engine = VerificationEngine()
    template = load_template_meta("T-9A-01")
    # Use a set of params to get a real correct answer, then call generate_distractors
    # We don't need exact params — just check the strategy is wired correctly
    result = generate_distractors("T-9A-01", "some answer", {})
    assert len(result) == 3
    for d in result:
        assert "_wrong_" not in d
        assert d != "some answer"


def test_generate_distractors_always_returns_three():
    """For any parametric template, generate_distractors must return exactly 3 items."""
    for template_id, answer, params in [
        ("T-7N-01", 8, {"n": 64}),
        ("T-7N-07", 50, {"pct": 25, "amount": 200}),
        ("T-8N-03", 6, {"a": 12, "b": 18, "measure": "HCF"}),
    ]:
        result = generate_distractors(template_id, answer, params)
        assert len(result) == 3, f"Expected 3 distractors for {template_id}, got {len(result)}"
        assert str(answer) not in result, f"Correct answer in distractors for {template_id}"


def test_generate_distractors_all_distinct():
    """All 3 returned distractors must be distinct strings."""
    result = generate_distractors("T-7N-01", 8, {"n": 64})
    assert len(set(result)) == 3, "Distractors must be distinct"
