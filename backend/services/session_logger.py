"""
services/session_logger.py
==========================
File-based session logging and stats reader.
Uses only Python stdlib — no external dependencies.
"""
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request

logger = logging.getLogger(__name__)

# Resolved at import time: backend/logs/session_log.txt
LOG_FILE = Path(__file__).parent.parent / "logs" / "session_log.txt"


def log_session_start(
    request: Request,
    year_level: int,
    strand: str,
    difficulty: str,
    count: int,
) -> None:
    """
    Append one pipe-delimited line to the session log.
    Silently no-ops on any error so failures never affect the session response.

    Format: ISO_TIMESTAMP|HASHED_IP|YEAR|STRAND|DIFFICULTY|COUNT
    Example: 2026-04-13T02:15:33|a3f9c12b|7|algebra|standard|10
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        hashed_ip = hashlib.md5(client_ip.encode()).hexdigest()[:8]
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        line = f"{ts}|{hashed_ip}|{year_level}|{strand.lower()}|{difficulty}|{count}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception as exc:
        logger.debug("Session log write failed (non-fatal): %s", exc)


def read_stats() -> dict:
    """
    Read logs/session_log.txt and return aggregated stats.
    Returns all-zero dict if the file does not exist yet.
    """
    if not LOG_FILE.exists():
        return {
            "total_sessions": 0,
            "today_sessions": 0,
            "sessions_by_year": {},
            "sessions_by_strand": {},
            "last_session_at": None,
        }

    today_prefix = datetime.now(timezone.utc).date().isoformat()  # "2026-04-13"
    total = 0
    today_count = 0
    by_year: dict[str, int] = {}
    by_strand: dict[str, int] = {}
    last_ts: str | None = None

    try:
        with open(LOG_FILE, "r") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) != 6:
                    continue
                ts, _hashed_ip, year, strand, _difficulty, _count = parts
                total += 1
                if ts.startswith(today_prefix):
                    today_count += 1
                by_year[year] = by_year.get(year, 0) + 1
                by_strand[strand] = by_strand.get(strand, 0) + 1
                last_ts = ts
    except Exception as exc:
        logger.warning("Failed to read session log: %s", exc)

    return {
        "total_sessions": total,
        "today_sessions": today_count,
        "sessions_by_year": by_year,
        "sessions_by_strand": by_strand,
        "last_session_at": last_ts,
    }
