"""
analytics.py
============
Structured usage analytics via JSON logging to stdout.

Render captures all stdout and displays it in the Logs tab — no external
dependencies, no database, no paid service required.

Each event is a single JSON line with a fixed schema:
  {"ts": "...", "event": "...", ...properties}

In-memory counters reset on redeploy; they are useful for real-time
monitoring via GET /api/stats while the service is running.
"""
from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger("analytics")

# ── In-memory counters (reset on redeploy) ───────────────────────────────────

_lock = threading.Lock()

_counters: dict[str, int] = defaultdict(int)
_strand_counts: dict[str, int] = defaultdict(int)
_year_counts: dict[str, int] = defaultdict(int)
_difficulty_counts: dict[str, int] = defaultdict(int)
_score_buckets: dict[str, int] = defaultdict(int)   # "0-25", "26-50", "51-75", "76-100"


def _score_bucket(score_pct: int) -> str:
    if score_pct <= 25:
        return "0-25"
    elif score_pct <= 50:
        return "26-50"
    elif score_pct <= 75:
        return "51-75"
    else:
        return "76-100"


# ── Core emit function ────────────────────────────────────────────────────────

def log_event(event: str, **properties) -> None:
    """
    Emit one JSON line to the analytics logger.

    All keyword arguments become top-level fields alongside `ts` and `event`.
    Non-serialisable values are converted to strings.
    """
    payload: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **properties,
    }
    # Fallback: stringify any non-serialisable value rather than crashing
    try:
        line = json.dumps(payload, default=str)
    except Exception:
        line = json.dumps({"ts": payload["ts"], "event": event, "error": "serialisation_failed"})
    logger.info(line)


# ── Named event helpers ───────────────────────────────────────────────────────

def track_session_started(
    *,
    session_id: str,
    year_level: int,
    strand: str,
    difficulty: str,
    count: int,
    student_id: str | None = None,
) -> None:
    log_event(
        "session_started",
        session_id=session_id,
        year_level=year_level,
        strand=strand,
        difficulty=difficulty,
        count=count,
        student_id=student_id or "anonymous",
    )
    with _lock:
        _counters["sessions_started"] += 1
        _strand_counts[strand] += 1
        _year_counts[str(year_level)] += 1
        _difficulty_counts[difficulty] += 1


def track_session_submitted(
    *,
    session_id: str,
    year_level: int,
    strand: str,
    difficulty: str,
    score: int,
    total: int,
    total_time_ms: int | None = None,
    student_id: str | None = None,
) -> None:
    score_pct = round(score / total * 100) if total > 0 else 0
    log_event(
        "session_submitted",
        session_id=session_id,
        year_level=year_level,
        strand=strand,
        difficulty=difficulty,
        score=score,
        total=total,
        score_pct=score_pct,
        total_time_ms=total_time_ms,
        student_id=student_id or "anonymous",
    )
    with _lock:
        _counters["sessions_submitted"] += 1
        _score_buckets[_score_bucket(score_pct)] += 1


def track_limit_reached(
    *,
    student_id: str | None = None,
    limit_type: str = "daily_session",
    tier: str = "free",
) -> None:
    log_event(
        "limit_reached",
        student_id=student_id or "anonymous",
        limit_type=limit_type,
        tier=tier,
    )
    with _lock:
        _counters["limits_reached"] += 1


def track_progress_analyse_requested(
    *,
    student_id: str | None = None,
    session_count: int = 0,
) -> None:
    log_event(
        "progress_analyse_requested",
        student_id=student_id or "anonymous",
        session_count=session_count,
    )
    with _lock:
        _counters["progress_analyses"] += 1


# ── Stats snapshot (for GET /api/stats) ──────────────────────────────────────

def get_stats() -> dict:
    """Return a snapshot of all in-memory counters (safe to expose publicly)."""
    with _lock:
        return {
            "sessions_started": _counters["sessions_started"],
            "sessions_submitted": _counters["sessions_submitted"],
            "limits_reached": _counters["limits_reached"],
            "progress_analyses": _counters["progress_analyses"],
            "by_strand": dict(_strand_counts),
            "by_year": dict(_year_counts),
            "by_difficulty": dict(_difficulty_counts),
            "score_distribution": dict(_score_buckets),
            "note": "Counters reset on each redeploy. For historical data, filter Render logs by event field.",
        }
