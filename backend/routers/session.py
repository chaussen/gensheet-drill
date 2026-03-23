"""
routers/session.py
==================
Session lifecycle endpoints:
  POST /api/session/start
  POST /api/session/{id}/submit
  GET  /api/session/{id}/result
"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from models.schemas import (
    SessionStartRequest,
    SessionStartResponse,
    SessionConfig,
    SessionSubmitRequest,
    SessionResultResponse,
    SessionSummaryObject,
    ResponseResultItem,
    QuestionObjectPublic,
    AnalysisObject,
)
from services.question_service import generate_session_questions
from services.session_service import generate_session_summary
from cache import session_cache
from config.tiers import get_tier_config

router = APIRouter(prefix="/api/session")
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_response_result_item(r: dict, q: dict) -> ResponseResultItem:
    q_type = q.get("question_type", "single_select")
    return ResponseResultItem(
        question_id=r["question_id"],
        question_text=q["question_text"],
        options=q["options"],
        question_type=q_type,
        selected_index=r.get("selected_index") if q_type == "single_select" else None,
        correct_index=q.get("correct_index") if q_type == "single_select" else None,
        selected_indices=r.get("selected_indices") if q_type == "multi_select" else None,
        correct_indices=q.get("correct_indices") if q_type == "multi_select" else None,
        correct=r["correct"],
        explanation=q["explanation"],
        vc_code=q["vc_code"],
        time_taken_ms=r.get("time_taken_ms"),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest):
    """
    Create a new drill session. Generates questions, stores full objects
    (with correct_index) in server memory, returns public view to frontend.
    """
    tier = get_tier_config()

    if req.count > tier["max_question_count"]:
        raise HTTPException(
            status_code=400,
            detail=f"Question count {req.count} exceeds maximum of {tier['max_question_count']} for {tier['tier']} tier.",
        )

    if req.student_id:
        today_count = session_cache.count_today(req.student_id)
        if today_count >= tier["daily_session_limit"]:
            raise HTTPException(
                status_code=429,
                detail="Daily session limit reached",
                headers={"Retry-After": "3600"},
            )

    try:
        questions = await generate_session_questions(
            year_level=req.year_level,
            strand=req.strand,
            difficulty=req.difficulty,
            count=req.count,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error generating questions: %s", e)
        raise HTTPException(status_code=503, detail="Could not generate questions. Please try again.")

    MIN_QUESTIONS = 5
    if len(questions) < MIN_QUESTIONS:
        raise HTTPException(
            status_code=503,
            detail="Could not generate enough questions. Please try again.",
        )

    session_id = str(uuid.uuid4())
    created_at = _now()

    # Store full question objects (including correct_index) server-side
    session_data = {
        "session_id": session_id,
        "student_id": req.student_id,
        "year_level": req.year_level,
        "strand": req.strand,
        "difficulty": req.difficulty,
        "count": len(questions),
        "config": {
            "year_level": req.year_level,
            "strand": req.strand,
            "difficulty": req.difficulty,
        },
        "questions": {q.question_id: q.model_dump() for q in questions},
        "question_order": [q.question_id for q in questions],
        "responses": [],
        "status": "active",
        "created_at": created_at,
        "score": None,
        "completed_at": None,
        "summary": None,
        "analysis": None,
    }
    session_cache.put(session_id, session_data)

    # Send questions WITHOUT correct_index to frontend
    public_questions = [
        QuestionObjectPublic(
            question_id=q.question_id,
            template_id=q.template_id,
            vc_code=q.vc_code,
            year_level=q.year_level,
            strand=q.strand,
            difficulty=q.difficulty,
            question_type=q.question_type,
            question_text=q.question_text,
            options=q.options,
            explanation=q.explanation,
            params=q.params,
            generated_at=q.generated_at,
        )
        for q in questions
    ]

    return SessionStartResponse(
        session_id=session_id,
        questions=public_questions,
        created_at=created_at,
        config=SessionConfig(
            year_level=req.year_level,
            strand=req.strand,
            difficulty=req.difficulty,
            count=len(questions),
        ),
    )


@router.post("/{session_id}/submit", response_model=SessionResultResponse)
async def submit_session(
    session_id: str,
    req: SessionSubmitRequest,
):
    """
    Auto-mark the session (pure Python — no AI) and compute an instant
    code-based summary. Returns score and summary immediately.
    """
    session = session_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session already submitted")

    marked = []
    score = 0

    for resp in req.responses:
        q = session["questions"].get(resp.question_id)
        if not q:
            logger.warning("Unknown question_id %s in submit for session %s",
                           resp.question_id, session_id)
            continue
        if q.get("question_type") == "multi_select":
            correct = set(resp.selected_indices or []) == set(q.get("correct_indices") or [])
        else:
            correct = resp.selected_index == q["correct_index"]
        if correct:
            score += 1
        marked.append({
            "question_id": resp.question_id,
            "selected_index": resp.selected_index,
            "selected_indices": resp.selected_indices,
            "time_taken_ms": resp.time_taken_ms,
            "correct": correct,
        })

    total = len(marked)
    completed_at = _now()

    session["responses"] = marked
    session["score"] = score
    session["submitted_count"] = total
    session["status"] = "submitted"
    session["completed_at"] = completed_at
    session["total_time_ms"] = req.total_time_ms
    summary = generate_session_summary(session, session["questions"], req.total_time_ms)
    session["summary"] = summary.model_dump()
    session_cache.update(session_id, session)

    response_items = [
        _make_response_result_item(r, session["questions"][r["question_id"]])
        for r in marked
    ]

    return SessionResultResponse(
        session_id=session_id,
        score=score,
        total=session["count"],   # original question count, not submitted count
        score_pct=round(score / session["count"] * 100) if session["count"] > 0 else 0,
        responses=response_items,
        summary=summary,
        analysis=None,
        completed_at=completed_at,
    )


@router.get("/{session_id}/result", response_model=SessionResultResponse)
async def get_result(session_id: str):
    """
    Retrieve the completed session result including the code-based summary.
    """
    session = session_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "active":
        raise HTTPException(status_code=400, detail="Session not yet submitted")

    summary_obj = None
    if session.get("summary"):
        try:
            summary_obj = SessionSummaryObject(**session["summary"])
        except Exception as e:
            logger.warning("Failed to parse summary for session %s: %s", session_id, e)

    analysis_obj = None
    if session.get("analysis"):
        try:
            analysis_obj = AnalysisObject(**session["analysis"])
        except Exception as e:
            logger.warning("Failed to parse analysis for session %s: %s", session_id, e)

    response_items = [
        _make_response_result_item(r, session["questions"][r["question_id"]])
        for r in session["responses"]
    ]

    total = session["count"]   # original question count
    score = session["score"] or 0

    return SessionResultResponse(
        session_id=session_id,
        score=score,
        total=total,
        score_pct=round(score / total * 100) if total > 0 else 0,
        responses=response_items,
        summary=summary_obj,
        analysis=analysis_obj,
        completed_at=session.get("completed_at", ""),
    )
