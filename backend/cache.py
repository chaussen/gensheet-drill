"""
cache.py
========
In-memory stores for sessions and pre-generated questions.
No database. Phase 1 only.
"""
import time
import os
from datetime import datetime, timezone

CACHE_TTL = int(os.getenv("QUESTION_CACHE_TTL_SECONDS", "3600"))


class SessionCache:
    """Stores active and completed sessions keyed by session_id."""

    def __init__(self):
        self._store: dict = {}

    def put(self, session_id: str, data: dict) -> None:
        self._store[session_id] = {"data": data, "ts": time.time()}

    def get(self, session_id: str) -> dict | None:
        entry = self._store.get(session_id)
        return entry["data"] if entry else None

    def update(self, session_id: str, data: dict) -> None:
        if session_id in self._store:
            self._store[session_id]["data"] = data

    def count_today(self, student_id: str) -> int:
        """Count sessions created today (UTC) for a given student_id."""
        if not student_id:
            return 0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = 0
        for entry in self._store.values():
            data = entry["data"]
            sid = data.get("student_id")
            if not sid or sid != student_id:
                continue
            created = data.get("created_at", "")
            if len(created) >= 10 and created[:10] == today:
                count += 1
        return count

    def size(self) -> int:
        return len(self._store)


class QuestionCache:
    """
    Stores pre-generated question lists keyed by (year, strand, difficulty).
    Used by Iteration 4 warm-up; sessions can also draw from this pool.
    """

    def __init__(self):
        self._store: dict = {}
        self._ts: dict = {}

    def put(self, year: int, strand: str, difficulty: str, questions: list) -> None:
        key = (year, strand, difficulty)
        self._store[key] = questions
        self._ts[key] = time.time()

    def get(self, year: int, strand: str, difficulty: str) -> list | None:
        key = (year, strand, difficulty)
        ts = self._ts.get(key)
        if ts and (time.time() - ts) < CACHE_TTL:
            return self._store.get(key)
        return None

    def size(self) -> int:
        return sum(len(v) for v in self._store.values())


# Module-level singletons
session_cache = SessionCache()
question_cache = QuestionCache()
