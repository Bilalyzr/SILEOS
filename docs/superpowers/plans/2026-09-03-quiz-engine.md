# Plan — Quiz & Assessment Engine fix wave (2026-09-03)

Binding spec: `docs/superpowers/specs/2026-09-03-quiz-engine-design.md` (read F1–F10 first).
Branch `quiz-engine-upgrade` (off `revenue-platform` @ 83f176f). Backend venv: main checkout
`backend/.venv`. Run backend tests from `backend/` with that interpreter. Frontend tests:
`npx vitest run` in `frontend/`; `npx tsc --noEmit` baseline 378 errors — zero NEW.

Conventions that bind every task: routes declared WITHOUT trailing slash; new API prefixes →
`noSlashEndpoints` in `frontend/src/api/axios.ts`; no `dangerouslySetInnerHTML`; no client-side
scoring; one transaction per request write (no `db.commit()` in loops).

Working tests file for backend: new `backend/tests/test_quiz_authoring.py` (authoring rules),
extend `backend/tests/test_assessment_integrity.py` (results/feedback policy), new
`backend/tests/test_quiz_grading_flow.py` (manual grading end-to-end through the API).

---

## Task 1 — Feedback policy: persist, read, default (spec R4, fixes F6)

**Files:** `backend/app/routers/quizzes.py`, `backend/tests/test_quiz_authoring.py` (new)

**Interfaces produced:**
- create/update read `feedbackMode` from payload; persisted into `quiz_feedback_mode`.
- `GET /courses/{course_id}/quizzes/{quiz_id}` returns top-level `feedbackMode`.
- Mapping: `"reveal_immediate"|"reveal_after_due"|"reveal_never"` stored verbatim; `None`/absent → `"reveal_immediate"`. Legacy values found in DB (`"default"`) normalize to `"reveal_immediate"` on read.

**Steps:**
- [ ] Test first (`test_quiz_authoring.py`):

```python
def test_create_quiz_persists_feedback_mode(instructor_client, seeded_course):
    r = instructor_client.post("/api/v1/courses/1/quizzes", json={
        "title": "T", "feedbackMode": "reveal_after_due",
        "questions": [{"type": "true_false", "question": "2+2=4",
                       "correctAnswer": "true", "points": 1}]})
    assert r.status_code in (200, 201)
    q = instructor_client.get("/api/v1/courses/1/quizzes/%d" % r.json()["id"]).json()
    assert q["feedbackMode"] == "reveal_after_due"

def test_feedback_mode_defaults_and_legacy():
    assert normalize_feedback_mode(None) == "reveal_immediate"
    assert normalize_feedback_mode("default") == "reveal_immediate"
    assert normalize_feedback_mode("reveal_never") == "reveal_never"
```

- [ ] Implement helper + wire:

```python
FEEDBACK_MODES = ("reveal_immediate", "reveal_after_due", "reveal_never")

def normalize_feedback_mode(value) -> str:
    return value if value in FEEDBACK_MODES else "reveal_immediate"
```

In `create_quiz` / `update_quiz`: `quiz.quiz_feedback_mode = normalize_feedback_mode(quiz_data.get("feedbackMode"))`.
In `get_quiz` response: `"feedbackMode": normalize_feedback_mode(quiz.quiz_feedback_mode)`.
- [ ] Full `test_assessment_integrity.py` + new file green; commit `feat(quiz): persist and expose feedback policy`.

## Task 2 — Server-side question validation (spec R7, fixes F9)

**Files:** `backend/app/routers/quizzes.py`, `backend/tests/test_quiz_authoring.py`

**Interfaces produced:** `_validate_questions(questions: list[dict]) -> None` — raises `HTTPException(422, {"code": "...", "message": ...})`. Called by `create_quiz` and `update_quiz` BEFORE any write. `add_question_to_quiz` validates the single question the same way.

