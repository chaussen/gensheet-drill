"""
ai_service.py
=============
Exactly two public functions (CLAUDE.md §6):
  - generate_questions(template_id, difficulty, count, param_schema)
  - analyse_session(session_data)

Provider is selected via AI_PROVIDER env var ("anthropic" | "google").
Model names are configurable via QUESTION_GEN_MODEL and ANALYSIS_MODEL env vars.

Prompts used verbatim from docs/ai_prompts.md. Do not change prompt text.
"""
import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

# ── Configuration from environment ────────────────────────────────────────────

AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic").lower()

# Model defaults differ by provider; QUESTION_GEN_MODEL / ANALYSIS_MODEL
# override whichever provider is active.
_PROVIDER_MODEL_DEFAULTS = {
    "anthropic": {
        "gen":      "claude-haiku-4-5-20251001",
        "analysis": "claude-sonnet-4-6",
    },
    "google": {
        "gen":      "gemini-2.0-flash",
        "analysis": "gemini-2.0-flash",
    },
}

_defaults = _PROVIDER_MODEL_DEFAULTS.get(AI_PROVIDER, _PROVIDER_MODEL_DEFAULTS["anthropic"])
QUESTION_GEN_MODEL = os.getenv("QUESTION_GEN_MODEL", _defaults["gen"])
ANALYSIS_MODEL     = os.getenv("ANALYSIS_MODEL",     _defaults["analysis"])

# ── Prompt constants (verbatim from docs/ai_prompts.md) ─────────────────────

_GEN_SYSTEM = (
    "You are a parameter generator for a mathematics drill system.\n"
    "Your ONLY task is to select valid parameter values from the ranges provided.\n"
    "You do NOT write questions. You do NOT compute answers. You do NOT explain anything.\n"
    "Return ONLY a valid JSON array. No markdown fences, no explanation, no preamble.\n"
    'Each item in the array is a "params" object for one question instance.'
)

_ANALYSIS_SYSTEM = """\
You are an educational assessment analyst for Australian secondary school mathematics.
You analyse student quiz results and provide structured, curriculum-referenced feedback.
Return ONLY a valid JSON object matching the schema below. No markdown, no explanation outside the JSON.

REQUIRED OUTPUT SCHEMA:
{
  "overall_score_pct": integer 0-100,
  "performance_band": "needs_support" | "developing" | "strong" | "exceeding",
  "strong_areas": [
    {"vc_code": string, "description": string, "score_pct": integer}
  ],
  "weak_areas": [
    {
      "vc_code": string,
      "description": string,
      "score_pct": integer,
      "error_pattern": string,
      "tip": string
    }
  ],
  "next_session_recommendation": {
    "focus_vc_codes": [string],
    "difficulty": "foundation" | "standard" | "advanced",
    "rationale": string
  },
  "motivational_note": string
}

RULES:
- performance_band: needs_support=0-39%, developing=40-59%, strong=60-79%, exceeding=80-100%
- strong_areas: include vc_codes where score_pct >= 80. Maximum 3 items.
- weak_areas: include vc_codes where score_pct < 60. Maximum 3 items, prioritised by lowest score.
- error_pattern: describe the specific mistake pattern you observe (e.g. "Forgot to flip inequality sign", "Used sin instead of cos"). Be specific, not generic.
- tip: one actionable study tip, maximum 2 sentences, age-appropriate for Year 7-9 student.
- next_session_recommendation.focus_vc_codes: maximum 3, choose from weak_areas.
- motivational_note: encouraging, specific to their result, 1-2 sentences, suitable for a 12-15 year old.
- Do not include vc_codes where there were fewer than 2 questions attempted."""


# ── Shared helper ─────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Strip markdown code fences before JSON parsing (CLAUDE.md §8)."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner)
    return text.strip()


# ── Anthropic provider ────────────────────────────────────────────────────────

_anthropic_client = None

def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _anthropic_client


async def _anthropic_call(system: str, user: str, model: str, max_tokens: int) -> str:
    client = _get_anthropic_client()
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ── Google (Gemini) provider ──────────────────────────────────────────────────

