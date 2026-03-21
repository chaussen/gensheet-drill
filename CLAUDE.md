# CLAUDE.md — GenSheet Drill
## AI Coding Assistant Instructions

> Read this file in full before writing a single line of code.
> All design decisions are pre-made. Your job is implementation only.

---

## 1. What This Project Is

**GenSheet Drill** is a web-based student practice platform for Australian secondary school mathematics (Years 7–9, Victorian Curriculum v2.0).

Students select a year level, strand, and difficulty. The system delivers a timed multiple-choice drill session, auto-marks it, then calls an AI service to generate a personalised study analysis.

---

## 2. Critical Scope Boundary — Read This First

This project has two clearly separated layers:

### ✅ YOUR JOB (implement this)
- FastAPI backend: endpoints, routing, session management, scoring logic
- React frontend: UI components, state management, API calls
- AI service connector: exactly 2 call types (question generation + session analysis)
- Schema validation: enforce question JSON shape before it reaches the student
- Verification engine: run `verification.py` to compute correct answers (file is pre-written)
- localStorage: persist session history client-side
- Render deployment: Procfile, keep-alive, environment config

### ❌ NOT YOUR JOB (already designed — do not modify)
- Question template design (defined in `docs/question_templates.json`)
- Verification logic (implemented in `docs/verification.py` — copy to `backend/`)
- Distractor strategies (defined in `docs/question_templates.json`)
- Curriculum scope decisions (already made — see taxonomy section)
- AI prompt content (defined in `docs/ai_prompts.md` — use verbatim)
- JSON schemas (defined in `docs/schemas.json`)

**If you think a template is wrong or a verifier is incorrect: do not change it. Add a TODO comment and continue.**

---

## 3. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 18 (Vite) | No Next.js, no SSR — SPA only |
| Styling | Tailwind CSS | Core utilities only, no custom config |
| Backend | FastAPI (Python 3.11+) | Async endpoints |
| AI service | Anthropic Claude API | `claude-haiku-4-5-20251001` for generation, `claude-sonnet-4-6` for analysis |
| Verification | Python + sympy + fractions | Pre-written — see `docs/verification.py` |
| Storage (Phase 1) | localStorage (client) + in-memory cache (server) | No database |
| Hosting | Render free tier | Single web service, FastAPI serves React build |

---

## 4. Project File Structure

```
gensheet-drill/
├── CLAUDE.md                    ← this file
├── docs/
│   ├── question_templates.json  ← PRE-DEFINED. do not modify.
│   ├── schemas.json             ← PRE-DEFINED. do not modify.
│   ├── verification.py          ← PRE-WRITTEN. copy to backend/, do not modify.
│   └── ai_prompts.md            ← PRE-WRITTEN. use verbatim.
├── backend/
│   ├── main.py                  ← FastAPI app entry point
│   ├── routers/
│   │   ├── session.py           ← /api/session/* endpoints
│   │   └── questions.py         ← /api/questions/* endpoints
│   ├── services/
│   │   ├── question_service.py  ← orchestrates generation + verification
│   │   ├── ai_service.py        ← wraps Anthropic API calls (2 functions only)
│   │   ├── verification.py      ← copied from docs/verification.py
│   │   └── distractor_service.py← generates wrong options from strategy
│   ├── models/
│   │   └── schemas.py           ← Pydantic models matching docs/schemas.json
│   ├── cache.py                 ← in-memory question cache
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── SessionSetup.jsx ← year/strand/difficulty selector
│   │   │   ├── DrillQuestion.jsx← single MCQ question display
│   │   │   ├── DrillSession.jsx ← orchestrates question flow
│   │   │   ├── ResultsScreen.jsx← score + analysis display
│   │   │   └── ProgressView.jsx ← history from localStorage
│   │   ├── hooks/
│   │   │   ├── useSession.js    ← session state management
│   │   │   └── useProgress.js   ← localStorage read/write
│   │   └── api/
│   │       └── client.js        ← all fetch calls to backend
│   ├── package.json
│   └── vite.config.js
├── Procfile                     ← Render deployment
└── .env.example
```

---

## 5. Implementation Iterations

Build in this exact order. Do not start Iteration 2 until Iteration 1 passes its milestone test.

### Iteration 1 — Backend Core (no UI)
**Goal:** Question pipeline works end-to-end via curl/Postman.

Tasks:
1. Copy `docs/verification.py` → `backend/verification.py`
2. Build `distractor_service.py` using strategy codes from `docs/question_templates.json`
3. Build `ai_service.py` with exactly 2 public functions: `generate_questions()` and `analyse_session()`
4. Build `question_service.py` that chains: AI call → schema validate → verify answers → assemble options
5. Build session endpoints: `POST /api/session/start`, `POST /api/session/{id}/submit`, `GET /api/session/{id}/result`
6. Build `GET /api/health` keep-alive endpoint

**Milestone test:** `curl -X POST /api/session/start -d '{"year_level":8,"strand":"Algebra","difficulty":"standard","count":5}'` returns 5 valid, verified questions with 4 MCQ options each.

