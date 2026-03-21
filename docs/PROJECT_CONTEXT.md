# PROJECT_CONTEXT.md
## GenSheet Drill — Handoff Document
**Archive session:** https://claude.ai/chat/89e19c8b-45a5-4f02-9ee6-9301f7048ca1

---

## 1. What This Product Is

**GenSheet Drill** — a web-based MCQ drill platform for Australian secondary maths students (Years 7–9, Victorian Curriculum v2.0). Students pick year, strand, difficulty → answer a timed drill → receive auto-marked score + AI study analysis.

**This is not GenSheet** (the worksheet generator). It is a separate product that shares a brand. Do not conflate them.

---

## 2. Core Architecture Decisions (final, do not revisit)

| Decision | What was chosen | Why |
|---|---|---|
| Question generation | AI picks parameter values only; backend constructs question text | Eliminates hallucination risk on maths content |
| Answer verification | Python/sympy computes correct answer independently from params | AI never touches answer correctness |
| Auto-marking | `student_index == correct_index`, pure Python | No AI involved in marking |
| AI role | Exactly 2 calls: param generation (Haiku) + session analysis (Sonnet) | Minimal, bounded AI surface |
| Storage Phase 1 | In-memory cache (server) + localStorage (client) | No database |
| Auth | None — device fingerprint only | No login, no accounts |
| Hosting | Render free tier, FastAPI serves React static build | Single service |
| VC code exposure | **Removed from user-facing output** — see §6 | Content alignment via template design |

---

## 3. Tech Stack

```
Frontend:   React 18 (Vite) + Tailwind CSS — SPA only, no SSR
Backend:    FastAPI (Python 3.11+), async
AI:         Anthropic claude-haiku-4-5-20251001 (param gen) + claude-sonnet-4-6 (analysis)
Verify:     Python + sympy + fractions (pre-written, see docs/verification.py)
Deploy:     Render free tier
Keep-alive: UptimeRobot pings /api/health every 14 min
```

---

## 4. File Inventory

All files below exist. New project should have them in `docs/` alongside the VCAA curriculum JSONs.

| File | Purpose | Modify? |
|---|---|---|
| `docs/CLAUDE.md` | Full instructions for Claude Code coding assistant | No |
| `docs/question_templates.json` | 60 question templates, Years 7–9, all strands | Only to add curated bank entries |
| `docs/verification.py` | Complete Python verification engine, 44 verifier functions | No — copy to `backend/` as-is |
| `docs/schemas.json` | JSON schemas for all data objects | No |
| `docs/ai_prompts.md` | Exact prompts for both AI calls — use verbatim | No |

**VCAA curriculum JSONs** (already in new project) are the source of truth for content descriptions and code mappings. Use them when drafting curated bank entries.

---

## 5. Build State

### Done (Iterations 1 + 2 complete, plus post-launch fixes)
- FastAPI backend with all session endpoints
- Question pipeline: AI params → verify → assemble MCQ
- React frontend: session setup, drill UI, results screen
- AI provider switcher (bonus feature, already shipped)
- **Bug fix:** Fraction answers now formatted as "p/q" strings (sympy Rational preserved through pipeline)
- **Bug fix:** Post-generation validation enforces integer-solution constraint on T-7A-02, T-8A-02, T-9A-02, T-9A-04 (max 3 retries, then skip slot)
- **Feature:** Multi-select question type — `question_type: "single_select" | "multi_select"`, advanced difficulty only; 5 options, 2–3 correct; marked by set equality against `correct_indices`; 5 templates implemented (T-7N-02, T-7SP-01, T-8SP-02, T-9N-01, T-9A-05)

### Remaining iterations

| Iteration | What | Blocked on |
|---|---|---|
| 3 — Progress tracking | localStorage history, per-strand bar chart, weak spots summary | Curated banks (14 single_select banks still unpopulated) |
| 4 — Hardening + deploy | Question cache pre-warm, Render config, error handling, keep-alive | Iteration 3 done |

---

## 6. VC Code Decision (important — read before touching any code)

**Problem found:** VC codes in `question_templates.json` were assigned manually and some are wrong (at least Y7 Space and Algebra strand codes are mismatched against real VCAA data).

**Decision made:** Remove VC code dependency from all user-facing output for Phase 1.
- The AI analysis prompt should reference topics in plain English ("expanding brackets") not VC codes
- The results screen should show topic names not codes
- `vc_code` field stays in the data model for future use but is never displayed to students

**Do not** spend time auditing or fixing vc_code values. Do not expose them in the UI.

---

## 7. Curated Banks — Status and Instructions

14 question banks need populating before curated_bank templates can serve questions. These are templates where `"generation_mode": "curated_bank"` in `question_templates.json`.

