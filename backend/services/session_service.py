"""
Pure Python session summary computation — zero AI calls.
"""
from models.schemas import SessionSummaryObject, StrandStat, NextSessionSuggestion

STRAND_ORDER = ["Algebra", "Measurement", "Number", "Probability", "Space", "Statistics"]

TIME_ACCURACY_MESSAGES = {
    ("exceeding", "fast"):         "Excellent — high accuracy and fast responses.",
    ("exceeding", "moderate"):     "Great accuracy. You're taking your time — that's fine.",
    ("exceeding", "slow"):         "Great accuracy. Try to pick up the pace next session.",
    ("strong", "fast"):            "Good score and quick responses. Watch for careless errors.",
    ("strong", "moderate"):        "Solid session overall.",
    ("strong", "slow"):            "Good accuracy but slow pacing — try to move more confidently.",
    ("developing", "fast"):        "Fast but some errors — slow down slightly and check your work.",
    ("developing", "moderate"):    "Some questions are tricky — focus on your weak strand next.",
    ("developing", "slow"):        "Take your time — accuracy is more important than speed right now.",
    ("needs_support", "fast"):     "Moving quickly but missing too many — slow down and check each step.",
    ("needs_support", "moderate"): "This strand needs more practice. Try foundation difficulty.",
    ("needs_support", "slow"):     "Take your time — try foundation difficulty to build confidence.",
}

REASON_TEMPLATES = {
    "weak":          "You got {correct}/{attempted} on {strand}. Try foundation difficulty next.",
    "medium":        "You scored {pct}% on {strand}. Keep practising at this level.",
    "strong":        "Great work on {strand}! Try {next_difficulty} difficulty next.",
    "strong_at_top": "Great work on {strand}! Keep challenging yourself at advanced level.",
    "all_good":      "You're performing well across all strands. Try advanced next.",
    "all_good_at_top": "Excellent across all strands. Keep it up at advanced level.",
}

_DIFFICULTY_ORDER = ["foundation", "standard", "advanced"]


def _step_up_difficulty(current: str) -> str:
    """Return the next difficulty level up, or the same if already at advanced."""
    try:
        idx = _DIFFICULTY_ORDER.index(current)
    except ValueError:
        idx = 1  # default to standard if unknown
    return _DIFFICULTY_ORDER[min(idx + 1, len(_DIFFICULTY_ORDER) - 1)]


def _performance_band(score_pct: int) -> str:
    if score_pct < 40:
        return "needs_support"
    if score_pct < 60:
        return "developing"
    if score_pct < 80:
        return "strong"
    return "exceeding"


def _build_time_accuracy_summary(performance_band: str, time_band: str) -> str:
    return TIME_ACCURACY_MESSAGES.get((performance_band, time_band), "Session complete.")


def generate_session_summary(session: dict, questions: dict, total_time_ms: int = 0) -> SessionSummaryObject:
    """
    Compute SessionSummaryObject from completed session data.

    Args:
        session: session cache dict with 'responses', 'config', etc.
        questions: dict mapping question_id → QuestionObject
    """
    responses = session.get("responses", [])
    config = session.get("config", {})
    current_difficulty = config.get("difficulty", "standard")

    strand_data: dict[str, dict] = {}
    score = 0
    for r in responses:
        correct = r.get("correct", False)
        if correct:
            score += 1
        qid = r.get("question_id")
        q = questions.get(qid)
        if q is None:
            continue
        strand = q.strand if hasattr(q, "strand") else q.get("strand", "Unknown")
        if strand not in strand_data:
            strand_data[strand] = {"attempted": 0, "correct": 0}
        strand_data[strand]["attempted"] += 1
        if correct:
            strand_data[strand]["correct"] += 1

    by_strand: dict[str, StrandStat] = {}
    for strand, data in strand_data.items():
        attempted = data["attempted"]
        correct = data["correct"]
        pct = round(correct / attempted * 100) if attempted > 0 else 0
        by_strand[strand] = StrandStat(attempted=attempted, correct=correct, score_pct=pct)

    total = len(responses)
    score_pct = round(score / total * 100) if total > 0 else 0
    band = _performance_band(score_pct)

    # Weakest / strongest — only strands with ≥ 2 questions attempted
    eligible = {s: stat for s, stat in by_strand.items() if stat.attempted >= 2}

    weakest_strand: str | None = None
    strongest_strand: str | None = None
    if eligible:
        weakest_strand = min(eligible, key=lambda s: eligible[s].score_pct)
        strongest_strand = max(eligible, key=lambda s: eligible[s].score_pct)

    # Next session suggestion
    if weakest_strand is not None:
        weak_pct = by_strand[weakest_strand].score_pct
        weak_correct = by_strand[weakest_strand].correct
        weak_attempted = by_strand[weakest_strand].attempted

        if weak_pct < 40:
            suggested_difficulty = "foundation"
            reason = REASON_TEMPLATES["weak"].format(
                correct=weak_correct, attempted=weak_attempted, strand=weakest_strand
            )
        elif weak_pct <= 70:
            suggested_difficulty = current_difficulty
            reason = REASON_TEMPLATES["medium"].format(pct=weak_pct, strand=weakest_strand)
        else:
            suggested_difficulty = _step_up_difficulty(current_difficulty)
            if suggested_difficulty == current_difficulty:
                # Already at advanced — no higher level exists
                reason = REASON_TEMPLATES["strong_at_top"].format(strand=weakest_strand)
            else:
                reason = REASON_TEMPLATES["strong"].format(
                    strand=weakest_strand, next_difficulty=suggested_difficulty
                )

        suggestion = NextSessionSuggestion(
            strand=weakest_strand,
            difficulty=suggested_difficulty,
            reason=reason,
        )
    else:
        # All strands ≥ 80% or no eligible strands — suggest next strand alphabetically
        all_strands = sorted(strand_data.keys())
        session_strand = config.get("strand", "Mixed")
        if session_strand in all_strands:
            idx = all_strands.index(session_strand)
            next_strand = all_strands[(idx + 1) % len(all_strands)]
        else:
            # Fall back to global strand order
            taken = set(strand_data.keys())
            remaining = [s for s in STRAND_ORDER if s not in taken]
            next_strand = remaining[0] if remaining else (STRAND_ORDER[0] if STRAND_ORDER else "Algebra")

        all_good_difficulty = _step_up_difficulty(current_difficulty)
        all_good_reason = (
            REASON_TEMPLATES["all_good_at_top"]
            if all_good_difficulty == current_difficulty
            else REASON_TEMPLATES["all_good"]
        )
        suggestion = NextSessionSuggestion(
            strand=next_strand,
            difficulty=all_good_difficulty,
            reason=all_good_reason,
        )

    # Time band
    avg_ms = total_time_ms / total if total > 0 else 0
    if avg_ms < 20000:
        time_band = "fast"
    elif avg_ms <= 60000:
        time_band = "moderate"
    else:
        time_band = "slow"
    time_accuracy_summary = _build_time_accuracy_summary(band, time_band)

    return SessionSummaryObject(
        score=score,
        total=total,
        score_pct=score_pct,
        performance_band=band,
        by_strand=by_strand,
        weakest_strand=weakest_strand,
        strongest_strand=strongest_strand,
        next_session_suggestion=suggestion,
        total_time_ms=total_time_ms,
        avg_time_per_question_ms=int(avg_ms),
        time_band=time_band,
        time_accuracy_summary=time_accuracy_summary,
    )
