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

from fastapi import APIRouter, HTTPException, BackgroundTasks

from models.schemas import (
    SessionStartRequest,
    SessionStartResponse,
    SessionConfig,
    SessionSubmitRequest,
    SessionResultResponse,
    ResponseResultItem,
    QuestionObjectPublic,
    AnalysisObject,
)
from services.question_service import generate_session_questions
from services import ai_service
from cache import session_cache

router = APIRouter(prefix="/api/session")
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_results_table(session: dict) -> str:
    """
    Construct the results table string for the AI analysis prompt.
    Format: Q# | VC Code | Topic | Student answer | Correct answer | Result
    (per docs/ai_prompts.md)
    """
    from docs_loader import load_template_meta
    rows = []
    for i, resp in enumerate(session["responses"], 1):
        q = session["questions"].get(resp["question_id"])
        if not q:
            continue
        try:
            meta = load_template_meta(q["template_id"])
            topic = meta.get("topic", q["template_id"])
        except Exception:
            topic = q["template_id"]

        student_answer = q["options"][resp["selected_index"]]
        correct_answer = q["options"][q["correct_index"]]
        result = "✓" if resp["correct"] else "✗"
        rows.append(
            f"Q{i} | {q['vc_code']} | {topic} | "
            f"{student_answer} | {correct_answer} | {result}"
        )
    return "\n".join(rows)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", response_model=SessionStartResponse)
async def start_session(req: SessionStartRequest):
    """
    Create a new drill session. Generates questions, stores full objects
    (with correct_index) in server memory, returns public view to frontend.
    """
    try:
        questions = await generate_session_questions(
            year_level=req.year_level,
            strand=req.strand,
            difficulty=req.difficulty,
            count=req.count,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not questions:
        raise HTTPException(
            status_code=503,
            detail="Could not generate questions. The AI service may be unavailable.",
        )

    session_id = str(uuid.uuid4())
    created_at = _now()

    # Store full question objects (including correct_index) server-side
    session_data = {
        "session_id": session_id,
        "year_level": req.year_level,
        "strand": req.strand,
        "difficulty": req.difficulty,
        "count": len(questions),
        "questions": {q.question_id: q.model_dump() for q in questions},
        "question_order": [q.question_id for q in questions],
        "responses": [],
        "status": "active",
        "created_at": created_at,
        "score": None,
        "completed_at": None,
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


async def _run_analysis(session_id: str) -> None:
    """Background task: call AI analysis and store result in session cache."""
    session = session_cache.get(session_id)
    if not session:
        return

    results_table = _build_results_table(session)
    analysis_data = await ai_service.analyse_session(
        {
            "year_level": session["year_level"],
            "difficulty": session["difficulty"],
            "score": session["score"],
            "total": session["count"],
            "results_table": results_table,
        }
    )
    session["analysis"] = analysis_data
    session_cache.update(session_id, session)


@router.post("/{session_id}/submit", response_model=SessionResultResponse)
async def submit_session(
    session_id: str,
    req: SessionSubmitRequest,
    background_tasks: BackgroundTasks,
):
    """
    Auto-mark the session (pure Python — no AI), then trigger background
    AI analysis. Returns score immediately; analysis: null until ready.
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
        correct = resp.selected_index == q["correct_index"]
        if correct:
            score += 1
        marked.append({
            "question_id": resp.question_id,
            "selected_index": resp.selected_index,
            "time_taken_ms": resp.time_taken_ms,
            "correct": correct,
        })

    total = len(marked)
    score_pct = round(score / total * 100) if total > 0 else 0
    completed_at = _now()

    session["responses"] = marked
    session["score"] = score
    session["submitted_count"] = total   # responses actually submitted
    # session["count"] is preserved as the original question count
    session["status"] = "submitted"
    session["completed_at"] = completed_at
    session_cache.update(session_id, session)

    background_tasks.add_task(_run_analysis, session_id)

    response_items = [
        ResponseResultItem(
            question_id=r["question_id"],
            question_text=session["questions"][r["question_id"]]["question_text"],
            options=session["questions"][r["question_id"]]["options"],
            selected_index=r["selected_index"],
            correct_index=session["questions"][r["question_id"]]["correct_index"],
            correct=r["correct"],
            explanation=session["questions"][r["question_id"]]["explanation"],
            vc_code=session["questions"][r["question_id"]]["vc_code"],
        )
        for r in marked
    ]

    return SessionResultResponse(
        session_id=session_id,
        score=score,
        total=session["count"],   # original question count, not submitted count
        score_pct=round(score / session["count"] * 100) if session["count"] > 0 else 0,
        responses=response_items,
        analysis=None,  # AI running in background
        completed_at=completed_at,
    )


@router.get("/{session_id}/result", response_model=SessionResultResponse)
async def get_result(session_id: str):
    """
    Poll this endpoint to retrieve score + AI analysis once it's ready.
    analysis will be null while the background task is still running.
    """
    session = session_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] == "active":
        raise HTTPException(status_code=400, detail="Session not yet submitted")

    analysis_obj = None
    if session.get("analysis"):
        try:
            analysis_obj = AnalysisObject(**session["analysis"])
        except Exception as e:
            logger.warning("Failed to parse analysis for session %s: %s", session_id, e)

    response_items = [
        ResponseResultItem(
            question_id=r["question_id"],
            question_text=session["questions"][r["question_id"]]["question_text"],
            options=session["questions"][r["question_id"]]["options"],
            selected_index=r["selected_index"],
            correct_index=session["questions"][r["question_id"]]["correct_index"],
            correct=r["correct"],
            explanation=session["questions"][r["question_id"]]["explanation"],
            vc_code=session["questions"][r["question_id"]]["vc_code"],
        )
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
        analysis=analysis_obj,
        completed_at=session.get("completed_at", ""),
    )