**Current status: 0 of 14 populated** (single_select curated banks). The 5 multi_select templates (T-7N-02, T-7SP-01, T-8SP-02, T-9N-01, T-9A-05) have their banks implemented directly in `question_service.py` as `MULTI_SELECT_BANKS` — they do not use the bank entry format below.

Each bank entry format:
```json
{
  "question_key": "unique_snake_case_id",
  "question_text": "full question as shown to student",
  "correct_answer": "exact string that will be compared",
  "wrong_answers": ["wrong1", "wrong2", "wrong3"]
}
```

**Banks required (with minimum entry counts):**

| Bank key | Min | Content scope |
|---|---|---|
| `unit_conversion_bank` | 40 | km↔m↔cm↔mm, kg↔g, L↔mL |
| `rational_ordering_bank` | 30 | Ascending/descending order of fractions, decimals, mixed numbers |
| `shape_classification_bank` | 30 | Triangles by sides/angles; quads by properties |
| `graph_type_bank` | 25 | Scenario → most appropriate graph type |
| `composite_area_bank` | 25 | L-shapes, rect+triangle etc. — text-described, integer answers |
| `quadrilateral_properties_bank` | 25 | Identify quad from described properties |
| `time_zone_bank` | 25 | AEST/AEDT/UTC/London/New York/Singapore — whole-hour offsets only |
| `sample_space_bank` | 20 | Count outcomes for probability experiments |
| `cartesian_plane_bank` | 20 | Identify labelled point coordinates |
| `congruence_condition_bank` | 20 | SSS / SAS / AAS / RHS from described triangle info |
| `experimental_probability_bank` | 20 | Relative frequency from trial data |
| `rational_irrational_bank` | 20 | Classify real numbers; exploit common misconceptions |
| `nonlinear_classification_bank` | 20 | Identify linear/quadratic/hyperbola/exponential from equation |
| `outlier_effect_bank` | 15 | Effect of outlier on mean vs median — compute before and after |

**How to draft banks:** Use the VCAA curriculum JSON files already in this project to verify content scope. Cross-check every correct answer manually — especially composite_area_bank, time_zone_bank, and outlier_effect_bank which are arithmetic-heavy.

**Multi-select bank entries** (for the 5 templates supporting multi_select):
```json
{
  "question_key": "prime_factors_72_ms",
  "question_text": "Select all prime factors of 72.",
  "correct_answers": [2, 3],
  "all_options": [2, 3, 4, 6, 9],
  "question_type": "multi_select"
}
```

---

## 8. AI Service Spec (summary — full prompts in docs/ai_prompts.md)

**Call 1 — Parameter generation**
- Model: `claude-haiku-4-5-20251001`
- Input: template_id + param schema + difficulty + count
- Output: JSON array of params objects — AI picks numbers, nothing else
- Fallback: locally-generated random params if AI fails

**Call 2 — Session analysis**
- Model: `claude-sonnet-4-6`
- Input: full session results as table (Q# | Topic | student answer | correct | ✓/✗)
- Output: AnalysisObject JSON — weak areas, tips, next session recommendation
- Called async after submission; frontend polls; never blocks results screen
- Topic references must be plain English — no VC codes in output

---

## 9. Scope Boundary for Claude Code

**Claude Code builds:**
- FastAPI endpoints, routing, session logic
- React components (SessionSetup, DrillQuestion, DrillSession, ResultsScreen, ProgressView)
- AI service connector (2 functions only)
- Schema validation, verification engine integration
- localStorage progress layer
- Render deployment config

**Claude Code does NOT touch:**
- `docs/verification.py` — copy to `backend/` as-is, no edits
- `docs/question_templates.json` — read-only unless adding curated bank entries
- `docs/ai_prompts.md` — use prompts verbatim, no improvisation
- `docs/schemas.json` — reference only

---

## 10. Environment Variables

```
ANTHROPIC_API_KEY           required
QUESTION_CACHE_TTL_SECONDS  default 3600
MAX_QUESTIONS_PER_SESSION   default 20
MIN_QUESTIONS_PER_SESSION   default 5
```

---

## 11. Quick Reference — Data Flow

```
Student selects year/strand/difficulty
  → POST /api/session/start
    → AI generates params for N templates (Haiku)
    → Backend verifies answers with verification.py
    → Backend generates distractors by strategy
    → Returns QuestionObjects (correct_index EXCLUDED from response)
  → Student answers all questions
  → POST /api/session/{id}/submit
    → Backend marks: exact index match (single_select) or set equality (multi_select) — no AI
    → Background: AI analyses session (Sonnet) → AnalysisObject
  → GET /api/session/{id}/result
    → Returns scored responses + AnalysisObject (may still be null if AI pending)
    → Frontend writes session summary to localStorage
```
