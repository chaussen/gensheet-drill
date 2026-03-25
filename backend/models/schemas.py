"""
Pydantic models matching docs/schemas.json exactly.
"""
from pydantic import BaseModel, Field, model_validator
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
    question_type: Literal["single_select", "multi_select"] = "single_select"
    question_text: str
    options: list[str]
    correct_index: int
    correct_indices: list[int] | None = None  # multi_select only; correct_index is -1 sentinel
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
    question_type: Literal["single_select", "multi_select"] = "single_select"
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
    student_id: str | None = None


class SessionStartResponse(BaseModel):
    session_id: str
    questions: list[QuestionObjectPublic]
    created_at: str
    config: SessionConfig


class ResponseItem(BaseModel):
    question_id: str
    selected_index: int | None = Field(default=None, ge=0, le=4)
    selected_indices: list[int] | None = None
    time_taken_ms: int | None = None

    @model_validator(mode="after")
    def check_exactly_one_selection(self) -> "ResponseItem":
        has_single = self.selected_index is not None
        has_multi = self.selected_indices is not None
        if has_single == has_multi:
            raise ValueError(
                "Exactly one of selected_index or selected_indices must be provided"
            )
        return self


class SessionSubmitRequest(BaseModel):
    responses: list[ResponseItem]
    total_time_ms: int = 0


class ResponseResultItem(BaseModel):
    question_id: str
    question_text: str
    options: list[str]
    question_type: Literal["single_select", "multi_select"] = "single_select"
    selected_index: int | None = None
    correct_index: int | None = None
    selected_indices: list[int] | None = None
    correct_indices: list[int] | None = None
    correct: bool
    explanation: str
    vc_code: str
    time_taken_ms: int | None = None


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


class StrandStat(BaseModel):
    attempted: int
    correct: int
    score_pct: int


class NextSessionSuggestion(BaseModel):
    strand: str
    difficulty: str
    reason: str


class SessionSummaryObject(BaseModel):
    score: int
    total: int
    score_pct: int
    performance_band: str  # needs_support / developing / strong / exceeding
    by_strand: dict[str, StrandStat]
    weakest_strand: str | None
    strongest_strand: str | None
    next_session_suggestion: NextSessionSuggestion
    total_time_ms: int = 0
    avg_time_per_question_ms: int = 0
    time_band: str = ""              # "fast" | "moderate" | "slow"
    time_accuracy_summary: str = ""  # plain English one-liner


class SessionResultResponse(BaseModel):
    session_id: str
    score: int
    total: int
    score_pct: int
    responses: list[ResponseResultItem]
    summary: SessionSummaryObject | None = None
    analysis: AnalysisObject | None = None
    completed_at: str


class TierConfigResponse(BaseModel):
    tier: str
    daily_session_limit: int
    max_question_count: int
    question_count_options: list[int]


class HealthResponse(BaseModel):
    status: str
    ts: str
    cache_size: int
