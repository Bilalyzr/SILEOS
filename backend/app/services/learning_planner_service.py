"""Transparent daily planning. Behaviour prompts checks, never a mastery verdict.
All mutations are scoped to a locked goal. No LLM/key/network dependency.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import ceil
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.models.course import Lesson
from app.models.enrollment import Enrollment, LessonProgress
from app.models.learning_planner import LearningGoal, LearningIntervention, LearningPlanTask
from app.models.learning_signals import AdaptiveSession
from app.models.mastery import ConceptPrerequisite, MasteryEvidence
from app.services import learning_signals_service as signals
from app.services.mastery_service import concepts_for

ACTIVE_ENROLLMENTS = ("enrolled", "completed")
ASSESSMENT_KINDS = ("quiz", "question", "assignment", "three_d_task")
FOLLOWUP_DAYS = 3
PASS_PERCENT = 75
MIN_CHECK_QUESTIONS = 2


def utcnow():
    return datetime.now(timezone.utc)


def today_for(goal, now=None):
    return (now or utcnow()).astimezone(ZoneInfo(goal.timezone)).date()


def enrolled(db, user_id, course_id):
    return db.query(Enrollment.id).filter(Enrollment.user_id == user_id, Enrollment.course_id == course_id,
                                         Enrollment.enrollment_status.in_(ACTIVE_ENROLLMENTS)).first() is not None


def _minutes(lesson):
    value = str(lesson.lesson_video_duration or "")
    try:
        parts = [float(v) for v in value.split(":")]
        seconds = sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
        return max(5, min(180, ceil(seconds / 60)))
    except (ValueError, OverflowError):
        return 10


def _assessment(db, goal):
    # Only evidence in this course; no other instructor's learners or course data.
    rows = db.query(MasteryEvidence).filter(MasteryEvidence.user_id == goal.user_id,
        MasteryEvidence.course_id == goal.course_id, MasteryEvidence.source_kind.in_(ASSESSMENT_KINDS),
        MasteryEvidence.created_at >= utcnow() - timedelta(days=60)).order_by(MasteryEvidence.created_at.desc(), MasteryEvidence.id.desc()).all()
    from app.models.quiz import Quiz, QuizAttempt, QuizAttemptAnswer, QuizQuestion
    hidden_quizzes = {qid for (qid,) in db.query(Quiz.id).filter(Quiz.post_parent == goal.course_id, Quiz.quiz_feedback_mode == "reveal_never").all()}
    answers = db.query(QuizAttemptAnswer, QuizAttempt, QuizQuestion).join(
        QuizAttempt, QuizAttempt.attempt_id == QuizAttemptAnswer.quiz_attempt_id).join(
        QuizQuestion, QuizQuestion.question_id == QuizAttemptAnswer.question_id).filter(
        QuizAttempt.user_id == goal.user_id, QuizAttempt.course_id == goal.course_id,
        QuizAttempt.attempt_status.in_(["attempt_ended", "pending_review"]),
        QuizAttemptAnswer.created_at >= utcnow() - timedelta(days=60)).all()
    records, direct_concepts = [], set()
    for answer, attempt, question in answers:
        if attempt.quiz_id in hidden_quizzes:
            continue
        if question.question_type in ("essay", "open_ended") and attempt.attempt_status != "attempt_ended":
            continue
        if not answer.question_mark or answer.question_mark <= 0:
            continue
        concepts = concepts_for(db, "question", answer.question_id) or concepts_for(db, "quiz", attempt.quiz_id)
        for concept in concepts:
            direct_concepts.add(concept)
            records.append((concept, max(0, min(100, float(answer.achieved_mark or 0) / float(answer.question_mark) * 100)),
                            answer.created_at, f"answer:{answer.attempt_answer_id}"))
    for row in rows:
        if row.source_kind == "quiz" and row.source_ref in {str(qid) for qid in hidden_quizzes}:
            continue
        if row.source_kind == "quiz" and row.concept in direct_concepts:
            continue  # use item evidence instead of counting the same quiz aggregate again
        records.append((row.concept, row.score_pct, row.created_at, f"evidence:{row.id}"))
    def when(record):
        dt = record[2]
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    grouped = defaultdict(list)
    for record in sorted(records, key=when, reverse=True):
        if len(grouped[record[0]]) < 5:
            grouped[record[0]].append(record)
    return {c: {"score": round(sum(r[1] for r in rs) / len(rs), 1), "count": len(rs),
                "latest_at": when(rs[0]).isoformat(), "latest_key": rs[0][3]} for c, rs in grouped.items()}


def _task(db, goal, key, kind, title, reason, day, concept=None, lesson_id=None, intervention_id=None, minutes=10):
    existing = db.query(LearningPlanTask).filter_by(goal_id=goal.id, task_key=key).first()
    if existing:
        return existing
    row = LearningPlanTask(goal_id=goal.id, task_key=key, kind=kind, title=title[:255], reason=reason,
        due_date=day, not_before=day, concept=concept, lesson_id=lesson_id, intervention_id=intervention_id, minutes=minutes)
    db.add(row)
    db.flush()
    return row


def _schedule(db, goal, day):
    tasks = db.query(LearningPlanTask).filter_by(goal_id=goal.id).order_by(LearningPlanTask.id).all()
    # A review also covers the curriculum study block for that lesson. Preserve
    # both records, but charge the learner's time only once. Restore curriculum
    # work if an instructor cancels the review before it is studied.
    reviewed = {t.lesson_id for t in tasks if t.kind == "review" and t.status in ("pending", "done")}
    for task in tasks:
        if task.kind != "lesson":
            continue
        covered = (task.outcome or {}).get("covered_by_review", False)
        if task.status == "pending" and task.lesson_id in reviewed:
            task.status = "skipped"
            task.outcome = {"covered_by_review": True, "note": "Included in the review study block."}
        elif task.status == "skipped" and covered and task.lesson_id not in reviewed:
            task.status = "pending"
            task.outcome = None
    used = defaultdict(int)
    for task in tasks:
        if task.status == "done" and task.completed_at:
            dt = task.completed_at.replace(tzinfo=timezone.utc) if task.completed_at.tzinfo is None else task.completed_at
            used[dt.astimezone(ZoneInfo(goal.timezone)).date()] += task.minutes
    pending = [t for t in tasks if t.status == "pending"]
    pending.sort(key=lambda t: (0 if t.kind == "followup" and t.not_before <= day else
                                1 if t.kind == "review" else 2 if t.kind == "practice" else 3, t.id))
    for task in pending:
        date = max(day, task.not_before)
        # A long lesson gets a dedicated study block, honestly flagged in the response.
        while used[date] and used[date] + task.minutes > goal.daily_minutes:
            date += timedelta(days=1)
        task.due_date = date
        used[date] += task.minutes
    db.flush()


def refresh_goal(db: Session, goal: LearningGoal):
    if goal.status != "active" or not enrolled(db, goal.user_id, goal.course_id):
        return
    day = today_for(goal)
    lessons = db.query(Lesson).filter(Lesson.post_parent == goal.course_id,
        Lesson.post_status.in_(["publish", "published"])).order_by(Lesson.menu_order, Lesson.id).all()
    linked = {l.id: concepts_for(db, "lesson", l.id) for l in lessons}
    completed = {lid for (lid,) in db.query(LessonProgress.lesson_id).filter(
        LessonProgress.user_id == goal.user_id, LessonProgress.course_id == goal.course_id,
        LessonProgress.progress_status == "completed").all()}
    profile = signals.learner_profile(db, goal.user_id, goal.course_id)
    behaviour = {c["concept"]: c for c in profile["struggling"]}
    evidence = _assessment(db, goal)
    candidates = set(behaviour) | {c for c, e in evidence.items() if e["score"] < 60}
    for concept in sorted(candidates):
        row = db.query(LearningIntervention).filter_by(goal_id=goal.id, concept=concept).first()
        ev, behaviour_row = evidence.get(concept), behaviour.get(concept)
        reopening = False
        if row:
            last = (row.evidence or {}).get("assessment") or {}
            reviewed_at = row.updated_at
            if reviewed_at and reviewed_at.tzinfo is None:
                reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
            reopening = bool(row.status == "resolved" and ev and ev["score"] < 60
                             and ev.get("latest_key") != last.get("latest_key")
                             and reviewed_at and datetime.fromisoformat(ev["latest_at"]) > reviewed_at)
            if not reopening:
                continue  # instructor closures are intentional; only fresh evidence reopens a resolved check
        why = []
        if ev and ev["score"] < 60:
            why.append(f"Recent course assessment average is {ev['score']}% across {ev['count']} evidence records.")
        if behaviour_row:
            why.append("A check may help: " + ", ".join(behaviour_row["why"]) + ". Behaviour alone does not establish a gap.")
        if not row:
            row = LearningIntervention(goal_id=goal.id, concept=concept)
            db.add(row)
        history = list((row.evidence or {}).get("history", []))
        if reopening:
            history.append({"action": "reopened", "at": utcnow().isoformat(), "previous_followup_score": row.followup_score})
        row.status, row.reason = "suggested", " ".join(why)
        row.baseline_score = ev["score"] if ev else None
        row.latest_score = row.followup_score = None
        row.evidence = {"assessment": ev, "behaviour": behaviour_row, "history": history,
                        "basis": "assessment" if ev and ev["score"] < 60 else "diagnostic"}
        db.flush()
        cycle = db.query(LearningPlanTask).filter_by(intervention_id=row.id).count() if reopening else 0
        prerequisites = [p.requires for p in db.query(ConceptPrerequisite).filter_by(concept=concept).all()
                         if p.requires in evidence and evidence[p.requires]["score"] < 60]
        for focus in prerequisites + [concept]:
            lesson = next((l for l in lessons if focus in linked[l.id]), None)
            if lesson:
                _task(db, goal, f"review:{row.id}:{cycle}:{lesson.id}", "review", f"Review: {lesson.post_title}",
                    f"Revisit {focus}" + (f" before checking {concept}." if focus != concept else " before your check."),
                    day, concept=focus, lesson_id=lesson.id, intervention_id=row.id, minutes=_minutes(lesson))
        _task(db, goal, f"check:{row.id}:{cycle}", "practice", f"Check your understanding: {concept}", row.reason,
              day, concept=concept, intervention_id=row.id)
    # Completing a study task means studied, not mastered. Course completion also syncs here.
    available = {l.id for l in lessons}
    for task in db.query(LearningPlanTask).filter(LearningPlanTask.goal_id == goal.id, LearningPlanTask.status.in_(["pending", "skipped"])).all():
        if task.lesson_id and task.lesson_id not in available:
            task.status = "skipped"
            task.outcome = {"note": "Lesson is no longer available."}
        elif task.status == "pending" and task.kind == "lesson" and task.lesson_id in completed:
            task.status = "done"
            task.completed_at = utcnow()
            task.outcome = {"note": "Completed in the course."}
    for lesson in lessons:
        if lesson.id not in completed:
            _task(db, goal, f"lesson:{lesson.id}", "lesson", lesson.post_title,
                  "Continue the course curriculum.", day, lesson_id=lesson.id, minutes=_minutes(lesson))
    _schedule(db, goal, day)
    db.commit()


def task_dict(t, course_id):
    return {"id": t.id, "kind": t.kind, "title": t.title, "reason": t.reason, "concept": t.concept,
        "minutes": t.minutes, "due_date": t.due_date, "not_before": t.not_before, "status": t.status,
        "session_id": t.session_id, "intervention_id": t.intervention_id, "outcome": t.outcome,
        "lesson_url": f"/courses/{course_id}/lessons/lesson-{t.lesson_id}" if t.lesson_id else None}


def intervention_dict(row):
    return {"id": row.id, "concept": row.concept, "status": row.status, "reason": row.reason,
        "evidence": row.evidence, "baseline_score": row.baseline_score, "latest_score": row.latest_score,
        "followup_score": row.followup_score, "instructor_note": row.instructor_note,
        "reviewed_at": row.reviewed_at, "created_at": row.created_at, "history": (row.evidence or {}).get("history", []),
        "change": round(row.followup_score - row.baseline_score, 1) if row.followup_score is not None and row.baseline_score is not None else None}


def goal_dict(db, goal):
    day = today_for(goal)
    tasks = db.query(LearningPlanTask).filter_by(goal_id=goal.id).order_by(LearningPlanTask.due_date, LearningPlanTask.id).all()
    pending = [t for t in tasks if t.status == "pending"]
    finish = max((t.due_date for t in pending), default=day)
    warnings = []
    if finish > goal.target_date:
        warnings.append("The current workload extends beyond your target date. Increase your daily budget or move the date.")
    if any(t.minutes > goal.daily_minutes for t in pending):
        warnings.append("Some lessons exceed your daily budget and have a dedicated longer block. You can study them in smaller parts.")
    if goal.target_date < day:
        warnings.append("Your target date has passed. Update it to keep planning ahead.")
    return {"id": goal.id, "course_id": goal.course_id, "title": goal.title, "target_date": goal.target_date,
        "daily_minutes": goal.daily_minutes, "timezone": goal.timezone, "status": goal.status, "today": day,
        "estimated_finish": finish, "warnings": warnings, "remaining_minutes": sum(t.minutes for t in pending),
        "tasks": [task_dict(t, goal.course_id) for t in tasks],
        "interventions": [intervention_dict(i) for i in db.query(LearningIntervention).filter_by(goal_id=goal.id).order_by(LearningIntervention.id).all()]}


def start_check(db, goal, task):
    if task.kind not in ("practice", "followup"):
        raise ValueError("This task is a study block, not a check.")
    if task.status != "pending":
        raise ValueError("This task is already finished.")
    if today_for(goal) < task.not_before:
        raise ValueError("This retention check is not due yet.")
    if task.session_id:
        return db.query(AdaptiveSession).filter_by(id=task.session_id).one()
    session = signals.build_adaptive(db, goal.user_id, goal.course_id, count=3,
        focus_concepts=[task.concept], focus_only=True, commit=False, phase=task.kind)
    if not session.question_ids:
        db.delete(session)
        row = db.query(LearningIntervention).filter_by(id=task.intervention_id).one()
        row.status = "needs_instructor"
        task.outcome = {"note": "No auto-gradable questions are linked to this concept. An instructor needs to add or review practice."}
        db.commit()
        raise ValueError(task.outcome["note"])
    task.session_id = session.id
    db.commit()
    return session


def finish_check(db, goal, task, answers):
    if not task.session_id:
        raise ValueError("Start the check first.")
    session = db.query(AdaptiveSession).filter_by(id=task.session_id, user_id=goal.user_id, course_id=goal.course_id).one()
    if session.submitted_at is None:
        signals.grade_adaptive(db, session, answers)
    # Grading commits its own evidence; reacquire the task lock for idempotent planning.
    task = db.query(LearningPlanTask).filter_by(id=task.id).with_for_update().populate_existing().one()
    if task.status == "done":
        return task.outcome
    results = [r for r in (session.results or []) if task.concept in r["concepts"]]
    count = len(results)
    score = round(100 * sum(bool(r["correct"]) for r in results) / count, 1) if count else None
    row = db.query(LearningIntervention).filter_by(id=task.intervention_id).one()
    enough = count >= MIN_CHECK_QUESTIONS
    if task.kind == "followup":
        row.followup_score = score
    else:
        row.latest_score = score
    if not enough:
        row.status = "needs_instructor"
        note = "Too few linked questions to establish understanding. Your instructor can review the evidence."
    elif score < PASS_PERCENT:
        row.status = "needs_instructor"
        note = "More support may help. This check is in your instructor's intervention queue."
    elif task.kind == "followup":
        row.status = "resolved"
        note = "Your delayed check met the target. This is evidence of retention, not a guarantee of permanent mastery."
    else:
        row.status = "monitoring"
        note = f"You met the practice target. A retention check is scheduled in {FOLLOWUP_DAYS} days."
        day = today_for(goal) + timedelta(days=FOLLOWUP_DAYS)
        _task(db, goal, f"followup:{task.id}", "followup", f"Retention check: {task.concept}",
              "Check what you remember after a gap, without reviewing the answer key first.", day,
              concept=task.concept, intervention_id=row.id)
    task.status = "done"
    task.completed_at = utcnow()
    task.outcome = {"score": score, "questions": count, "enough_evidence": enough, "note": note,
                    "results": session.results or [], "intervention_status": row.status,
                    "new_question_count": (session.plan or {}).get("new_question_count"),
                    "reused_question_count": (session.plan or {}).get("reused_question_count"),
                    "freshness_note": " ".join((session.plan or {}).get("why", []))}
    _schedule(db, goal, today_for(goal))
    db.commit()
    return task.outcome


def review_intervention(db, goal, row, action, note, reviewer_id):
    evidence = dict(row.evidence or {})
    evidence["history"] = list(evidence.get("history", [])) + [{"action": action, "note": note, "reviewer_id": reviewer_id, "at": utcnow().isoformat()}]
    row.evidence = evidence
    row.instructor_note = note
    row.reviewed_by = reviewer_id
    row.reviewed_at = utcnow()
    if action == "dismiss":
        row.status = "dismissed"
        for task in db.query(LearningPlanTask).filter_by(intervention_id=row.id, status="pending").all():
            task.status = "skipped"
    else:
        existing = db.query(LearningPlanTask).filter(LearningPlanTask.intervention_id == row.id,
            LearningPlanTask.kind.in_(["practice", "followup"]), LearningPlanTask.status == "pending").first()
        if not existing:
            count = db.query(LearningPlanTask).filter_by(intervention_id=row.id).count()
            _task(db, goal, f"retry:{row.id}:{count}", "practice", f"Instructor check: {row.concept}", note,
                  today_for(goal), concept=row.concept, intervention_id=row.id)
        row.status = "suggested"
    _schedule(db, goal, today_for(goal))
    db.commit()


def planner_pass(db, now=None):
    # Same best-effort rule as retention. A bad goal cannot stop other reminders.
    import logging
    ids = [gid for (gid,) in db.query(LearningGoal.id).filter_by(status="active").all()]
    refreshed = 0
    for gid in ids:
        try:
            goal = db.query(LearningGoal).filter_by(id=gid).with_for_update().one()
            if enrolled(db, goal.user_id, goal.course_id):
                refresh_goal(db, goal)
                refreshed += 1
        except Exception:
            db.rollback()
            logging.getLogger(__name__).exception("Planner refresh failed for goal %s", gid)
    return refreshed



def refresh_after_assessment(db, user_id, course_id):
    """A planner failure can never roll back or fail an already committed quiz."""
    import logging
    try:
        goal = db.query(LearningGoal).filter_by(user_id=user_id, course_id=course_id, status="active").with_for_update().first()
        if goal:
            refresh_goal(db, goal)
    except Exception:
        db.rollback()
        logging.getLogger(__name__).exception("Planner update skipped after assessment")
