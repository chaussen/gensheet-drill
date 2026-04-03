# GenSheet Drill — Bug Tracker

Bugs are logged here. Fixed bugs are kept for historical reference.

---

## BUG-001 — Y9 Number: duplicate questions within a session
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Start a 10-question Year 9 Number session (any difficulty).
  Actual: 3 out of 10 questions are word-for-word identical.
  Expected: all question texts are distinct.
**Root cause:** `generate_session_questions` deduplicates by `question_text` only for curated-bank templates. Y9 Number has 4 templates; `random.choices` picks the same parametric template multiple times, and the AI often returns identical params, producing identical question texts. Parametric templates were explicitly excluded from deduplication on the incorrect assumption that AI params are always varied.
**Root cause class:** PARAM_CONSTRAINT_VIOLATED
**Fix applied:** Removed the `curated_template_ids` restriction from the deduplication block in `generate_session_questions` — now ALL templates deduplicate by `question_text`. Updated the inline comment. (`backend/services/question_service.py`)
**Resolved:** 2026-04-03

---

## BUG-002 — Y9 Number (T-9N-02): scientific notation value displays as Python float repr; exponent not wrapped in LaTeX braces
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Start a Year 9 Number session. Observe T-9N-02 question and its MCQ options.
  Actual (question text): "Express 5.6e-05 in scientific notation." — value already looks like scientific notation (Python repr), confusing students.
  Actual (options): answers like "5.6 × 10^-5" render as "5.6 × 10^-5" in plain text instead of $5.6 \times 10^{-5}$.
  Expected (question text): "Express 0.000056 in scientific notation."
  Expected (options): properly typeset LaTeX with braced exponents.
**Root cause:** Two causes: (A) The `value` param is a Python float; `{value}` in the question template formats it with Python's default float repr (e.g. `5.6e-05`) instead of decimal notation. (B) `_to_latex_inner` converts `**N` → `^{N}` but never wraps bare `^N` patterns in braces, so the verifier's output `"5.6 × 10^-5"` becomes `$5.6 \times 10^-5$` in LaTeX — `^-` superscripts only the minus sign.
**Root cause class:** FORMAT_MISMATCH
**Fix applied:** (A) In `build_question`, for T-9N-02, convert the float `value` param to a decimal string via `Decimal` before question text rendering. (B) In `_to_latex_inner`, added `re.sub(r'\^(-?\d+)', r'^{\1}', s)` to wrap all bare `^N` / `^-N` in braces. (`backend/services/question_service.py`)
**Resolved:** 2026-04-03

---

## BUG-003 — Skipped questions shown as "wrong answer selected" in results
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Start a session, skip one or more questions (navigate past without selecting), then submit.
  Actual: skipped questions show a red ✗ border and "Your answer: Option A" in the breakdown (as if option A was selected).
  Expected: skipped questions show grey `—` border and a "skipped" badge; no "Your answer" row.
**Root cause:** `submitSession` in `useSession.js` builds responses with `ans?.selectedIndex ?? 0`. When a question is skipped, `ans` is undefined, so `selectedIndex` falls back to `0` — the first option is sent as the student's answer. The backend marks this as correct=false (unless option 0 happens to be correct). `isSkipped()` in `ResultsScreen` checks `r.selected_index == null`, which is false for index 0, so the question renders as wrong.
**Root cause class:** SCHEMA_DRIFT
**Fix applied:** In `useSession.js`, changed `?? 0` → `?? null` for single-select and `?? []` → `?? null` for multi-select skipped submissions. Updated `ResponseItem` validator in `schemas.py` to accept both `selected_index` and `selected_indices` being null (skipped). Added `test_submit_skipped_questions` test. (`frontend/src/hooks/useSession.js`, `backend/models/schemas.py`, `backend/tests/test_session_endpoints.py`)
**Resolved:** 2026-04-03

---

## BUG-004 — No way to return to question review after viewing progress history
**Found:** 2026-04-03
**Status:** Resolved
**Reproduce:**
  Complete a session → see ResultsScreen → click "View History" → AI generates progress report → click "← Back".
  Actual: "← Back" navigates to Session Setup, discarding the ResultsScreen with question breakdown.
  Expected: "← Back" returns to the most recent ResultsScreen so the student can review questions.
**Root cause:** ProgressView's `onBack` callback always calls `setBaseView('setup')`. The session result is still held in `useSession` state, but there is no navigation path back to 'results' from the progress view.
**Root cause class:** SCHEMA_DRIFT
**Fix applied:** In `App.jsx`, changed ProgressView's `onBack` to `() => setBaseView(session.result ? 'results' : 'setup')`. Since `session.result` is only cleared on `resetSession()` (which is called when starting a new session), the Back button returns to ResultsScreen when a recent result exists. (`frontend/src/App.jsx`)
**Resolved:** 2026-04-03