**Steps:**
- [ ] Tests first — one per rule: bad type; MCQ with <2 non-empty options; MCQ `correctAnswer` out of range (`correctAnswer: 9` with 4 options → 422, the silent-unscorable case); MCQ non-integer `correctAnswer` ("1.9" → 422); true_false `correctAnswer: "maybe"` → 422; empty fill_in_blank → 422; essay with 0 options → OK; points=0 → 422; points=1001 → 422.
- [ ] Implement exactly per spec §R7 (multi_select validation lands with Task 4 — write the validator branch now, tests in Task 4).
- [ ] `add_question_to_quiz` also replaces its bare `except: pass` (`quizzes.py:227`) with explicit `json.JSONDecodeError` handling that 422s on malformed `question_options`.
- [ ] Commit `feat(quiz): server-side question validation (422 codes)`.

## Task 3 — Transactional writes + question identity preservation (spec R5/R6, fixes F7)

**Files:** `backend/app/routers/quizzes.py`, `backend/tests/test_quiz_authoring.py`

**Interfaces changed:** `create_quiz` / `update_quiz` perform zero commits until the final single `db.commit()` (rollback on exception). `update_quiz` updates questions **in place** by `question_order` position: existing question rows are patched (title/type/marks/explanation), extra incoming questions insert with new ids, questions whose order index no longer exists in the payload are deleted — deletion allowed only when the quiz has zero attempts, else HTTP 409 `{"code": "question_has_attempts"}` listing the removable-vs-blocked question ids.

**Steps:**
- [ ] Test first:

```python
def test_update_preserves_question_ids(instructor_client, seeded_quiz):
    before = [q["id"] for q in seeded_quiz["questions"]]
    payload = _quiz_payload(seeded_quiz)          # same questions, edited title of Q1
    payload["questions"][0]["question"] = "edited"
    r = instructor_client.put(f"/api/v1/courses/1/quizzes/{seeded_quiz['id']}", json=payload)
    after = [q["id"] for q in
             instructor_client.get(f"/api/v1/courses/1/quizzes/{seeded_quiz['id']}").json()["questions"]]
    assert r.status_code == 200 and after[0] == before[0]

def test_update_cannot_drop_question_with_attempts(instructor_client, quiz_with_attempt):
    payload = _quiz_payload(quiz_with_attempt)[:-1]           # drop last question
    r = instructor_client.put(..., json=payload)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "question_has_attempts"
```

- [ ] Rebuild `create_quiz`/`update_quiz` write paths: collect ORM objects, single commit, `try/except: db.rollback(); raise`. Delete the per-question `db.commit()/db.refresh()` calls (`quizzes.py:133-134,463-465`).
- [ ] In-place update: iterate `existing_questions` ordered by `question_order`; for payload index `i < len(existing)`: patch fields on `existing[i]` and replace its answers (answers have no external references — deleting+recreating answers is fine); for `i >= len(existing)`: insert new.
- [ ] Mid-loop failure test: monkeypatch `QuizQuestionAnswer` to raise on the 2nd insert → assert quiz still has ALL original questions afterwards (rollback proof).
- [ ] Commit `fix(quiz): transactional create/update + stable question ids`.

## Task 4 — multi_select question type (spec §5)

**Files:** `backend/app/routers/quizzes.py`, `backend/tests/test_quiz_authoring.py`, `backend/tests/test_assessment_integrity.py`

**Interfaces:**
- Persistence: answers rows with `is_correct=True` for EACH correct option (`belongs_question_type="multi_select"`). `get_quiz` (owner view) returns `correctAnswers: [idx, ...]`.
- Scoring in `_submit_quiz_impl`: user answer is a list of indices (accept ints or numeric strings; dedupe); correct iff set equality with the correct set; else 0. Non-list payload → wrong (no crash).

**Steps:**
- [ ] Validation tests (Task 2 validator): `correctAnswers` must be list, ≥1, in-range, distinct ints.
- [ ] Scoring tests: exact match full marks; superset/subset 0; duplicates collapse (`[0,0,1]` ≡ `[0,1]`); `"0"` string index accepted; `[0,1,9]` out-of-range → wrong.
- [ ] Implement in `_submit_quiz_impl` next to the `multiple_choice` branch:

```python
elif question.question_type == "multi_select":
    picked = user_answer if isinstance(user_answer, list) else None
    picked_set = {(_mc_answer_index(a)) for a in picked} if picked else None
    correct_set = {i for i, a in enumerate(all_answers) if a.is_correct} \
        if question.question_type == "multi_select" else None
    is_correct = picked_set is not None and picked_set == correct_set
```

