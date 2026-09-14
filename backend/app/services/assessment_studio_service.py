"""Assessment coverage, reviewed publication, and immutable practice content.
Published items use negative AdaptiveSession question IDs; positive IDs remain
QuizQuestion IDs. Keys are only returned to course editors or after submission.
"""
from datetime import datetime, timezone
import hashlib
import json
from sqlalchemy import or_
from app.models.assessment_studio import StudioQuestion
from app.models.course import Lesson
from app.models.mastery import ConceptLink, CourseOutcome
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
from app.models.sileos_pack import BankQuestion, QuestionBank
from app.services.mastery_service import concepts_for, normalize_concept

TYPES = ("multiple_choice", "multiple_select", "true_false", "fill_in_blanks", "short_answer")


def now():
    return datetime.now(timezone.utc)


def prompt_key(title):
    return " ".join(title.lower().split())


def validate(content):
    title = content.get("title", "").strip()
    explanation = content.get("explanation", "").strip()
    kind = content.get("type")
    options = [s.strip() for s in content.get("options", [])]
    answer = content.get("answer")
    if not 3 <= len(title) <= 3000 or not 3 <= len(explanation) <= 5000:
        raise ValueError("A question and explanation of at least three characters are required.")
    if kind not in TYPES or content.get("difficulty") not in ("easy", "medium", "hard"):
        raise ValueError("Choose a supported question type and difficulty.")
    if kind in ("multiple_choice", "multiple_select"):
        if not 2 <= len(options) <= 8 or any(not o or len(o) > 1000 for o in options) or len({o.lower() for o in options}) != len(options):
            raise ValueError("Provide two to eight distinct, non-empty options.")
        indices = answer if isinstance(answer, list) else [answer]
        if not indices or any(type(i) is not int or i < 0 or i >= len(options) for i in indices):
            raise ValueError("Select valid correct options.")
        if len(set(indices)) != len(indices) or (kind == "multiple_choice" and len(indices) != 1):
            raise ValueError("Select exactly one answer for a single-choice question.")
        answer = indices if kind == "multiple_select" else indices[0]
    elif kind == "true_false":
        if str(answer).lower() not in ("true", "false"):
            raise ValueError("The answer must be true or false.")
        options, answer = [], str(answer).lower()
    else:
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 1000:
            raise ValueError("Provide the accepted text answer.")
        options, answer = [], answer.strip()
    return {"title": title, "type": kind, "options": options, "answer": answer,
            "explanation": explanation, "difficulty": content["difficulty"]}


def bank_content(bq):
    return {"title": bq.question_title, "type": bq.question_type, "options": bq.options or [],
            "answer": bq.correct_answer, "explanation": bq.answer_explanation or "", "difficulty": bq.difficulty or "medium"}


def question_dict(db, row):
    bq = db.query(BankQuestion).filter_by(id=row.bank_question_id).one()
    content = bank_content(bq)
    snap = row.published_snapshot
    if snap:
        answer = snap["expected"][0]
        if snap["type"] in ("multiple_choice", "multiple_select"):
            indices = [i for i, o in enumerate(snap["options"]) if o in snap["expected"]]
            answer = indices if snap["type"] == "multiple_select" else indices[0]
        content = {"title": snap["title"], "type": snap["type"], "options": snap["options"] if snap["type"] != "true_false" else [],
                   "answer": answer, "explanation": snap["explanation"], "difficulty": snap["difficulty"]}
    return {"id": row.id, "bank_question_id": row.bank_question_id, "course_id": row.course_id,
            "concept": row.concept, "purpose": row.purpose, "status": row.status,
            "version": row.version, "history": row.history, **content}


def audit(row, user_id, action, note="", **metadata):
    row.history = list(row.history or []) + [{"action": action, "note": note, "user_id": user_id, "at": now().isoformat(), **metadata}]


def content_signature(db, row):
    content = bank_content(db.query(BankQuestion).filter_by(id=row.bank_question_id).one())
    return hashlib.sha256(json.dumps([content, row.concept, row.purpose], sort_keys=True).encode()).hexdigest()