_google_client = None

def _get_google_client():
    global _google_client
    if _google_client is None:
        from google import genai
        _google_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _google_client


async def _google_call(system: str, user: str, model: str, max_tokens: int) -> str:
    from google.genai import types
    client = _get_google_client()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    return response.text


# ── Provider dispatch ─────────────────────────────────────────────────────────

async def _call(system: str, user: str, model: str, max_tokens: int) -> str:
    """Route to the active provider."""
    if AI_PROVIDER == "google":
        return await _google_call(system, user, model, max_tokens)
    return await _anthropic_call(system, user, model, max_tokens)


# ── Public API ────────────────────────────────────────────────────────────────

async def generate_questions(
    template_id: str,
    difficulty: str,
    count: int,
    param_schema: dict,
) -> list[dict]:
    """
    Ask the AI to pick valid parameter values for the given template.
    Returns a list of params dicts (length == count).
    Retries once on JSON parse failure; raises on second failure.
    Uses QUESTION_GEN_MODEL (cheap/fast model — haiku or gemini-flash).
    """
    param_schema_json = json.dumps(param_schema, indent=2)

    user_prompt = (
        f"Template ID: {template_id}\n"
        f"Parameter schema:\n{param_schema_json}\n\n"
        f"Generate {count} distinct parameter sets.\n"
        f"Each set must produce a different question (use varied values across the range).\n"
        f"Difficulty level: {difficulty}\n"
        f"Use only the values allowed for the '{difficulty}' difficulty tier.\n\n"
        f"Return a JSON array of {count} objects. Each object contains only the parameter keys "
        f"and their chosen values.\n"
        f"Example format (do not copy these values):\n"
        f"[\n"
        f'  {{"param_a": 5, "param_b": 3, "op": "+"}},\n'
        f'  {{"param_a": 8, "param_b": 12, "op": "-"}}\n'
        f"]"
    )

    last_err = None
    for attempt in range(2):
        try:
            raw = await _call(_GEN_SYSTEM, user_prompt, QUESTION_GEN_MODEL, max_tokens=1000)
            result = json.loads(_strip_markdown(raw))
            if isinstance(result, list) and len(result) > 0:
                return result
            raise ValueError(f"Expected non-empty list, got: {type(result)}")
        except Exception as e:
            last_err = e
            logger.warning(
                "generate_questions attempt %d failed for %s (provider=%s): %s",
                attempt + 1, template_id, AI_PROVIDER, e,
            )

    raise ValueError(
        f"generate_questions failed for {template_id} after 2 attempts: {last_err}"
    )


async def analyse_session(session_data: dict) -> dict | None:
    """
    Analyse a completed session and return an AnalysisObject dict.
    Returns None if analysis fails after retry (frontend shows 'unavailable').
    Called as a background task — never blocks the result screen.
    Uses ANALYSIS_MODEL (more capable model — sonnet or gemini-pro).
    """
    year_level  = session_data["year_level"]
    difficulty  = session_data["difficulty"]
    score       = session_data["score"]
    total       = session_data["total"]
    score_pct   = round(score / total * 100) if total > 0 else 0
    results_table = session_data["results_table"]

    user_prompt = (
        f"Student year level: Year {year_level}\n"
        f"Session difficulty: {difficulty}\n"
        f"Score: {score}/{total} ({score_pct}%)\n\n"
        f"Question-by-question results:\n{results_table}\n\n"
        f"The results table format is:\n"
        f"  Q# | VC Code | Topic | Student answer | Correct answer | Result"
    )

    for attempt in range(2):
        try:
            raw = await _call(_ANALYSIS_SYSTEM, user_prompt, ANALYSIS_MODEL, max_tokens=1500)
            return json.loads(_strip_markdown(raw))
        except Exception as e:
            logger.warning(
                "analyse_session attempt %d failed (provider=%s): %s",
                attempt + 1, AI_PROVIDER, e,
            )

    logger.error("analyse_session failed after 2 attempts — storing null")
    return None