(all_answers already loaded in the MCQ branch — hoist the query so both branches share it).
- [ ] `get_quiz` owner branch: `question_dict["correctAnswers"] = [i for i,a in enumerate(answers) if a.is_correct]`.
- [ ] Commit `feat(quiz): multi_select type — validation, persistence, exact-set scoring`.

## Task 5 — Results endpoint: feedback policy + review payload (spec R4/R3, fixes F5 backend half)

**Files:** `backend/app/routers/quizzes.py`, `backend/tests/test_assessment_integrity.py`

**Interfaces changed:** `get_quiz_attempt_results` (quizzes.py:1452) response adds `"feedback_mode"`; per-question `correct_answer`/`explanation` omitted when policy says so:
- `reveal_immediate` → today's behavior (already gated on attempt ended / manual-graded states — keep).
- `reveal_after_due` → omit until the attempt's deadline passed (quiz with `quiz_time_limit>0`: `attempt_started_at + limit + pause`; untimed quizzes: treat as `reveal_immediate`).
- `reveal_never` → omit always; keep `is_correct`/`achieved_mark`/instructor feedback.
Multi_select review items expose `correct_answer` as the index list and `given_answer` normalized to an index list.

**Steps:**
- [ ] Tests: three modes × (before/after deadline for timed) matrix; assert key ABSENCE not just value; attempt owner still sees own `given_answer` in every mode.
- [ ] Implement filter helper `_redact_review_item(item, mode, deadline_utc, now_utc)`; call for each review item before returning.
- [ ] Commit `feat(quiz): feedback policy enforced in results payload`.

## Task 6 — Builder: feedback policy + multi_select + validation errors (fixes F6 UI half)

**Files:** `frontend/src/pages/instructor/quiz-builder.tsx`, `frontend/src/tests/quiz-builder.test.tsx` (new, vitest+RTL)

**Interfaces:** `QuizQuestion.type` union adds `'multi_select'` with `correctAnswers?: number[]`; `QuizSettings` gets `feedbackMode`; save payload includes `feedbackMode` (replaces the dead `showCorrectAnswers` toggle — remove it from the UI and state; it never worked).

**Steps:**
- [ ] Replace `showCorrectAnswers` checkbox with a select:

```tsx
<label>Answer reveal</label>
<select value={settings.feedbackMode}
        onChange={(e) => setSettings({ ...settings, feedbackMode: e.target.value })}>
  <option value="reveal_immediate">Right after submitting</option>
  <option value="reveal_after_due">After the deadline passes</option>
  <option value="reveal_never">Never (score only)</option>
</select>
```

- [ ] Add "Multiple Select" add-question button; editor renders checkbox list instead of radios when `type === 'multi_select'`, toggling indices inside `correctAnswers`.
- [ ] Client validation mirrors R7 (friendly toasts), and 422 responses surface `detail.message` in the error toast instead of the generic failure string.
- [ ] Update JSON template + import/export to include `feedbackMode`, `multi_select`, `correctAnswers`.
- [ ] Component test: toggling two checkboxes then save → PUT body has `correctAnswers: [0,2]`; changing type clears stale answer fields.
- [ ] `npx vitest run` green, tsc delta 0. Commit `feat(quiz-builder): feedback policy + multi_select + validation surfacing`.

## Task 7 — Wizard: kill the dead-end inline builder (fixes F1)

**Files:** `frontend/src/pages/instructor/create-course.tsx`, `frontend/src/tests/create-course-quiz.test.tsx` (new)

**Interfaces:** quiz lecture row in the wizard gains a "Configure quiz" button that mirrors `edit-course.tsx` `handleConfigureQuiz` (create-course.tsx must import nothing from edit-course — copy the handler, ~40 lines, adapted): POST `/courses/{id}/quizzes` with `{title, description, timeLimit: 30, passingScore: 70, maxAttempts: 0, questions: []}` then `navigate('/instructor|admin/courses/{courseId}/quiz-builder/{quizId}?sectionId=...')`.

