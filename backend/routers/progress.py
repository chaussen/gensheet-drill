"""
routers/progress.py
===================
On-demand multi-session AI analysis:
  POST /api/progress/analyse
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import AnalysisObject
from services import ai_service
from cache import session_cache
from docs_loader import load_template_meta
import analytics

router = APIRouter(prefix="/api/progress")
logger = logging.getLogger(__name__)


class ProgressAnalyseRequest(BaseModel):
    session_ids: list[str] = Field(min_length=2)
    student_id: str


def _build_session_row(session: dict, session_num: int) -> str:
    """Format one session's results as a labelled block for the AI prompt."""
    completed_at = session.get("completed_at", "")
    try:
        dt = datetime.fromisoformat(completed_at)
        date_str = dt.strftime("%Y-%m-%d")
    except Exception:
        date_str = completed_at[:10] if completed_at else "unknown"

    year_level = session.get("year_level", "?")
    strand     = session.get("strand", "?")
    difficulty = session.get("difficulty", "?")
    score      = session.get("score", 0)
    count      = session.get("count", len(session.get("responses", [])))

    header = (
        f"Session {session_num} ({date_str}, Year {year_level}, "
        f"{strand}, {difficulty}, {score}/{count}):"
    )

    rows = []
    for i, resp in enumerate(session.get("responses", []), 1):
        q = session["questions"].get(resp["question_id"])
        if not q:
            continue
        try:
            meta = load_template_meta(q["template_id"])
            topic = meta.get("topic", q["template_id"])
        except Exception:
            topic = q.get("template_id", "?")

        if q.get("question_type") == "multi_select":
            student_answer = ", ".join(
                q["options"][idx] for idx in (resp.get("selected_indices") or [])
            ) or "(none)"
            correct_answer = ", ".join(
                q["options"][idx] for idx in (q.get("correct_indices") or [])
            )
        else:
            si = resp.get("selected_index")
            student_answer = q["options"][si] if si is not None else "(none)"
            correct_answer = q["options"][q["correct_index"]]

        result = "✓" if resp.get("correct") else "✗"
        rows.append(
            f"Q{i} | {q['vc_code']} | {topic} | "
            f"{student_answer} | {correct_answer} | {result}"
        )

    return header + "\n" + "\n".join(rows)


@router.post("/analyse", response_model=AnalysisObject)
async def analyse_progress(body: ProgressAnalyseRequest):
    """
    Generate an AI progress report across the selected sessions.
    Requires at least 2 resolvable sessions from the server-side cache.
    """
    resolved = []
    missing_count = 0
    for sid in body.session_ids:
        session = session_cache.get(sid)
        if session and session.get("status") == "submitted":
            resolved.append(session)
        else:
            missing_count += 1

    if missing_count:
        logger.warning(
            "analyse_progress: %d session(s) not found in cache",
            missing_count,
        )

    if len(resolved) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"At least 2 completed sessions are required. "
                f"Only {len(resolved)} were found in the server cache. "
                f"Sessions may have expired — the server keeps sessions in memory only."
            ),
        )

    analytics.track_progress_analyse_requested(
        student_id=body.student_id,
        session_count=len(resolved),
    )

    # Build aggregated results table
    blocks = [_build_session_row(s, i + 1) for i, s in enumerate(resolved)]
    aggregated_table = "\n\n".join(blocks)

    # Use year_level and difficulty from the most recent resolved session
    latest = resolved[-1]
    sessions_data = {
        "aggregated_table": aggregated_table,
        "session_count": len(resolved),
        "year_level": latest.get("year_level"),
        "difficulty": latest.get("difficulty", "standard"),
    }

    result = await ai_service.analyse_progress(sessions_data)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Progress report unavailable — AI service did not respond. Please try again.",
        )

    try:
        return AnalysisObject(**result)
    except Exception as e:
        logger.error("analyse_progress: failed to parse AnalysisObject: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Progress report unavailable — response could not be parsed. Please try again.",
        )
