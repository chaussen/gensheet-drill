"""
Pydantic models matching docs/schemas.json exactly.
"""
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timezone
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QuestionObject(BaseModel):
    """Full question object including correct_index. Stored server-side, never sent to frontend."""
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_id: str
    vc_code: str
    year_level: int
    strand: str
    difficulty: str
    question_text: str
    options: list[str]
    correct_index: int
    explanation: str
    params: dict
    generated_at: str = Field(default_factory=_now_iso)


class QuestionObjectPublic(BaseModel):
    """QuestionObject without correct_index — sent to frontend in SessionStartResponse."""
    question_id: str
    template_id: str
    vc_code: str
    year_level: int
    strand: str
    difficulty: str
    question_text: str
    options: list[str]
    explanation: str
    params: dict
    generated_at: str


class SessionConfig(BaseModel):
    year_level: int
    strand: str
    difficulty: str
    count: int


class SessionStartRequest(BaseModel):
    year_level: Literal[7, 8, 9]
    strand: Literal["Number", "Algebra", "Measurement", "Space", "Statistics", "Probability", "Mixed"] = "Mixed"
    difficulty: Literal["foundation", "standard", "advanced"]
    count: int = Field(default=10, ge=5, le=20)


class SessionStartResponse(BaseModel):
    session_id: str
    questions: list[QuestionObjectPublic]
    created_at: str
    config: SessionConfig


class ResponseItem(BaseModel):
    question_id: str
    selected_index: int = Field(ge=0, le=3)
    time_taken_ms: int | None = None


class SessionSubmitRequest(BaseModel):
    responses: list[ResponseItem]


class ResponseResultItem(BaseModel):
    question_id: str
    question_text: str
    options: list[str]
    selected_index: int
    correct_index: int
    correct: bool
    explanation: str
    vc_code: str


class StrongArea(BaseModel):
    vc_code: str
    description: str
    score_pct: int


class WeakArea(BaseModel):
    vc_code: str
    description: str
    score_pct: int
    error_pattern: str
    tip: str


class NextSessionRecommendation(BaseModel):
    focus_vc_codes: list[str]
    difficulty: str
    rationale: str


class AnalysisObject(BaseModel):
    overall_score_pct: int
    performance_band: str
    strong_areas: list[StrongArea] = []
    weak_areas: list[WeakArea] = []
    next_session_recommendation: NextSessionRecommendation
    motivational_note: str | None = None


class SessionResultResponse(BaseModel):
    session_id: str
    score: int
    total: int
    score_pct: int
    responses: list[ResponseResultItem]
    analysis: AnalysisObject | None = None
    completed_at: str


class HealthResponse(BaseModel):
    status: str
    ts: str
    cache_size: int