**Steps:**
- [ ] Delete the inline Quiz Configuration block (`create-course.tsx:1286-1520`) and the `QuizQuestion`/`QuizData` interfaces (`:50-64`) and `quizData` field (`:92`) — dead code after this task.
- [ ] Lecture type select `quiz` option now renders the stub: title field + "Configure quiz →" button + summary line ("Questions are managed in the Quiz Builder").
- [ ] The stub quiz row's `type` change does NOT call the lesson PATCH endpoint (lessons have no quiz type — today's silent no-op); keep type local exactly as the edit page does.
- [ ] Test: clicking Configure with no prior quiz POSTs once (no dupes on double-click — reuse the `addingLecture` guard pattern) and navigates to `/instructor/courses/{courseId}/quiz-builder/{id}`.
- [ ] Commit `fix(create-course): replace state-only quiz builder with Quiz Builder handoff`.

## Task 8 — Shared post-submit QuizReview component (fixes F2/F5 frontend core)

**Files:** `frontend/src/components/quiz/QuizReview.tsx` (new), `frontend/src/tests/quiz-review.test.tsx` (new)

**Interfaces consumed:** items from `GET /quiz-attempts/{id}/results`: `question_id, type, prompt, given_answer, is_correct, achieved_mark, question_mark, correct_answer?, correct_answers?, explanation?, feedback?`. Props: `{ items: ReviewItem[]; feedbackMode: string; pendingReview: boolean }`.

**Renders per item:** your answer (formatted per type — MCQ index→option text is INCLUDED by the results endpoint as `given_answer_text`; if absent, render raw), ✓/✗ badge (manual-graded: "Instructor scored n/m"), correct answer (when present), explanation block (when present), instructor feedback block (when present). When policy hides answers, renders a one-line notice: "The instructor set this quiz to reveal answers {after the deadline|never}."

**Steps:**
- [ ] Component + tests (answer present/absent per mode; no `dangerouslySetInnerHTML`; essay item shows feedback when graded, "awaiting review" when pending).
- [ ] Commit `feat(quiz): shared QuizReview component driven by server results`.

## Task 9 — Full-page quiz results use QuizReview (fixes F5)

**Files:** `frontend/src/pages/quiz-taking.tsx`

**Steps:**
- [ ] After submit, fetch `/quiz-attempts/{attemptId}/results` (attempt id is already in the submit response — check `result`; if absent, the results route `/courses/{courseId}/quizzes/{quizId}/results` legacy alias exists at `quizzes.py:1846`) and render `<QuizReview items={...} feedbackMode={result.feedback_mode} pendingReview={result.pendingReview} />` under the score card.
- [ ] Manual-question notice already exists (`:415`) — keep; review section sits below it.
- [ ] Test: results view renders review items with explanation text; `reveal_never` shows the notice and no answers.
- [ ] Commit `feat(quiz-taking): per-question review after submit`.

## Task 10 — Inline lesson renderer: server truth + all types (fixes F2/F3)

**Files:** `frontend/src/pages/lesson-redesigned.tsx`

**Steps:**
- [ ] Delete client-side `isCorrect` computation (`:334-342`) and the owner-only review block (`:492-513`); after submit, fetch the SAME attempt results payload as Task 9 and render `<QuizReview>`.
- [ ] Pre-submit inputs: add `short_answer` text input, `essay`/`open_ended` textarea, `multi_select` checkbox group to the inline renderer.
- [ ] Submit gating: `Object.keys(answers).length !== quiz.questions.length` (`:531`) — manual questions may be left blank per instructor config? NO — keep required, but blank essay is allowed to submit only if the quiz's server contract allows; simplest binding rule: essay/open_ended may submit empty (server accepts empty manual answers), so count only non-manual questions in the gate:
  `const required = quiz.questions.filter(q => !['essay','open_ended'].includes(q.type))`.
- [ ] Tests: student payload (no `correctAnswer` in fixture) still shows ✓/✗ correctly post-submit from mocked results; essay quiz submittable.
- [ ] Commit `fix(lesson-quiz): server-driven review + missing question-type inputs`.

## Task 11 — Close the grading loop IN THE EXISTING queue (fixes corrected F4; audit Part 2)

