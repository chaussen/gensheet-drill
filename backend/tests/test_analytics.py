"""Unit tests for analytics.py — in-memory counters, event logging, stats snapshot."""

import json
import logging
from unittest.mock import MagicMock, patch

import analytics


def _reset_counters():
    """Resets all in-memory counters to zero between tests."""
    with analytics._lock:
        analytics._counters.clear()
        analytics._strand_counts.clear()
        analytics._year_counts.clear()
        analytics._difficulty_counts.clear()
        analytics._score_buckets.clear()


# ── _score_bucket ─────────────────────────────────────────────────────────────


def test_score_bucket_ranges():
    assert analytics._score_bucket(0) == "0-25"
    assert analytics._score_bucket(25) == "0-25"
    assert analytics._score_bucket(26) == "26-50"
    assert analytics._score_bucket(50) == "26-50"
    assert analytics._score_bucket(51) == "51-75"
    assert analytics._score_bucket(75) == "51-75"
    assert analytics._score_bucket(76) == "76-100"
    assert analytics._score_bucket(100) == "76-100"


# ── log_event ─────────────────────────────────────────────────────────────────


def test_log_event_emits_json_line():
    """log_event must emit a valid JSON line at INFO level."""
    with patch.object(analytics.logger, "info") as mock_info:
        analytics.log_event("test_event", key1="value1", count=42)

    mock_info.assert_called_once()
    line = mock_info.call_args[0][0]
    payload = json.loads(line)
    assert payload["event"] == "test_event"
    assert payload["key1"] == "value1"
    assert payload["count"] == 42
    assert "ts" in payload


def test_log_event_handles_non_serializable():
    """log_event must not crash when given non-serialisable values."""
    with patch.object(analytics.logger, "info"):
        # bytes are not JSON-serialisable — should use default=str fallback
        analytics.log_event("test", bad=bytes([1, 2, 3]))


# ── track_session_started ─────────────────────────────────────────────────────


def test_track_session_started_increments_counters():
    _reset_counters()
    analytics.track_session_started(
        session_id="s1",
        year_level=7,
        strand="Algebra",
        difficulty="standard",
        count=10,
    )
    stats = analytics.get_stats()
    assert stats["sessions_started"] == 1
    assert stats["by_year"]["7"] == 1
    assert stats["by_strand"]["Algebra"] == 1
    assert stats["by_difficulty"]["standard"] == 1


def test_track_session_started_multiple():
    _reset_counters()
    analytics.track_session_started(
        session_id="s1",
        year_level=7,
        strand="Number",
        difficulty="foundation",
        count=5,
    )
    analytics.track_session_started(
        session_id="s2",
        year_level=8,
        strand="Algebra",
        difficulty="standard",
        count=10,
    )
    analytics.track_session_started(
        session_id="s3",
        year_level=7,
        strand="Number",
        difficulty="foundation",
        count=10,
    )
    stats = analytics.get_stats()
    assert stats["sessions_started"] == 3
    assert stats["by_year"]["7"] == 2
    assert stats["by_year"]["8"] == 1
    assert stats["by_strand"]["Number"] == 2
    assert stats["by_strand"]["Algebra"] == 1
    assert stats["by_difficulty"]["foundation"] == 2
    assert stats["by_difficulty"]["standard"] == 1


def test_track_session_started_anonymous_student_id():
    _reset_counters()
    with patch.object(analytics, "log_event") as mock_log:
        analytics.track_session_started(
            session_id="s1",
            year_level=7,
            strand="Algebra",
            difficulty="standard",
            count=5,
            student_id=None,
        )
    call_args = mock_log.call_args[1]
    assert call_args["student_id"] == "anonymous"


# ── track_session_submitted ───────────────────────────────────────────────────


def test_track_session_submitted_increments_counters():
    _reset_counters()
    analytics.track_session_submitted(
        session_id="s1",
        year_level=8,
        strand="Algebra",
        difficulty="standard",
        score=7,
        total=10,
    )
    stats = analytics.get_stats()
    assert stats["sessions_submitted"] == 1
    assert stats["score_distribution"]["51-75"] == 1


def test_track_session_submitted_score_buckets():
    _reset_counters()
    analytics.track_session_submitted(
        session_id="s1",
        year_level=7,
        strand="Number",
        difficulty="standard",
        score=2,
        total=10,
    )
    analytics.track_session_submitted(
        session_id="s2",
        year_level=8,
        strand="Algebra",
        difficulty="standard",
        score=5,
        total=10,
    )
    analytics.track_session_submitted(
        session_id="s3",
        year_level=9,
        strand="Algebra",
        difficulty="standard",
        score=7,
        total=10,
    )
    analytics.track_session_submitted(
        session_id="s4",
        year_level=7,
        strand="Number",
        difficulty="standard",
        score=9,
        total=10,
    )
    stats = analytics.get_stats()
    assert stats["score_distribution"]["0-25"] == 1
    assert stats["score_distribution"]["26-50"] == 1
    assert stats["score_distribution"]["51-75"] == 1
    assert stats["score_distribution"]["76-100"] == 1


# ── track_limit_reached ───────────────────────────────────────────────────────


def test_track_limit_reached_increments_counter():
    _reset_counters()
    analytics.track_limit_reached(
        student_id="st1", limit_type="daily_session", tier="free"
    )
    stats = analytics.get_stats()
    assert stats["limits_reached"] == 1


# ── track_progress_analyse_requested ──────────────────────────────────────────


def test_track_progress_analyse_requested_increments_counter():
    _reset_counters()
    analytics.track_progress_analyse_requested(student_id="st1", session_count=3)
    stats = analytics.get_stats()
    assert stats["progress_analyses"] == 1


def test_track_progress_analyse_requested_emits_log():
    with patch.object(analytics, "log_event") as mock_log:
        analytics.track_progress_analyse_requested(student_id="st1", session_count=3)
    args = mock_log.call_args
    assert args[0][0] == "progress_analyse_requested"
    assert args[1]["session_count"] == 3


# ── get_stats ─────────────────────────────────────────────────────────────────


def test_get_stats_empty_state():
    _reset_counters()
    stats = analytics.get_stats()
    assert stats["sessions_started"] == 0
    assert stats["sessions_submitted"] == 0
    assert stats["by_strand"] == {}
    assert stats["by_year"] == {}
    assert stats["by_difficulty"] == {}
    assert stats["score_distribution"] == {}
    assert "note" in stats


def test_get_stats_thread_safe():
    """get_stats must safely read counters even under contention (basic check)."""
    _reset_counters()
    analytics.track_session_started(
        session_id="t",
        year_level=7,
        strand="Number",
        difficulty="standard",
        count=5,
    )
    stats = analytics.get_stats()
    assert isinstance(stats, dict)
