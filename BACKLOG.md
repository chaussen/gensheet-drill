# GenSheet Drill — Backlog: Drill Loop Enhancements

**Principle:** Code handles complexity. AI stays strictly guided. No new screens, no gamification — just a sharper drill-answer-review loop.

---

## ENHANCEMENT A: Weighted Question Selection (Weak-Topic Targeting)

**Goal:** Silently serve more questions from topics the student has historically answered poorly. No UI change — the drill just gets smarter.

### A1 — Build topic accuracy index from localStorage

**What:** Add a utility function that reads all past session results from localStorage and computes a per-topic accuracy ratio.

```
Input:  localStorage session history (already stored by ProgressView)
Output: Map<topic_string, { correct: int, total: int, accuracy: float }>
```

**Key detail:** "Topic" here means the `topic` field from the template (e.g., "Solve linear equations", "Area of triangles and parallelograms"). Not strand, not template_id — the human-readable topic string. This is what's already stored in session results.

**Where:** New utility function in `frontend/src/utils/topicAccuracy.js`. Pure function, no side effects. Reads from the same localStorage structure ProgressView already uses.

**Edge case:** If a student has zero history, return an empty map. The selector (A2) must handle this gracefully.

---

### A2 — Weighted template selection algorithm (backend)

**What:** Modify the question selection logic in `question_service.py` to accept an optional `weak_topics` list from the frontend. When provided, the selector biases toward templates whose `topic` field matches weak topics.

**Algorithm — keep it simple:**

```
1. Collect all eligible templates for (year, strand, difficulty)
2. If weak_topics is empty or not provided → current behaviour (uniform random)
3. If weak_topics is provided:
   a. Partition templates into two pools:
      - WEAK pool: templates whose topic is in weak_topics
      - NORMAL pool: everything else
   b. Target ratio: 60% weak, 40% normal (of total question count)
   c. Draw from WEAK pool first (with replacement via param variation)
   d. Fill remainder from NORMAL pool
   e. If WEAK pool has fewer templates than needed, fill extra from NORMAL
   f. Shuffle final question list so weak topics aren't clustered at the start
```

**Why 60/40 not 100/0:** A session of *only* weak topics is demoralising. Students need some questions they can get right to maintain momentum.

**No AI involvement.** This is pure Python logic. The AI param generation call receives the selected template list as before — it doesn't know or care about the weighting.

**Backend change:** `POST /api/session/start` accepts an optional `weak_topics: list[str]` in the request body. Ignored if empty or missing. No breaking change to existing clients.

---

### A3 — Frontend sends weak topics on session start

**What:** Before calling `POST /api/session/start`, the frontend calls `getTopicAccuracy()` from A1, filters to topics below a threshold, and sends them as `weak_topics`.

**Threshold logic:**
```javascript
function getWeakTopics(year, strand) {
  const accuracy = getTopicAccuracy()  // from A1
  const validTopics = Object.entries(accuracy)
    .filter(([topic, stats]) => {
      return stats.total >= 3            // minimum 3 attempts to be meaningful
        && stats.accuracy < 0.6          // below 60% = weak
    })
    .map(([topic]) => topic)
  return validTopics  // may be empty — that's fine
}
```

**No UI for this.** The student never sees the weak_topics list. They pick year/strand/difficulty as before. The system silently serves better questions.

**Files changed:**
- `frontend/src/utils/topicAccuracy.js` — **NEW**
- `frontend/src/hooks/useSession.js` — add `weak_topics` to session start payload
- `backend/question_service.py` — weighted selection logic
- `backend/routes/session.py` — accept `weak_topics` param

---

## ENHANCEMENT B: Redo Mistakes

**Goal:** One button on results screen starts a mini-session with only the questions the student got wrong. No AI call, no daily limit hit, no setup screen.

### B1 — "Redo mistakes" button on ResultsScreen

**What:** Add a single button to `ResultsScreen.jsx` that appears only when `incorrect_count >= 1`. Label: **"Redo mistakes"**. Placed below the score summary, above the AI analysis section.