**RE-SCOPED:** a functional grading queue already exists —
`frontend/src/pages/instructor/grading-queue.tsx` (323 lines, routed App.tsx:692, linked from
courses/gradebook pages) driving `GET /courses/{id}/grading-queue` (gradebook.py:127),
`POST /quiz-attempts/{attempt_id}/answers/{answer_id}/grade` (quizzes.py:1615), and
`POST /quiz-attempts/{attempt_id}/finalize` (quizzes.py:1694). Do NOT build a new page.

**Files:** `frontend/src/pages/instructor/grading-queue.tsx`, `backend/app/routers/quizzes.py` (finalize handler), `backend/tests/test_quiz_grading_flow.py` (new), `frontend/src/tests/grading-queue.test.tsx` (new)

**Steps:**
- [ ] Feedback field: the grade endpoint already accepts `feedback` (quizzes.py:1619 read-set) but the page sends `{achieved_mark}` only (grading-queue.tsx:98). Add a feedback textarea per manual answer, include it in the grade payload, show saved feedback on reload (grading-queue merged payload must expose `feedback` — extend gradebook.py:127 response if absent).
- [ ] Backend e2e test first (`test_quiz_grading_flow.py`): essay submit → appears in merged queue with question text + given answer → grade with feedback + mark → finalize → results payload shows feedback + final score + status `attempt_ended` → resubmit 409.
- [ ] Student notification on finalize: best-effort `award()`-style notification AFTER the finalize commit (copy the h5p.py hook pattern: own commit first, try/except around notify, unique event key). Test: finalize creates exactly one notification row; double-finalize 409s without duplicating.
- [ ] Student surface: quiz-taking + lesson QuizRenderer "awaiting review" states gain a "Refresh result" action that re-fetches the attempt results (and auto-refreshes once when navigate-back occurs) so finalized scores actually appear.
- [ ] Component test: feedback textarea persists, mark validation (non-numeric rejected, > question_mark rejected client-side to match server).
- [ ] Commit `feat(quiz): instructor feedback + finalize notifications in existing grading queue`.

---

## Task 12 — Seed, docs, full suites, live QA

**Files:** `backend/seed_quiz_demo.py` (new), `CLAUDE.md`, `docs/PLATFORM_SCHEMA.md` (regenerate only if columns changed — they don't), ledger.

**Steps:**
- [ ] Seed script: rebuild demo quiz 1 with every type incl. multi_select + non-empty explanations + `reveal_immediate`, and a second quiz `reveal_after_due` with a time limit; enroll arjun; pre-create one `pending_review` essay attempt from arjun so the grading queue demo isn't empty.
- [ ] `alembic` unchanged this sub-project (no new columns — `quiz_feedback_mode` exists). Verify: fresh `create_all` DB and migrated `visual_qa.db` both behave.
- [ ] FULL backend suite (baseline 944 passed / 4 skipped — zero regressions), `npx vitest run`, tsc delta 0.
- [ ] Live QA both flows (§2 step 9 of the working method): priya authors MCQ+multi+essay quiz via wizard→builder; arjun takes it from the lesson AND the full page, submits, sees review; priya grades the essay in the queue, finalizes; arjun sees final score + feedback. One failure path: resubmit after finalize → 409.
- [ ] `CLAUDE.md` entry (quiz engine section: surfaces, feedback modes, grading queue), ledger copy to `docs/superpowers/handoff/quiz-engine-ledger.md`, commit, merge to `revenue-platform`, both suites on merged result, push, restart preview processes.

---

## Task ordering & review gates

- Order 1→12. Tasks 1–5 are backend-contiguous (one reviewer pass may cover 2–5). Task 7 is the owner's original complaint — implement early if re-prioritized, it depends only on Task 2's validator for its 422 toast test.
- Money-adjacent: none. Authz surfaces: grading endpoints (already instructor-gated server-side) — reviewer must still verify the new PAGE never offers actions to non-owners (defense in depth).
- Adversarial review after Tasks 5, 7, 10, 11 minimum (upload/input-adjacent: none; untrusted input: question payloads, essay text, feedback text — XSS/length/unicode probes mandatory; feedback text is stored and shown to students → probe `<script>`, `\u0000`, 100KB strings).
- Deferred minors ledger: partial credit for multi_select; matching/numeric/cloze types; negative marking UI; per-take random-N; rich-text prompts; `quiz_feedback_mode` legacy-value backfill migration (read-time normalization only for now).
