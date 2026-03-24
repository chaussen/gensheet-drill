# GenSheet Drill — Backlog

**Backlog item 1: Integrate CURATED_WRONG banks**
```
The consultation session has produced CURATED_WRONG bank entries for 7 templates.
I will provide the all the JSON arrays in docs/curated_wrong_banks.json.

For each of these templates, change distractor_strategy to "CURATED_WRONG"
in docs/question_templates.json, and update question_service.py to read
wrong options from the provided bank entries rather than the distractor engine:
  T-7N-02, T-8N-02, T-8A-01, T-8A-03, T-8P-03, T-9A-01, T-9A-03
```

**Backlog item 2: Enforce session question count limits**
```
MIN_QUESTIONS_PER_SESSION and MAX_QUESTIONS_PER_SESSION are declared as env vars
but never enforced. The backend currently accepts any count from the client.
Add a guard to the session start endpoint that clamps the requested count
to the [min, max] range before processing. Return HTTP 400 with a clear message
if the requested count is outside the allowed range.
```

**Backlog item 3: Fix mixed session distribution for thin strands**
```
Two changes to question selection logic:

1. Disable mixed strand sessions for Year 9. When year=9 and strand=Mixed,
   return HTTP 400: "Mixed sessions are not available for Year 9.
   Please select a specific strand."
   Also disable Statistics for Year 9 (only 1 template).

2. For Year 7 and 8 mixed sessions, weight strand selection by template count
   rather than distributing evenly. Strands with fewer than 3 parametric
   templates should appear proportionally less. Document the approach in a comment.