**Disabled state:** If all questions were correct, don't show the button at all — not greyed out, just absent.

---

### B2 — Redo session generation (frontend only)

**What:** When "Redo mistakes" is clicked, construct a new mini-session entirely on the frontend using the question objects already in memory.

**Logic:**
```
1. Filter current session's questions to only those answered incorrectly
2. For each question:
   a. Keep the same question_text, correct_answer, and options
   b. Reshuffle the options array (Fisher-Yates)
   c. Recalculate correct_index based on new option positions
3. Create a new session object with these questions
4. Navigate to DrillSession with this object — skip SessionSetup entirely
```

**Critical constraints:**
- **No backend call.** No `POST /api/session/start`. The questions already exist.
- **No AI call.** Params are reused, not regenerated.
- **No daily limit decrement.** This is a redo, not a new session. `canStartSession()` is not checked. Do not increment `daily_usage`.
- **Timer still runs.** Timed session behaviour applies normally to the redo.
- **Results screen after redo:** Show results as normal. The code-based summary runs on the redo results. AI analysis is **not** triggered for redo sessions (it would be redundant — same topics, same difficulty).

**State flag:** Add `isRedo: boolean` to the session state. Used to:
- Skip daily limit check
- Skip AI analysis call on submit
- Show "Redo session" label in results header instead of "Session results"
- **Not** write to localStorage session history (redo results don't pollute accuracy tracking — they would artificially inflate topic attempt counts)

**Files changed:**
- `frontend/src/components/ResultsScreen.jsx` — add button
- `frontend/src/hooks/useSession.js` — redo session construction, `isRedo` flag
- `frontend/src/components/DrillSession.jsx` — respect `isRedo` for limit/analysis skipping

---

## ENHANCEMENT C: Static Hints on Wrong Answers

**Goal:** After submission, each incorrectly answered question shows a one-line worked hint — the key step or insight, not a full solution. Comes from template data, not AI.

### C1 — Add `hint` field to question templates

**What:** Add a `hint` string to each template in `question_templates.json`. This is a static, human-written sentence describing the first step or key concept.

**Format rules:**
- One sentence only. Maximum 120 characters.
- Must be parameter-agnostic — the hint applies to ANY instance of the template, not to specific numbers.
- Starts with a verb (imperative mood): "Multiply base × height, then divide by 2." not "The formula is ½bh."
- No VC codes. No jargon a Year 7 student wouldn't know.

**Examples by template:**

| Template | Hint |
|---|---|
| T-7M-01 (area triangle/parallelogram) | "For triangles, multiply base × height then halve. For parallelograms, just multiply." |
| T-7A-02 (solve linear equation) | "Get the variable alone by undoing operations in reverse order." |
| T-8M-03 (circle area/circumference) | "Area uses πr². Circumference uses 2πr. Don't mix them up." |
| T-9A-03 (expand binomials) | "Multiply each term in the first bracket by each term in the second." |
| T-7N-07 (percentage of amount) | "Convert the percentage to a decimal, then multiply by the amount." |

**Curated bank templates:** The hint goes on the template, not on each bank entry. Every question from `unit_conversion_bank` shares one hint: "Move the decimal point right to go to smaller units, left to go to larger units."

**Scope:** All ~68 templates need a hint. This is a content task, not a coding task. Draft all hints in a single pass here before handing to Claude Code.

---

### C2 — Backend includes hint in results response

**What:** When `GET /api/session/{id}/result` returns scored responses, include the `hint` field for each question. The hint is already in the template data — the backend just needs to pass it through.

**Response shape change (additive, not breaking):**
```json
{
  "question_id": "T-7M-01_abc123",
  "question_text": "A triangle has base 8 cm...",
  "selected_index": 2,
  "correct_index": 0,
  "is_correct": false,
  "hint": "For triangles, multiply base × height then halve. For parallelograms, just multiply."
}
```

**Only include `hint` when `is_correct` is false.** Correct answers don't need hints — saves payload size and avoids clutter.

**Files changed:**
- `question_templates.json` — add `hint` to every template (content task, C1)
- `backend/question_service.py` — carry `hint` through the question pipeline
- `backend/routes/session.py` — include `hint` in result response for wrong answers

---

### C3 — Frontend displays hint on wrong answers

**What:** On `ResultsScreen.jsx`, for each incorrectly answered question, show the hint below the correct answer in a muted style.

**Display:**
```
Q3  ✗  Expand (2x+3)(x−4)
       Your answer: 2x² − 8x + 3     Correct: 2x² − 5x − 12
       💡 Multiply each term in the first bracket by each term in the second.
```

**Styling:** Muted text colour, slightly smaller font, indented under the correct answer line. The lightbulb emoji is a visual anchor — no other decoration. No expand/collapse — always visible for wrong answers.

**Files changed:**
- `frontend/src/components/ResultsScreen.jsx` — render hint conditionally

---

## ENHANCEMENT D: Mixed Difficulty Mode

**Goal:** A "Mixed" difficulty option that serves a spread of foundation/standard/advanced questions in one session. Mimics a real test where questions escalate.

### D1 — Define the difficulty distribution

**What:** Establish fixed ratios for mixed difficulty. These ratios are hardcoded — not configurable by the student.

```python
MIXED_DIFFICULTY_RATIOS = {
    "foundation": 0.3,   # 30%
    "standard":   0.5,   # 50%
    "advanced":   0.2,   # 20%
}
```

**For a 10-question session:** 3 foundation, 5 standard, 2 advanced.
**Rounding rule:** Round down for foundation and advanced, fill remainder with standard. For a 5-question session: 1 foundation, 3 standard, 1 advanced.

**This is code, not AI.** The backend decides the split. The AI param generation call happens per-difficulty-batch (see D3).

---

### D2 — Add "Mixed" to difficulty options in SessionSetup

**What:** Add a fourth difficulty option to `SessionSetup.jsx`.

**Current options:** Foundation | Standard | Advanced
**New options:** Foundation | Standard | Advanced | Mixed

**"Mixed" description text** (shown below the option when selected):
"A mix of easier and harder questions — like a real test."

**No other UI changes.** The strand and year selectors stay the same.

**Files changed:**
- `frontend/src/components/SessionSetup.jsx` — add Mixed option
- `frontend/src/hooks/useSession.js` — pass `difficulty: "mixed"` to backend

---

### D3 — Backend handles mixed difficulty sessions

**What:** When `difficulty: "mixed"` is received in `POST /api/session/start`, the backend generates questions at three difficulty levels according to D1 ratios.

**Implementation — three separate template selections, one merged session:**

```python
def generate_mixed_session(year, strand, question_count, weak_topics=None):
    ratios = MIXED_DIFFICULTY_RATIOS
    counts = distribute_counts(question_count, ratios)
    # counts = {"foundation": 3, "standard": 5, "advanced": 2}

    all_questions = []
    for difficulty, count in counts.items():
        if count == 0:
            continue
        # Reuse existing single-difficulty generation pipeline
        questions = generate_questions(
            year=year,
            strand=strand,
            difficulty=difficulty,
            count=count,
            weak_topics=weak_topics   # A2 weighting applies per-difficulty batch
        )
        # Tag each question with its difficulty for display purposes
        for q in questions:
            q["difficulty_tag"] = difficulty
        all_questions.extend(questions)

    # Shuffle to avoid predictable ordering
    # BUT: group by difficulty bands with slight randomisation
    # Foundation first, then standard, then advanced — within each band, shuffled
    # This mimics real test escalation without being rigidly ordered
    ordered = []
    for diff in ["foundation", "standard", "advanced"]:
        batch = [q for q in all_questions if q["difficulty_tag"] == diff]
        random.shuffle(batch)
        ordered.extend(batch)

    return ordered
```

**AI param generation:** Called once per difficulty batch, not once per question. A 10-question mixed session = 3 AI calls (one per difficulty level). This keeps AI calls bounded. If any single batch fails, the fallback random param generator handles that batch — the other batches are independent.

**Key design decision — ordering:** Questions are served in difficulty order (foundation → standard → advanced), shuffled within each band. NOT fully randomised across all difficulties. Rationale: students should warm up on easier questions first. A fully random order might front-load advanced questions and create a bad first impression.

---

### D4 — Display difficulty tag on DrillQuestion (optional, low priority)

**What:** During a mixed session, show a small difficulty badge on each question. Not shown in single-difficulty sessions (it would be redundant).

**Display:** A pill-shaped label in the top-right corner of the question card:
- Foundation → green pill, "Foundation"
- Standard → blue pill, "Standard"  
- Advanced → amber pill, "Advanced"

**Why optional:** The value is debatable. Showing "Advanced" on a question might psych out a struggling student. Showing "Foundation" might feel patronising. If you choose to skip this item, the mixed session works perfectly without it — the student just doesn't know which difficulty each question came from.

**If implemented:** Only show during the drill, not on the results screen. Results already show correct/incorrect — adding difficulty labels to results adds clutter without actionable insight.

**Files changed:**
- `backend/routes/session.py` — include `difficulty_tag` in question response (only for mixed sessions)
- `frontend/src/components/DrillQuestion.jsx` — render badge conditionally

---

### D5 — Results screen handles mixed sessions

**What:** On `ResultsScreen.jsx`, the score summary for mixed sessions shows a per-difficulty breakdown.

**Display (mixed sessions only):**
```
Score:  7 / 10  (70%)

  Foundation:   3/3  (100%)
  Standard:     3/5  (60%)
  Advanced:     1/2  (50%)
```

**For non-mixed sessions:** Continue showing the single score line as today. The per-difficulty breakdown only appears when `session.difficulty === "mixed"`.

**Code-based summary integration:** The summary function receives the `difficulty_tag` per question and can factor it into its analysis. A student who aces foundation but fails advanced gets different feedback from one who fails across the board.

**Files changed:**
- `frontend/src/components/ResultsScreen.jsx` — per-difficulty breakdown
- Code-based summary function — accept and use `difficulty_tag`

---

### D6 — localStorage records mixed session data

**What:** When a mixed session is saved to localStorage history, store the per-difficulty breakdown alongside the overall score.

**Existing localStorage record shape (additive change):**
```json
{
  "session_id": "...",
  "year": 8,
  "strand": "Algebra",
  "difficulty": "mixed",
  "score": 7,
  "total": 10,
  "difficulty_breakdown": {
    "foundation": { "correct": 3, "total": 3 },
    "standard": { "correct": 3, "total": 5 },
    "advanced": { "correct": 1, "total": 2 }
  },
  "timestamp": "..."
}
```

**For non-mixed sessions:** `difficulty_breakdown` is omitted. `difficulty` remains "foundation", "standard", or "advanced" as today.

**ProgressView impact:** The per-strand accuracy chart already aggregates across sessions. Mixed sessions contribute to the same strand totals — no chart changes needed. The `difficulty_breakdown` is stored for future use (e.g., if ProgressView later shows difficulty-level trends) but is not displayed in Phase 1.

**Files changed:**
- `frontend/src/hooks/useProgress.js` — store `difficulty_breakdown`

---

## Implementation Order

Recommended sequence based on dependencies:

```
B1 → B2          (Redo mistakes — standalone, no dependencies, quick win)
C1              (Write all 68 hints — content task, can run in parallel)
C2 → C3          (Hints backend + frontend — depends on C1 content)
A1 → A2 → A3    (Weighted selection — independent chain)
D1 → D2 → D3    (Mixed difficulty core — the complex one)
D5 → D6          (Mixed results display + storage)
D4              (Difficulty badges — optional, do last or skip)
```

**B (Redo) is the quickest win** — entirely frontend, no backend changes, no template changes, immediately useful.

**C (Hints) requires a content session first** (C1) to draft all 68 hint strings before any code is written.

**A (Weighted selection) is invisible to the user** but high-impact for learning outcomes. Independent of B/C/D.

**D (Mixed difficulty) is the most complex** and should be last. It touches backend selection logic, AI call batching, results display, and localStorage — the widest surface area.