def save_draft(db, course_id, user_id, content, concept, purpose, row=None, allow_incomplete=False):
    if allow_incomplete:
        if content.get("type") not in TYPES:
            raise ValueError("Only supported auto-gradable question types can be copied into the studio.")
        cleaned = {**content, "options": [str(o) for o in content.get("options", [])] if isinstance(content.get("options"), list) else [],
                   "answer": content.get("answer") if content.get("answer") is not None else ""}
    else:
        cleaned = validate(content)
    if row is None:
        # Bank content remains reusable. Sharing into a course is explicit through
        # this studio row; it never grants access to the creator's other banks.
        title = f"Course {course_id} · Assessment Studio"
        bank = db.query(QuestionBank).filter_by(instructor_id=user_id, title=title).first()
        if not bank:
            bank = QuestionBank(instructor_id=user_id, title=title)
            db.add(bank); db.flush()
        bq = BankQuestion(bank_id=bank.id, question_title=cleaned["title"], question_type=cleaned["type"])
        db.add(bq); db.flush()
        row = StudioQuestion(course_id=course_id, bank_question_id=bq.id, created_by=user_id, history=[])
        db.add(row)
    else:
        bq = db.query(BankQuestion).filter_by(id=row.bank_question_id).one()
        row.version += 1
    bq.question_title, bq.question_type = cleaned["title"], cleaned["type"]
    bq.options, bq.correct_answer = cleaned["options"], cleaned["answer"]
    bq.answer_explanation, bq.difficulty = cleaned["explanation"], cleaned["difficulty"]
    bq.question_mark, bq.tags = 1, ["studio-draft"]
    row.concept, row.purpose, row.status = normalize_concept(concept), purpose, "draft"
    audit(row, user_id, "saved_draft")
    db.flush()
    return row


def publish_snapshot(db, row):
    content = validate(bank_content(db.query(BankQuestion).filter_by(id=row.bank_question_id).one()))
    if content["type"] in ("multiple_choice", "multiple_select"):
        indices = content["answer"] if isinstance(content["answer"], list) else [content["answer"]]
        expected = [content["options"][i] for i in indices]
    elif content["type"] == "true_false":
        content["options"] = ["True", "False"]
        expected = [content["answer"]]
    else:
        expected = [content["answer"]]
    return {"question_id": -row.id, "title": content["title"], "type": content["type"],
            "options": content["options"], "concepts": [row.concept], "difficulty": content["difficulty"],
            "expected": expected, "explanation": content["explanation"], "purpose": row.purpose, "marks": 1}


def catalog(db, course_id):
    """Only content usable by the exact planner grading path counts as coverage."""
    quizzes = db.query(Quiz).filter(Quiz.post_parent == course_id, Quiz.post_status.in_(["publish", "published"]),
        or_(Quiz.quiz_feedback_mode.is_(None), Quiz.quiz_feedback_mode != "reveal_never"),
        or_(Quiz.quiz_available_from.is_(None), Quiz.quiz_available_from <= now()),
        or_(Quiz.quiz_available_until.is_(None), Quiz.quiz_available_until >= now())).all()
    quiz_links = {q.id: concepts_for(db, "quiz", q.id) for q in quizzes}
    questions = db.query(QuizQuestion).filter(QuizQuestion.quiz_id.in_(list(quiz_links)),
        QuizQuestion.question_type.in_(TYPES), or_(QuizQuestion.is_retired.is_(False), QuizQuestion.is_retired.is_(None))).all()
    out = []
    for q in questions:
        concepts = concepts_for(db, "question", q.question_id) or quiz_links[q.quiz_id]
        answers = db.query(QuizQuestionAnswer).filter_by(belongs_question_id=q.question_id).order_by(QuizQuestionAnswer.answer_order).all()
        expected = [a.answer_title for a in answers if a.is_correct and a.answer_title and a.answer_title.strip()]
        options = [a.answer_title for a in answers] if q.question_type in ("multiple_choice", "multiple_select", "true_false") else []
        if not expected or not concepts:
            continue
        if options and (len(options) < 2 or any(not o or not o.strip() for o in options) or len({o.strip().lower() for o in options}) != len(options)):
            continue
        if q.question_type in ("multiple_choice", "true_false") and len(expected) != 1:
            continue
        out.append({"question_id": q.question_id, "title": q.question_title, "type": q.question_type,
                    "options": options, "expected": expected, "concepts": concepts,
                    "difficulty": (q.question_settings or {}).get("difficulty", "medium"),
                    "explanation": q.answer_explanation or "", "purpose": "practice", "marks": 1})
    for row in db.query(StudioQuestion).filter_by(course_id=course_id, status="published"):
        if row.published_snapshot:
            out.append(row.published_snapshot)
    return out


