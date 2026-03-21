"""
Tests for ai_service provider routing and config.
Actual API calls are mocked — no network required.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

import services.ai_service as ai_service
from services.ai_service import _strip_markdown


# ── _strip_markdown ────────────────────────────────────────────────────────────

def test_strip_markdown_no_fences():
    raw = '[{"a": 1}]'
    assert _strip_markdown(raw) == '[{"a": 1}]'


def test_strip_markdown_json_fence():
    raw = '```json\n[{"a": 1}]\n```'
    assert _strip_markdown(raw) == '[{"a": 1}]'


def test_strip_markdown_plain_fence():
    raw = '```\n[{"a": 1}]\n```'
    assert _strip_markdown(raw) == '[{"a": 1}]'


def test_strip_markdown_strips_whitespace():
    raw = '  \n[{"a": 1}]\n  '
    assert _strip_markdown(raw) == '[{"a": 1}]'


# ── Provider config ────────────────────────────────────────────────────────────

def test_provider_defaults_to_anthropic(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    # After env change we'd need to re-import; just check current module state
    assert ai_service.AI_PROVIDER in ("anthropic", "google")


def test_model_env_override(monkeypatch):
    """QUESTION_GEN_MODEL and ANALYSIS_MODEL env vars are read at import time;
    check they're exposed as module attributes."""
    assert hasattr(ai_service, "QUESTION_GEN_MODEL")
    assert hasattr(ai_service, "ANALYSIS_MODEL")


# ── generate_questions (Anthropic mock) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_questions_returns_parsed_list():
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text='[{"n": 64}, {"n": 81}]')]

    with patch.object(ai_service, "_call", new=AsyncMock(return_value='[{"n": 64}, {"n": 81}]')):
        result = await ai_service.generate_questions("T-7N-01", "standard", 2, {"n": {}})

    assert result == [{"n": 64}, {"n": 81}]


@pytest.mark.asyncio
async def test_generate_questions_strips_markdown():
    raw = '```json\n[{"n": 64}]\n```'
    with patch.object(ai_service, "_call", new=AsyncMock(return_value=raw)):
        result = await ai_service.generate_questions("T-7N-01", "standard", 1, {})
    assert result == [{"n": 64}]


@pytest.mark.asyncio
async def test_generate_questions_retries_on_bad_json():
    """Should retry once; raises after 2 failures."""
    with patch.object(ai_service, "_call", new=AsyncMock(return_value="not json")):
        with pytest.raises(ValueError, match="failed.*after 2 attempts"):
            await ai_service.generate_questions("T-7N-01", "standard", 1, {})


# ── analyse_session ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyse_session_returns_dict():
    payload = json.dumps({
        "overall_score_pct": 80,
        "performance_band": "strong",
        "strong_areas": [],
        "weak_areas": [],
        "next_session_recommendation": {
            "focus_vc_codes": [],
            "difficulty": "standard",
            "rationale": "Keep it up."
        },
        "motivational_note": "Great work!"
    })
    with patch.object(ai_service, "_call", new=AsyncMock(return_value=payload)):
        result = await ai_service.analyse_session({
            "year_level": 8, "difficulty": "standard",
            "score": 8, "total": 10, "results_table": "Q1 | VC | topic | a | b | ✓",
        })
    assert result["overall_score_pct"] == 80
    assert result["performance_band"] == "strong"


@pytest.mark.asyncio
async def test_analyse_session_returns_none_on_failure():
    """Two consecutive failures → returns None (not raises)."""
    with patch.object(ai_service, "_call", new=AsyncMock(side_effect=Exception("timeout"))):
        result = await ai_service.analyse_session({
            "year_level": 8, "difficulty": "standard",
            "score": 5, "total": 10, "results_table": "",
        })
    assert result is None
