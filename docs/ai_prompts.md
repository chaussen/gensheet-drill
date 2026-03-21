# AI Prompts Reference
## GenSheet Drill — Use these prompts verbatim. Do not improvise.

---

## Prompt 1: Question Parameter Generation

**Used by:** `ai_service.py → generate_questions()`
**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 1000
**Called:** Once per question batch request (not per question)

### When to call
When the question cache is empty or needs replenishment for a given (year_level, strand, difficulty) combination.

### What the AI does
The AI picks valid parameter values from declared ranges. It does NOT write question text. The backend constructs question text from the template.

### System prompt
```
You are a parameter generator for a mathematics drill system.
Your ONLY task is to select valid parameter values from the ranges provided.
You do NOT write questions. You do NOT compute answers. You do NOT explain anything.
Return ONLY a valid JSON array. No markdown fences, no explanation, no preamble.
Each item in the array is a "params" object for one question instance.
```

### User prompt template
```
Template ID: {template_id}
Parameter schema:
{param_schema_json}

Generate {count} distinct parameter sets.
Each set must produce a different question (use varied values across the range).
Difficulty level: {difficulty}
Use only the values allowed for the '{difficulty}' difficulty tier.

Return a JSON array of {count} objects. Each object contains only the parameter keys and their chosen values.
Example format (do not copy these values):
[
  {{"param_a": 5, "param_b": 3, "op": "+"}},
  {{"param_a": 8, "param_b": 12, "op": "-"}}
]
```

### Expected response
```json
[
  {"a": 3, "b": 7, "op": "+"},
  {"a": -5, "b": 4, "op": "-"},
  ...
]
```

### Error handling
- If response is not valid JSON: retry once with the same prompt
- If retry fails: fall back to locally-generated random params (see `question_service.py → _fallback_params()`)
- Log all failures with template_id and difficulty

---

## Prompt 2: Session Analysis

**Used by:** `ai_service.py → analyse_session()`
**Model:** `claude-sonnet-4-6`
**Max tokens:** 1500
**Called:** Once after session submission. Async — frontend polls for result.

### When to call
After `POST /api/session/{id}/submit` completes scoring. Trigger as a background task.

### What the AI does
Analyses the student's session results and returns structured feedback: strengths, weaknesses, error patterns, and a next-session recommendation.

### System prompt
```
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
- Do not include vc_codes where there were fewer than 2 questions attempted.
```

### User prompt template
```
Student year level: Year {year_level}
Session difficulty: {difficulty}
Score: {score}/{total} ({score_pct}%)

Question-by-question results:
{results_table}

The results table format is:
  Q# | VC Code | Topic | Student answer | Correct answer | Result
```

### Results table construction (backend responsibility)
```python
def build_results_table(session, questions):
    rows = []
    for i, (resp, q) in enumerate(zip(session.responses, questions), 1):
        if q.question_type == "multi_select":
            student_answer = ", ".join(q.options[i] for i in (resp.selected_indices or []))
            correct_answer = ", ".join(q.options[i] for i in (q.correct_indices or []))
        else:
            student_answer = q.options[resp.selected_index]
            correct_answer = q.options[q.correct_index]
        rows.append(
            f"Q{i} | {q.vc_code} | {get_topic(q.template_id)} | "
            f"{student_answer} | {correct_answer} | "
            f"{'✓' if resp.correct else '✗'}"
        )
    return "\n".join(rows)
```

### Expected response
```json
{
  "overall_score_pct": 60,
  "performance_band": "strong",
  "strong_areas": [
    {"vc_code": "VC2M8A01", "description": "Expanding algebraic expressions", "score_pct": 100}
  ],
  "weak_areas": [
    {
      "vc_code": "VC2M8A02",
      "description": "Solving linear equations with pronumerals on both sides",
      "score_pct": 33,
      "error_pattern": "Moving terms to the same side without flipping the sign",
      "tip": "When you move a term across the equals sign, always change its sign. Try writing out each step on a new line."
    }
  ],
  "next_session_recommendation": {
    "focus_vc_codes": ["VC2M8A02"],
    "difficulty": "foundation",
    "rationale": "Build confidence with simpler equations before tackling two-sided problems."
  },
  "motivational_note": "You've got a solid grip on expanding — that's a key skill. Keep practising equations and you'll get there."
}
```

### Error handling
- Strip markdown fences before JSON.parse
- If JSON is invalid: retry once
- If retry fails: store `analysis: null` in session result
- Frontend handles `analysis: null` by showing "Analysis unavailable — try again later"
- Do NOT block the result screen waiting for analysis; show score immediately, analysis loads async

---

## Prompt Design Rationale (for reference only — do not change prompts)

**Why parametric generation instead of full question generation?**
Asking the AI to only pick parameter values (not write questions or compute answers) has three benefits:
1. Near-zero hallucination risk — selecting "5" from a range [1..12] cannot be wrong
2. Consistent question format — template controls structure, AI just fills numbers
3. Verification is clean — the backend independently computes the correct answer from params

**Why structured JSON output for analysis?**
The analysis object feeds directly into React components. Structured output eliminates frontend parsing complexity and makes A/B testing analysis quality straightforward.

**Why different models for each call?**
- Haiku: parameter selection is a trivially simple task; fast and cheap
- Sonnet: analysis requires nuanced pedagogical reasoning; quality matters more than speed