def studio_snapshot(db, qid, course_id):
    row = db.query(StudioQuestion).filter_by(id=-qid, course_id=course_id).first()
    return row.published_snapshot if row else None


def coverage(db, course_id):
    from app.models.learning_planner import LearningGoal, LearningIntervention, LearningPlanTask
    from app.models.enrollment import Enrollment
    from app.services.learning_planner_service import ACTIVE_ENROLLMENTS
    items = catalog(db, course_id)
    lessons = db.query(Lesson).filter_by(post_parent=course_id).all()
    lesson_links = {l.id: concepts_for(db, "lesson", l.id) for l in lessons}
    goals = db.query(LearningGoal).join(Enrollment, (Enrollment.user_id == LearningGoal.user_id) & (Enrollment.course_id == LearningGoal.course_id)).filter(
        LearningGoal.course_id == course_id, Enrollment.enrollment_status.in_(ACTIVE_ENROLLMENTS)).all()
    interventions = db.query(LearningIntervention).filter(LearningIntervention.goal_id.in_([g.id for g in goals])).all()
    drafts = db.query(StudioQuestion).filter_by(course_id=course_id).order_by(StudioQuestion.id.desc()).all()
    outcome = db.query(CourseOutcome).filter_by(course_id=course_id).first()
    concepts = set(outcome.target_concepts or []) if outcome else set()
    concepts.update(c for cs in lesson_links.values() for c in cs)
    concepts.update(c for item in items for c in item["concepts"])
    concepts.update(i.concept for i in interventions)
    concepts.update(q.concept for q in drafts)
    rows = []
    for c in sorted(concepts):
        qs = [q for q in items if c in q["concepts"]]
        # Exact copies do not inflate distinct-question coverage.
        practice = {prompt_key(q["title"]) for q in qs if q["purpose"] == "practice"}
        reserve = {prompt_key(q["title"]) for q in qs if q["purpose"] == "followup"} - practice
        taught = [l for l in lessons if l.post_status in ("publish", "published") and c in lesson_links[l.id]]
        relevant = [i for i in interventions if i.concept == c]
        completed = db.query(LearningPlanTask).filter(LearningPlanTask.intervention_id.in_([i.id for i in relevant]), LearningPlanTask.status == "done").all()
        checks = [t for t in completed if t.kind in ("practice", "followup")]
        valid_followups = [t for t in checks if t.kind == "followup" and (t.outcome or {}).get("enough_evidence")]
        gains = []
        for i in relevant:
            own_checks = sorted([t for t in checks if t.intervention_id == i.id], key=lambda t: t.id, reverse=True)
            practice_check = next((t for t in own_checks if t.kind == "practice"), None)
            delayed = next((t for t in own_checks if t.kind == "followup"), None)
            if (i.followup_score is not None and i.latest_score is not None and practice_check and delayed
                    and (practice_check.outcome or {}).get("enough_evidence") and (delayed.outcome or {}).get("enough_evidence")):
                gains.append(i.followup_score - i.latest_score)

        rows.append({"concept": c, "lessons": len(taught), "practice_questions": len(practice), "reserved_followups": len(reserve),
            "practice_ready": len(practice) >= 2, "followup_ready": len(reserve) >= 2,
            "needs_support": sum(i.status == "needs_instructor" for i in relevant),
            "outcomes": {"interventions": len(relevant), "completed_checks": len(checks),
                "graded_questions": sum((t.outcome or {}).get("questions", 0) for t in checks),
                "valid_followups": len(valid_followups),
                "followups_passed": sum((t.outcome or {}).get("score", 0) >= 75 for t in valid_followups),
                "paired_learners": len(gains), "mean_practice_to_followup_change": round(sum(gains)/len(gains), 1) if gains else None}})
    return {"course_id": course_id, "concepts": rows, "questions": [question_dict(db, q) for q in drafts],
            "lessons": [{"id": l.id, "title": l.post_title, "published": l.post_status in ("publish", "published"), "concepts": lesson_links[l.id]} for l in lessons],
            "live_questions": [{"id": q.question_id, "title": q.question_title, "concepts": concepts_for(db, "question", q.question_id)} for q in db.query(QuizQuestion).join(Quiz).filter(Quiz.post_parent == course_id).all()]}


