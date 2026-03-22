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