---

### Iteration 2 — React Frontend
**Goal:** Student can complete a full drill session in the browser.

Tasks:
1. `SessionSetup.jsx`: dropdowns for Year (7/8/9), Strand (6 options + "Mixed"), Difficulty (foundation/standard/advanced), question count (5/10/15)
2. `DrillSession.jsx`: fetch questions from backend on mount; display one at a time with progress indicator
3. `DrillQuestion.jsx`: render question text + 4 MCQ options as buttons; highlight selection; no correct/wrong reveal until session submitted
4. `ResultsScreen.jsx`: show score, band, analysis object (weak areas + tips + recommendation)
5. Wire submit: `POST /api/session/{id}/submit` with all response indices

**Milestone test:** Complete a 10-question Year 8 Algebra session in browser; see score and analysis.

---

### Iteration 3 — Progress Tracking
**Goal:** Student can see their history across sessions on same device.

Tasks:
1. `useProgress.js` hook: read/write localStorage key `gensheet_progress`
2. After each session: append session summary to localStorage progress record
3. `ProgressView.jsx`: show sessions table + per-strand bar chart (use recharts or plain SVG)
4. Aggregate `by_vc_code` stats for the "your weak spots" summary

**Milestone test:** Complete 3 sessions; progress view shows all 3 with correct scores and weak area summary.

---

### Iteration 4 — Hardening & Deployment
**Goal:** Live on Render with acceptable performance.

Tasks:
1. Question cache (`cache.py`): pre-generate 20 questions per (year × strand × difficulty) on startup
2. Render config: `Procfile`, `build.sh`, static file serving from FastAPI
3. Keep-alive: `/api/health` returns `{"status":"ok","ts":"..."}`, configure UptimeRobot to ping every 14 min
4. Error handling: graceful fallback if AI service fails (return cached questions; if cache empty, return 503 with message)
5. Environment: `ANTHROPIC_API_KEY` via Render env vars, never hardcoded

**Milestone test:** Deploy to Render. Cold start within 30s. 10 consecutive sessions with no errors.

---

## 6. AI Service — Exact Specification

The AI service has **exactly two functions**. Nothing else.

### Function 1: `generate_questions(template_id, difficulty, count)`

**What it does:** Asks the AI to pick valid parameter values for a given template. The AI does NOT write questions — it selects numbers within declared ranges.

**Returns:** List of `params` dicts. Backend constructs question text, verifies answer, builds options.

See `docs/ai_prompts.md` → Section "Question Generation Prompt" for the exact prompt. Use it verbatim.

**Model:** `claude-haiku-4-5-20251001`
**Max tokens:** 1000
**Expected latency:** <3s per batch of 10

---

### Function 2: `analyse_session(session_data)`

**What it does:** Receives a completed session object and returns an AnalysisObject JSON with weak areas, tips, and next session recommendation.

**Returns:** AnalysisObject (see `docs/schemas.json`)

See `docs/ai_prompts.md` → Section "Session Analysis Prompt" for the exact prompt. Use it verbatim.

**Model:** `claude-sonnet-4-6`
**Max tokens:** 1500
**Expected latency:** <8s
**Called once per session, after submission, not during**

---

## 7. Auto-Marking — No AI Involved

Marking is pure Python. After the student submits:

```python
for response in submission.responses:
    question = get_question(response.question_id)
    response.correct = (response.selected_index == question.correct_index)
session.score = sum(r.correct for r in session.responses)
```

`correct_index` is set by the verification engine during question generation, never by the AI.

---

## 8. Key Constraints

- **No database.** Phase 1 uses in-memory cache (server) + localStorage (client). Do not add SQLite, Redis, or any DB.
- **No user accounts.** No login, no registration, no JWT. Student identity = device fingerprint stored in localStorage.
- **No markdown formatting in AI responses.** Both AI prompts instruct the model to return raw JSON only. If response contains markdown fences, strip them before parsing.
- **Always validate before storing.** Every question object from the AI must pass Pydantic validation AND verification before it is cached or returned.
- **Render free tier limits.** Do not add any dependency that requires >512MB RAM. Keep `requirements.txt` lean.
- **Single service.** FastAPI serves both the API and the React static build. No separate frontend deployment.

---

## 9. Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...        # required
QUESTION_CACHE_TTL_SECONDS=3600    # default 3600
MAX_QUESTIONS_PER_SESSION=20       # default 20
MIN_QUESTIONS_PER_SESSION=5        # default 5
KEEP_ALIVE_INTERVAL_SECONDS=840    # 14 min, for UptimeRobot
```

---

## 10. Reference Files — Read These Next

After reading CLAUDE.md, read these in order:

1. `docs/question_templates.json` — full template library (60 templates, Years 7–9)
2. `docs/schemas.json` — Pydantic/JSON schemas for all data objects
3. `docs/verification.py` — complete verification engine (copy to `backend/`)
4. `docs/ai_prompts.md` — exact prompts for both AI calls

Do not proceed to coding until you have read all four.
