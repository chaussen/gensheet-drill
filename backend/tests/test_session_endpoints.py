"""
Tests for session API endpoints using FastAPI TestClient.
AI calls and question generation are mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from main import app
from models.schemas import QuestionObject
from datetime import datetime, timezone


def _make_question(q_id: str, correct_index: int = 2) -> QuestionObject:
    options = ["wrong_a", "wrong_b", "correct", "wrong_c"]
    return QuestionObject(
        question_id=q_id,
        template_id="T-8A-02",
        vc_code="VC2M8A02",
        year_level=8,
        strand="Algebra",
        difficulty="standard",
        question_text="Solve: 3x + 2 = x + 8",
        options=options,
        correct_index=correct_index,
        explanation="The correct answer is 3.",
        params={"a": 3, "b": 2, "c": 1, "d": 8},
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


MOCK_QUESTIONS = [_make_question(f"qid-{i}", correct_index=2) for i in range(5)]


@pytest.fixture
def client():
    return TestClient(app)


# ── POST /api/session/start ───────────────────────────────────────────────────

def test_start_session_returns_200(client):
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 8,
            "strand": "Algebra",
            "difficulty": "standard",
            "count": 5,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["questions"]) == 5


def test_start_session_omits_correct_index(client):
    """Frontend must not receive correct_index."""
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 8, "strand": "Algebra",
            "difficulty": "standard", "count": 5,
        })
    for q in resp.json()["questions"]:
        assert "correct_index" not in q


def test_start_session_503_on_empty_questions(client):
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=[]),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 8, "strand": "Algebra",
            "difficulty": "standard", "count": 5,
        })
    assert resp.status_code == 503


def test_start_session_invalid_year(client):
    resp = client.post("/api/session/start", json={
        "year_level": 10, "difficulty": "standard"
    })
    # Pydantic rejects year_level=10 (not in Literal[7,8,9]) → 422
    assert resp.status_code == 422


def test_start_session_invalid_difficulty(client):
    resp = client.post("/api/session/start", json={
        "year_level": 8, "difficulty": "expert"
    })
    assert resp.status_code == 422


# ── POST /api/session/{id}/submit ─────────────────────────────────────────────

def _start_and_get_session(client):
    """Helper: start a session and return (session_id, question_ids)."""
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 8, "strand": "Algebra",
            "difficulty": "standard", "count": 5,
        })
    data = resp.json()
    return data["session_id"], [q["question_id"] for q in data["questions"]]


def test_submit_session_marks_correctly(client):
    session_id, q_ids = _start_and_get_session(client)
    responses = [{"question_id": qid, "selected_index": 2} for qid in q_ids]  # all correct

    resp = client.post(f"/api/session/{session_id}/submit", json={"responses": responses})

    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 5
    assert data["total"] == 5
    assert data["score_pct"] == 100
    assert all(r["correct"] for r in data["responses"])
    assert data["summary"] is not None
    assert data["summary"]["score"] == 5
    assert data["summary"]["performance_band"] == "exceeding"


def test_submit_session_marks_wrong(client):
    session_id, q_ids = _start_and_get_session(client)
    # Answer index 0 = wrong for all (correct is index 2)
    responses = [{"question_id": qid, "selected_index": 0} for qid in q_ids]

    resp = client.post(f"/api/session/{session_id}/submit", json={"responses": responses})

    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 0
    assert not any(r["correct"] for r in data["responses"])
    assert data["summary"]["performance_band"] == "needs_support"


def test_submit_reveals_correct_index(client):
    """After submit, correct_index must be in the response."""
    session_id, q_ids = _start_and_get_session(client)
    responses = [{"question_id": qid, "selected_index": 1} for qid in q_ids]

    resp = client.post(f"/api/session/{session_id}/submit", json={"responses": responses})

    for r in resp.json()["responses"]:
        assert "correct_index" in r
        assert r["correct_index"] == 2


def test_submit_skipped_questions(client):
    """
    Skipped questions (no selected_index) must be marked correct=False and
    selected_index must be None in the response so the frontend can display them
    as 'skipped' rather than 'wrong answer selected'.
    """
    session_id, q_ids = _start_and_get_session(client)
    # Submit with no selection for all questions (all skipped)
    responses = [{"question_id": qid} for qid in q_ids]

    resp = client.post(f"/api/session/{session_id}/submit", json={"responses": responses})

    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 0
    assert all(not r["correct"] for r in data["responses"])
    # selected_index must be null so the frontend isSkipped() check works
    for r in data["responses"]:
        assert r["selected_index"] is None


def test_submit_double_submit_rejected(client):
    session_id, q_ids = _start_and_get_session(client)
    responses = [{"question_id": qid, "selected_index": 0} for qid in q_ids]

    client.post(f"/api/session/{session_id}/submit", json={"responses": responses})
    resp2 = client.post(f"/api/session/{session_id}/submit", json={"responses": responses})

    assert resp2.status_code == 400


def test_submit_unknown_session(client):
    resp = client.post("/api/session/nonexistent-id/submit", json={"responses": []})
    assert resp.status_code == 404


# ── GET /api/session/{id}/result ──────────────────────────────────────────────

def test_get_result_before_submit_returns_400(client):
    session_id, _ = _start_and_get_session(client)
    resp = client.get(f"/api/session/{session_id}/result")
    assert resp.status_code == 400


def test_get_result_after_submit(client):
    session_id, q_ids = _start_and_get_session(client)
    responses = [{"question_id": qid, "selected_index": 2} for qid in q_ids]

    client.post(f"/api/session/{session_id}/submit", json={"responses": responses})
    resp = client.get(f"/api/session/{session_id}/result")

    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 5
    assert data["summary"] is not None
    assert data["analysis"] is None


def test_get_result_unknown_session(client):
    resp = client.get("/api/session/does-not-exist/result")
    assert resp.status_code == 404


# ── GET /api/health ───────────────────────────────────────────────────────────

def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "ts" in data
    assert "cache_size" in data


# ── Year 9 strand restrictions ────────────────────────────────────────────────

def test_y9_mixed_rejected(client):
    """Year 9 Mixed sessions must be rejected with 400."""
    resp = client.post("/api/session/start", json={
        "year_level": 9,
        "strand": "Mixed",
        "difficulty": "standard",
        "count": 5,
    })
    assert resp.status_code == 400
    assert "Mixed" in resp.json()["detail"]


def test_y9_statistics_rejected(client):
    """Year 9 Statistics sessions must be rejected with 400."""
    resp = client.post("/api/session/start", json={
        "year_level": 9,
        "strand": "Statistics",
        "difficulty": "standard",
        "count": 5,
    })
    assert resp.status_code == 400
    assert "Statistics" in resp.json()["detail"]


def test_y8_mixed_allowed(client):
    """Year 8 Mixed sessions must not be rejected by the Y9 guard."""
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 8,
            "strand": "Mixed",
            "difficulty": "standard",
            "count": 5,
        })
    assert resp.status_code == 200


def test_y9_algebra_allowed(client):
    """Year 9 single-strand sessions (other than Statistics) must proceed."""
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 9,
            "strand": "Algebra",
            "difficulty": "standard",
            "count": 5,
        })
    assert resp.status_code == 200


# ── Question count enforcement ────────────────────────────────────────────────

def test_count_below_minimum_rejected(client):
    """count=4 is below the Pydantic ge=5 constraint — rejected with 422."""
    resp = client.post("/api/session/start", json={
        "year_level": 8,
        "strand": "Algebra",
        "difficulty": "standard",
        "count": 4,
    })
    assert resp.status_code == 422  # Pydantic validation (ge=5) fires before endpoint logic


def test_count_above_global_maximum_rejected(client):
    """count=21 exceeds the Pydantic le=20 constraint — rejected with 422."""
    resp = client.post("/api/session/start", json={
        "year_level": 8,
        "strand": "Algebra",
        "difficulty": "standard",
        "count": 21,
    })
    assert resp.status_code == 422  # Pydantic validation (le=20) fires before endpoint logic


def test_count_above_tier_max_rejected(client):
    """Free tier cap is 10; count=15 must be rejected by tier enforcement."""
    with patch("routers.session.get_tier_config", return_value={
        "tier": "free",
        "daily_session_limit": 3,
        "max_question_count": 10,
        "question_count_options": [5, 10],
    }):
        resp = client.post("/api/session/start", json={
            "year_level": 8,
            "strand": "Algebra",
            "difficulty": "standard",
            "count": 15,
        })
    assert resp.status_code == 400
    assert "10" in resp.json()["detail"]


def test_count_at_minimum_accepted(client):
    """count=5 is exactly the minimum — must be accepted."""
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ):
        resp = client.post("/api/session/start", json={
            "year_level": 8,
            "strand": "Algebra",
            "difficulty": "standard",
            "count": 5,
        })
    assert resp.status_code == 200


# ── Daily session limit (429) ─────────────────────────────────────────────────

def test_daily_limit_returns_429(client):
    """When a student exceeds their daily session cap, the endpoint must return 429."""
    with patch("routers.session.get_tier_config", return_value={
        "tier": "free",
        "daily_session_limit": 3,
        "max_question_count": 10,
        "question_count_options": [5, 10],
    }), patch("routers.session.session_cache") as mock_cache:
        mock_cache.count_today.return_value = 3  # already at limit
        resp = client.post("/api/session/start", json={
            "year_level": 8,
            "strand": "Algebra",
            "difficulty": "standard",
            "count": 5,
            "student_id": "student-abc",
        })
    assert resp.status_code == 429


def test_daily_limit_not_triggered_without_student_id(client):
    """If no student_id is supplied, the daily limit check is skipped."""
    with patch(
        "routers.session.generate_session_questions",
        new=AsyncMock(return_value=MOCK_QUESTIONS),
    ), patch("routers.session.get_tier_config", return_value={
        "tier": "free",
        "daily_session_limit": 0,  # even 0-limit is bypassed without student_id
        "max_question_count": 10,
        "question_count_options": [5, 10],
    }):
        resp = client.post("/api/session/start", json={
            "year_level": 8,
            "strand": "Algebra",
            "difficulty": "standard",
            "count": 5,
            # no student_id
        })
    assert resp.status_code == 200


# ── GET /api/config/limits ────────────────────────────────────────────────────

def test_config_limits_endpoint(client):
    """GET /api/config/limits must return tier, daily_session_limit, and question_count_options."""
    resp = client.get("/api/config/limits")
    assert resp.status_code == 200
    data = resp.json()
    assert "tier" in data
    assert "daily_session_limit" in data
    assert "max_question_count" in data
    assert "question_count_options" in data
    assert isinstance(data["question_count_options"], list)
    assert len(data["question_count_options"]) >= 1