def add_link(db, course_id, user_id, kind, ref_id, concept):
    if kind == "lesson":
        exists = db.query(Lesson.id).filter_by(id=ref_id, post_parent=course_id).first()
    else:
        exists = db.query(QuizQuestion.question_id).join(Quiz).filter(QuizQuestion.question_id == ref_id, Quiz.post_parent == course_id).first()
    if not exists:
        raise ValueError("Choose content belonging to this course.")
    if not db.query(ConceptLink.id).filter_by(kind=kind, ref_id=str(ref_id), concept=concept).first():
        db.add(ConceptLink(kind=kind, ref_id=str(ref_id), concept=concept, course_id=course_id, created_by=user_id))
    db.flush()


def build_focused(db, user_id, course_id, count, focus, phase, commit):
    from app.models.learning_signals import AdaptiveSession
    from app.models.quiz import QuizAttemptAnswer
    from app.services.mastery_service import clean_concepts
    focus = clean_concepts(focus)
    pool = [q for q in catalog(db, course_id) if set(q["concepts"]).intersection(focus)
            and (phase == "followup" or q["purpose"] == "practice")]
    seen = {qid for session in db.query(AdaptiveSession).filter_by(user_id=user_id, course_id=course_id)
            for qid in (session.question_ids or [])}
    seen.update(qid for (qid,) in db.query(QuizAttemptAnswer.question_id).join(Quiz, Quiz.id == QuizAttemptAnswer.quiz_id).filter(
        QuizAttemptAnswer.user_id == user_id, Quiz.post_parent == course_id).all())
    seen_titles = set()
    for qid in seen:
        if qid < 0:
            snapshot = studio_snapshot(db, qid, course_id)
            if snapshot:
                seen_titles.add(prompt_key(snapshot["title"]))
        else:
            q = db.query(QuizQuestion).filter_by(question_id=qid).first()
            if q:
                seen_titles.add(prompt_key(q.question_title))
    def repeated(q):
        return q["question_id"] in seen or prompt_key(q["title"]) in seen_titles
    # Unseen content always outranks repetition, even if difficulty differs.
    pool.sort(key=lambda q: (repeated(q), q["purpose"] != ("followup" if phase == "followup" else "practice"), q["question_id"]))
    chosen, titles = [], set()
    for q in pool:
        key = prompt_key(q["title"])
        if key in titles:
            continue
        chosen.append(q); titles.add(key)
        if len(chosen) >= count:
            break
    reused = sum(repeated(q) for q in chosen)
    note = (f"{reused} of {len(chosen)} questions have been shown before. This check may reflect answer familiarity." if reused else
            "These question prompts have not appeared in your previous recorded checks or quiz answers.")
    plan = {"focus_concepts": focus, "concepts": focus, "why": [note], "phase": phase,
            "new_question_count": len(chosen) - reused, "reused_question_count": reused,
            "difficulty": {str(q["question_id"]): q["difficulty"] for q in chosen}}
    session = AdaptiveSession(user_id=user_id, course_id=course_id, question_ids=[q["question_id"] for q in chosen], plan=plan)
    db.add(session)
    if commit:
        db.commit(); db.refresh(session)
    else:
        db.flush()
    return session
