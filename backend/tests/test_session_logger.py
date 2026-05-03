"""Unit tests for session_logger.py — file-based session logging and stats reading."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from services.session_logger import LOG_FILE, log_session_start, read_stats

# Save the real LOG_FILE path so we can restore it
_ORIGINAL_LOG_FILE = LOG_FILE


@pytest.fixture
def temp_log_file(monkeypatch):
    """Replace LOG_FILE with a temp file for isolated testing."""
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="test_session_log_")
    os.close(fd)
    monkeypatch.setattr("services.session_logger.LOG_FILE", type(LOG_FILE)(path))
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


# ── log_session_start ─────────────────────────────────────────────────────────


def test_log_session_start_writes_line(temp_log_file):
    """log_session_start must append a valid pipe-delimited line to the log."""
    mock_request = MagicMock()
    mock_request.client.host = "192.168.1.1"

    log_session_start(
        mock_request, year_level=8, strand="Algebra", difficulty="standard", count=10
    )

    with open(temp_log_file, "r") as f:
        lines = f.readlines()
    assert len(lines) == 1

    parts = lines[0].strip().split("|")
    assert len(parts) == 6
    # Format: ISO_TIMESTAMP|HASHED_IP|YEAR|STRAND|DIFFICULTY|COUNT
    assert parts[2] == "8"
    assert parts[3] == "algebra"  # lowercased
    assert parts[4] == "standard"
    assert parts[5] == "10"
    # hashed IP should be 8 hex chars
    assert len(parts[1]) == 8
    assert all(c in "0123456789abcdef" for c in parts[1])


def test_log_session_start_handles_missing_client(temp_log_file):
    """When request.client is None, must not crash."""
    mock_request = MagicMock()
    mock_request.client = None

    log_session_start(
        mock_request, year_level=7, strand="Number", difficulty="foundation", count=5
    )

    with open(temp_log_file, "r") as f:
        lines = f.readlines()
    assert len(lines) == 1
    parts = lines[0].strip().split("|")
    assert parts[3] == "number"


def test_log_session_start_silent_on_permission_error(temp_log_file, monkeypatch):
    """log_session_start must not raise when file write fails."""
    # Make the file read-only
    import stat

    os.chmod(temp_log_file, stat.S_IRUSR)

    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"

    # Should not raise
    log_session_start(
        mock_request, year_level=7, strand="Algebra", difficulty="standard", count=5
    )


# ── read_stats ────────────────────────────────────────────────────────────────


def test_read_stats_empty_file(temp_log_file):
    """read_stats returns all-zero dict when the log file is empty."""
    stats = read_stats()
    assert stats["total_sessions"] == 0
    assert stats["today_sessions"] == 0
    assert stats["sessions_by_year"] == {}
    assert stats["sessions_by_strand"] == {}
    assert stats["last_session_at"] is None


def test_read_stats_counts_multiple_lines(temp_log_file):
    """read_stats correctly aggregates counts across multiple log lines."""
    lines = [
        "2026-01-15T10:00:00|abcd1234|8|algebra|standard|10\n",
        "2026-01-15T11:00:00|efab5678|7|number|foundation|5\n",
        "2026-01-16T10:00:00|00ff9999|8|algebra|advanced|15\n",
    ]
    with open(temp_log_file, "w") as f:
        f.writelines(lines)

    stats = read_stats()
    assert stats["total_sessions"] == 3
    assert stats["sessions_by_year"] == {"8": 2, "7": 1}
    assert stats["sessions_by_strand"] == {"algebra": 2, "number": 1}
    assert stats["last_session_at"] == "2026-01-16T10:00:00"


def test_read_stats_skips_malformed_lines(temp_log_file):
    """read_stats skips lines that don't have exactly 6 pipe-delimited fields."""
    lines = [
        "2026-01-15T10:00:00|abcd1234|8|algebra|standard|10\n",  # valid
        "garbage line\n",  # skip
        "2026-01-15T11:00:00|efab5678|7\n",  # skip (4 fields)
        "\n",  # skip (blank)
        "2026-01-16T10:00:00|00ff9999|8|algebra|advanced|15\n",  # valid
    ]
    with open(temp_log_file, "w") as f:
        f.writelines(lines)

    stats = read_stats()
    assert stats["total_sessions"] == 2


def test_read_stats_counts_today_sessions(temp_log_file):
    """read_stats correctly counts today's sessions."""
    from datetime import datetime, timezone

    today_prefix = datetime.now(timezone.utc).date().isoformat()
    yesterday_prefix = "2020-01-01"  # definitely not today

    lines = [
        f"{today_prefix}T10:00:00|abcd1234|8|algebra|standard|10\n",
        f"{today_prefix}T11:00:00|efab5678|7|number|foundation|5\n",
        f"{yesterday_prefix}T10:00:00|00ff9999|9|space|advanced|15\n",
    ]
    with open(temp_log_file, "w") as f:
        f.writelines(lines)

    stats = read_stats()
    assert stats["total_sessions"] == 3
    assert stats["today_sessions"] == 2


def test_read_stats_file_does_not_exist(monkeypatch):
    """read_stats returns zeros when the log file doesn't exist yet."""
    monkeypatch.setattr(
        "services.session_logger.LOG_FILE",
        type(LOG_FILE)("/tmp/nonexistent_session_log.txt"),
    )
    stats = read_stats()
    assert stats["total_sessions"] == 0
    assert stats["today_sessions"] == 0
