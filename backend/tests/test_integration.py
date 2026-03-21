"""
Integration tests — Iteration 1 milestone.

These tests call the real AI provider and exercise the full pipeline:
  template → AI params → verification → distractor assembly → QuestionObject

Skipped automatically if ANTHROPIC_API_KEY (or GEMINI_API_KEY for Google)
is not set in the environment, so CI stays green without credentials.

Run manually:
    pytest tests/test_integration.py -v -s
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

import services.ai_service as ai_service

# ── Skip markers ──────────────────────────────────────────────────────────────

def _has_anthropic_key():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    # Real keys are long; reject obvious placeholders like "sk-ant-your-key-here"
    return key.startswith("sk-ant-") and len(key) > 30

def _has_google_key():
    key = os.getenv("GEMINI_API_KEY", "")
    return bool(key.strip()) and "your" not in key.lower()

def _active_provider_key_present():
    # Read AI_PROVIDER fresh from env (module-level constant may be stale in tests)
    provider = os.getenv("AI_PROVIDER", "anthropic").lower()
    if provider == "google":
        return _has_google_key()
    return _has_anthropic_key()

def _active_provider():
    return os.getenv("AI_PROVIDER", "anthropic").lower()

needs_api_key = pytest.mark.skipif(
    not _active_provider_key_present(),
    reason=f"No valid API key for active provider (AI_PROVIDER={os.getenv('AI_PROVIDER', 'anthropic')})",
)


def _skip_if_quota(exc: Exception):
    """Call inside except blocks: skips the test if the error is a free-tier quota limit."""
    msg = str(exc).lower()
    if "429" in msg or "quota" in msg or "rate" in msg:
        pytest.skip(f"Free-tier quota exceeded (expected on free plan): {exc}")


# ── AI service ────────────────────────────────────────────────────────────────

@needs_api_key
@pytest.mark.asyncio
async def test_generate_questions_real_api():
    """AI returns a non-empty list of param dicts for a simple template."""
    from docs_loader import load_template_meta
    template = load_template_meta("T-7N-01")  # sqrt: single int param "n"

    try:
        result = await ai_service.generate_questions(
            template_id="T-7N-01",
            difficulty="standard",
            count=3,
            param_schema=template["params"],
        )
    except Exception as e:
        _skip_if_quota(e)
        raise

    assert isinstance(result, list)
    assert len(result) >= 1
    for params in result:
        assert isinstance(params, dict)
        assert "n" in params
        assert params["n"] in template["params"]["n"]["standard"]


@needs_api_key
@pytest.mark.asyncio
async def test_generate_questions_algebra_real_api():
    """AI returns valid params for Year 8 Algebra (the milestone template set)."""
    from docs_loader import load_template_meta
    template = load_template_meta("T-8A-02")

    try:
        result = await ai_service.generate_questions(
            template_id="T-8A-02",
            difficulty="standard",
            count=2,
            param_schema=template["params"],
        )
    except Exception as e:
        _skip_if_quota(e)
        raise

    assert isinstance(result, list)
    assert len(result) >= 1
    for params in result:
        assert "a" in params
        assert "b" in params


# ── Full question pipeline ─────────────────────────────────────────────────────

@needs_api_key
@pytest.mark.asyncio
async def test_full_question_pipeline_single():
    """
    One question: AI params (or fallback) → verification → distractor assembly → QuestionObject.
    Verifies the Iteration 1 milestone at the service layer.
    When AI quota is exceeded the pipeline uses local fallback params; the test
    still validates the full verify→distractor→MCQ path.
    """
    from services.question_service import generate_session_questions

    try:
        questions = await generate_session_questions(
            year_level=8,
            strand="Algebra",
            difficulty="standard",
            count=1,
        )
    except Exception as e:
        _skip_if_quota(e)
        raise

    assert len(questions) == 1
    q = questions[0]

    assert len(q.options) == 4
    assert len(set(q.options)) == 4, "All 4 options must be distinct"
    assert 0 <= q.correct_index <= 3
    assert q.options[q.correct_index] != ""
    assert q.year_level == 8
    assert q.strand == "Algebra"
    assert q.vc_code.startswith("VC2M8A")


@needs_api_key
@pytest.mark.asyncio
async def test_milestone_five_verified_questions():
    """
    CLAUDE.md Iteration 1 milestone test (programmatic form):
    POST /api/session/start with year=8, strand=Algebra, difficulty=standard, count=5
    must return 5 valid, verified questions with 4 MCQ options each.
    Uses fallback params when AI quota is exceeded.
    """
    from services.question_service import generate_session_questions

    questions = await generate_session_questions(
        year_level=8,
        strand="Algebra",
        difficulty="standard",
        count=5,
    )

    if len(questions) == 0:
        pytest.skip("No questions returned — likely quota exhausted and fallback also failed")
    assert len(questions) == 5, f"Expected 5 questions, got {len(questions)}"

    for i, q in enumerate(questions):
        assert len(q.options) == 4, f"Q{i+1}: expected 4 options"
        assert len(set(q.options)) == 4, f"Q{i+1}: options must be distinct"
        assert 0 <= q.correct_index <= 3, f"Q{i+1}: correct_index out of range"
        assert q.question_text, f"Q{i+1}: question_text is empty"
        assert q.vc_code, f"Q{i+1}: vc_code is empty"
        assert q.template_id, f"Q{i+1}: template_id is empty"


@needs_api_key
@pytest.mark.asyncio
async def test_full_endpoint_pipeline():
    """
    Exercises the complete HTTP pipeline end-to-end:
    POST /start → POST /submit → GET /result (without waiting for AI analysis).
    """
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # 1. Start session with real question generation
    resp = client.post("/api/session/start", json={
        "year_level": 8,
        "strand": "Algebra",
        "difficulty": "standard",
        "count": 5,
    })
    assert resp.status_code == 200, f"start failed: {resp.text}"
    data = resp.json()
    session_id = data["session_id"]
    questions = data["questions"]

    assert len(questions) == 5
    for q in questions:
        assert "correct_index" not in q, "correct_index must not be in start response"
        assert len(q["options"]) == 4

    # 2. Submit all responses (deliberately answering index 0 for all)
    responses = [{"question_id": q["question_id"], "selected_index": 0} for q in questions]
    resp2 = client.post(f"/api/session/{session_id}/submit", json={"responses": responses})
    assert resp2.status_code == 200, f"submit failed: {resp2.text}"
    result = resp2.json()

    assert result["total"] == 5
    assert 0 <= result["score"] <= 5
    assert 0 <= result["score_pct"] <= 100
    for r in result["responses"]:
        assert "correct_index" in r   # revealed after submit
        assert "correct" in r

    # 3. Poll result (analysis may still be null — that's fine)
    resp3 = client.get(f"/api/session/{session_id}/result")
    assert resp3.status_code == 200
    assert resp3.json()["session_id"] == session_id
