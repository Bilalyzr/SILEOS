"""Studio lifecycle, scope, publication integrity and fresh practice regression."""
from datetime import timedelta
import importlib.util
from pathlib import Path
import pytest
from app.core.security import create_access_token
from app.models.assessment_studio import StudioQuestion
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer, QuizAttempt
from app.models.mastery import ConceptLink, MasteryEvidence, CourseOutcome
from app.models.sileos_pack import BankQuestion, QuestionBank
from app.models.learning_planner import LearningGoal, LearningPlanTask
from app.services import assessment_studio_service as svc
from app.services import learning_signals_service as signals
from app.services import learning_planner_service as planner


@pytest.fixture
def studio_world(db, make_user, student_user):
    from app.models.user import InstructorProfile
    teacher = make_user(role="instructor", email="studio@example.com")
    db.add(InstructorProfile(user_id=teacher.id, is_approved=True))
    course = Course(post_author=teacher.id, post_title="Studio course", post_status="publish", course_price=0)
    db.add(course); db.flush()
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    db.add(CourseOutcome(course_id=course.id, target_concepts=["fractions"]))
    db.commit()
    return teacher, course


def auth(client, user):
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": str(user.id)})


def payload(title="Which fraction equals one half?", **changes):
    return {"title": title, "type": "multiple_choice", "options": ["2/4", "3/4"], "answer": 0,
            "explanation": "Divide the numerator and denominator of 2/4 by two.", "difficulty": "medium",
            "concept": "fractions", "purpose": "practice", **changes}


def draft(client, world, **changes):
    auth(client, world[0])
    r = client.post(f"/api/v1/assessment-studio/courses/{world[1].id}/questions", json=payload(**changes))
    assert r.status_code == 201, r.text
    return r.json()


def action(client, row, verb):
    r = client.post(f"/api/v1/assessment-studio/questions/{row['id']}/action", json={"version": row["version"], "action": verb, "note": "Verified the answer, explanation and concept."})
    assert r.status_code == 200, r.text
    return r.json()


def publish(client, world, **changes):
    return action(client, action(client, draft(client, world, **changes), "review"), "publish")


def test_lifecycle_requires_review_and_keeps_bank_content_reusable(client, db, studio_world):
    row = draft(client, studio_world)
    uri = f"/api/v1/assessment-studio/questions/{row['id']}/action"
    assert client.post(uri, json={"action": "publish", "version": 1, "note": "Bypass review"}).status_code == 409
    row = action(client, row, "review")
    edited = client.put(f"/api/v1/assessment-studio/questions/{row['id']}", json=payload(version=row['version'], explanation="Both parts divide by two."))
    assert edited.status_code == 200 and edited.json()["status"] == "draft"
    assert client.post(uri, json={"action": "publish", "version": row["version"], "note": "Stale review"}).status_code == 409
    row = action(client, action(client, edited.json(), "review"), "publish")
    assert db.query(Quiz).count() == db.query(QuizAttempt).count() == 0
    assert db.query(BankQuestion).count() == 1
    assert len(row["history"]) == 5
    assert client.put(f"/api/v1/assessment-studio/questions/{row['id']}", json=payload(version=row['version'])).status_code == 409


@pytest.mark.parametrize("change", [
    {"options": ["same", "SAME"]}, {"answer": True}, {"answer": 2}, {"answer": [0, 1]},
    {"explanation": "   "}, {"concept": "   "}, {"type": "short_answer", "answer": []},
    {"type": "true_false", "answer": "maybe"}, {"type": "multiple_select", "answer": [0, 0]},
])
def test_invalid_questions_never_enter_bank(client, db, studio_world, change):
    auth(client, studio_world[0])
    r = client.post(f"/api/v1/assessment-studio/courses/{studio_world[1].id}/questions", json=payload(**change))
    assert r.status_code == 422, r.text
    assert db.query(StudioQuestion).count() == db.query(BankQuestion).count() == 0


def test_students_and_other_course_editors_cannot_read_keys(client, db, studio_world, student_user, make_user):
    row = publish(client, studio_world)
    auth(client, student_user)
    assert client.get(f"/api/v1/assessment-studio/courses/{studio_world[1].id}").status_code == 403
    other = make_user(role="instructor", email="otherstudio@example.com")
    from app.models.user import InstructorProfile
    db.add(InstructorProfile(user_id=other.id, is_approved=True)); db.commit()
    auth(client, other)
    assert client.get('/api/v1/assessment-studio/courses').json()["courses"] == []
    assert client.get(f"/api/v1/assessment-studio/courses/{studio_world[1].id}").status_code == 403
    assert client.post(f"/api/v1/assessment-studio/questions/{row['id']}/action", json={"action": "retire", "version": row["version"], "note": "Not authorized"}).status_code == 403
    from app.models.course_ops import CourseCollaborator
    db.add(CourseCollaborator(course_id=studio_world[1].id, user_id=other.id)); db.commit()
    assert client.get(f"/api/v1/assessment-studio/courses/{studio_world[1].id}").status_code == 200
    assert client.get('/api/v1/assessment-studio/bank-questions').json()["questions"] == []


def test_coverage_counts_only_usable_questions_and_distinct_prompts(client, db, studio_world):
    teacher, course = studio_world
    publish(client, studio_world)
    publish(client, studio_world, title="How can a fraction be simplified?")
    publish(client, studio_world, title="Choose an equivalent fraction after a delay", purpose="followup")
    draft(client, studio_world, title="Unreviewed draft should not count")
    auth(client, teacher)
    r = client.get(f"/api/v1/assessment-studio/courses/{course.id}")
    assert r.status_code == 200, r.text
    c = r.json()["concepts"][0]
    assert c["practice_questions"] == 2 and c["practice_ready"]
    assert c["reserved_followups"] == 1 and not c["followup_ready"]
    duplicate = action(client, draft(client, studio_world), "review")
    assert client.post(f"/api/v1/assessment-studio/questions/{duplicate['id']}/action", json={"action": "publish", "version": duplicate["version"], "note": "Duplicate prompt"}).status_code == 409


def test_published_snapshot_grades_after_retirement_and_no_pre_submit_key_leak(client, db, studio_world, student_user):
    row = publish(client, studio_world)
    session = signals.build_adaptive(db, student_user.id, studio_world[1].id, 3, ["fractions"], focus_only=True)
    assert session.question_ids == [-row["id"]]
    public = signals.adaptive_questions(db, session)[0]
    assert not {"expected", "answer", "explanation"}.intersection(public)
    assert "expected" not in str(session.plan)
    action(client, row, "retire")
    # Even another bank workflow changing its answer cannot change a published session.
    bankq = db.query(BankQuestion).one(); bankq.correct_answer = 1; db.commit()
    result = signals.grade_adaptive(db, session, {str(-row["id"]): "2/4"})
    assert result["score"] == 1 and result["results"][0]["explanation"]
    assert db.query(MasteryEvidence).filter_by(source_kind="practice_question").count() == 1
    assert signals.build_adaptive(db, student_user.id, studio_world[1].id, 3, ["fractions"], focus_only=True).question_ids == []


def test_followup_prefers_unseen_reserve_and_reports_repeated_content(client, db, studio_world, student_user):
    for i in range(3): publish(client, studio_world, title=f"Practice question about fractions {i}")
    for i in range(3): publish(client, studio_world, title=f"Delayed question about fractions {i}", purpose="followup")
    first = signals.build_adaptive(db, student_user.id, studio_world[1].id, 3, ["fractions"], focus_only=True)
    assert len(first.question_ids) == 3
    assert all(db.query(StudioQuestion).filter_by(id=-qid).one().purpose == "practice" for qid in first.question_ids)
    delayed = signals.build_adaptive(db, student_user.id, studio_world[1].id, 3, ["fractions"], focus_only=True, phase="followup")
    assert not set(delayed.question_ids).intersection(first.question_ids)
    assert delayed.plan["new_question_count"] == 3 and delayed.plan["reused_question_count"] == 0
    again = signals.build_adaptive(db, student_user.id, studio_world[1].id, 3, ["fractions"], focus_only=True, phase="followup")
    assert again.plan["reused_question_count"] == 3 and "familiarity" in again.plan["why"][0]


def test_linking_adds_concept_and_rejects_cross_course_content(client, db, studio_world):
    teacher, course = studio_world
    lesson = Lesson(post_author=teacher.id, post_parent=course.id, post_title="Fractions lesson", post_status="publish")
    othercourse = Course(post_author=teacher.id, post_title="Other", course_price=0)
    db.add_all([lesson, othercourse]); db.flush()
    db.add(ConceptLink(kind="lesson", ref_id=str(lesson.id), concept="numbers", course_id=course.id))
    otherlesson = Lesson(post_author=teacher.id, post_parent=othercourse.id, post_title="Other lesson")
    db.add(otherlesson); db.commit(); auth(client, teacher)
    uri = f"/api/v1/assessment-studio/courses/{course.id}/links"
    for _ in range(2):
        assert client.post(uri, json={"kind": "lesson", "ref_id": lesson.id, "concept": "Fractions"}).status_code == 200
    assert db.query(ConceptLink).filter_by(kind="lesson", ref_id=str(lesson.id)).count() == 2
    assert client.post(uri, json={"kind": "lesson", "ref_id": otherlesson.id, "concept": "fractions"}).status_code == 422


def test_bank_import_is_a_draft_copy_and_requires_ownership(client, db, studio_world, student_user):
    teacher, course = studio_world
    row = publish(client, studio_world)
    count = db.query(BankQuestion).count()
    r = client.post(f"/api/v1/assessment-studio/courses/{course.id}/import", json={"bank_question_id": row["bank_question_id"], "concept": "equivalence", "purpose": "followup"})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft" and db.query(BankQuestion).count() == count + 1
    bank = QuestionBank(instructor_id=student_user.id, title="Private")
    db.add(bank); db.flush()
    q = BankQuestion(bank_id=bank.id, question_title="Private question", question_type="short_answer")
    db.add(q); db.commit()
    assert client.post(f"/api/v1/assessment-studio/courses/{course.id}/import", json={"bank_question_id": q.id, "concept": "fractions"}).status_code == 404


def test_planner_uses_published_practice_and_records_outcome_counts(client, db, studio_world, student_user, monkeypatch):
    teacher, course = studio_world
    for i in range(3): publish(client, studio_world, title=f"Practice fraction {i}")
    for i in range(3): publish(client, studio_world, title=f"Delayed fraction {i}", purpose="followup")
    db.add(MasteryEvidence(user_id=student_user.id, course_id=course.id, concept="fractions", score_pct=20, weight=1, source_kind="quiz", source_ref="seed"))
    goal = LearningGoal(user_id=student_user.id, course_id=course.id, title="Improve fractions", daily_minutes=30, target_date=planner.utcnow().date()+timedelta(days=20), timezone="UTC", status="active")
    db.add(goal); db.commit(); planner.refresh_goal(db, goal)
    task = db.query(LearningPlanTask).filter_by(goal_id=goal.id, kind="practice").one()
    session = planner.start_check(db, goal, task)
    planner.finish_check(db, goal, task, {str(qid): "2/4" for qid in session.question_ids})
    later = planner.utcnow()+timedelta(days=4); monkeypatch.setattr(planner, 'utcnow', lambda: later)
    delayed = db.query(LearningPlanTask).filter_by(kind="followup", goal_id=goal.id).one()
    session = planner.start_check(db, goal, delayed)
    outcome = planner.finish_check(db, goal, delayed, {str(qid): "2/4" for qid in session.question_ids})
    assert outcome["intervention_status"] == "resolved" and outcome["new_question_count"] == 3
    assert db.query(QuizAttempt).count() == 0
    c = svc.coverage(db, course.id)["concepts"][0]["outcomes"]
    assert c["graded_questions"] == 6 and c["valid_followups"] == c["paired_learners"] == 1
    assert c["mean_practice_to_followup_change"] == 0


def test_hidden_retired_unavailable_and_keyless_quiz_questions_do_not_count(db, studio_world):
    teacher, course = studio_world
    for mode in ("hidden", "retired", "future", "keyless", "good"):
        quiz = Quiz(post_author=teacher.id, post_parent=course.id, post_title=mode, post_status="publish", quiz_feedback_mode="reveal_never" if mode == "hidden" else "default")
        if mode == "future": quiz.quiz_available_from = svc.now()+timedelta(days=1)
        db.add(quiz); db.flush()
        q = QuizQuestion(quiz_id=quiz.id, question_title=mode, question_type="multiple_choice", is_retired=mode == "retired")
        db.add(q); db.flush()
        db.add(ConceptLink(kind="question", ref_id=str(q.question_id), concept="fractions", course_id=course.id))
        db.add_all([QuizQuestionAnswer(belongs_question_id=q.question_id, answer_title="Yes", is_correct=mode != "keyless"), QuizQuestionAnswer(belongs_question_id=q.question_id, answer_title="No", is_correct=False)])
    db.commit()
    assert [q["title"] for q in svc.catalog(db, course.id)] == ["good"]


def test_studio_migration_roundtrip_and_schema(tmp_path):
    from sqlalchemy import create_engine, inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path = Path(__file__).resolve().parents[1]/'alembic/versions/0022_assessment_studio.py'
    spec = importlib.util.spec_from_file_location('studio_migration_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    engine = create_engine(f"sqlite:///{tmp_path/'studio.db'}")
    with engine.begin() as conn:
        module.op = Operations(MigrationContext.configure(conn))
        module.upgrade(); module.upgrade()
        assert {c['name'] for c in inspect(conn).get_columns('studio_questions')} == set(StudioQuestion.__table__.columns.keys())
        module.downgrade(); assert not inspect(conn).has_table('studio_questions')
        module.upgrade()
    engine.dispose()


def test_review_is_invalidated_by_outside_bank_changes(client, db, studio_world):
    row = action(client, draft(client, studio_world), "review")
    bq = db.query(BankQuestion).one()
    bq.correct_answer = 1; db.commit()
    r = client.post(f"/api/v1/assessment-studio/questions/{row['id']}/action", json={"action": "publish", "version": row["version"], "note": "Publish previously reviewed question"})
    assert r.status_code == 409
    assert db.query(StudioQuestion).one().published_snapshot is None


@pytest.mark.parametrize("kind,correct,given,options", [
    ("multiple_select", [0, 1], ["one", "two"], ["one", "two", "three"]),
    ("true_false", "false", "False", []),
    ("short_answer", "HTML", " html ", []),
    ("fill_in_blanks", "paragraph", "PARAGRAPH", []),
])
def test_published_question_types_use_their_reviewed_answer(client, db, studio_world, student_user, kind, correct, given, options):
    row = publish(client, studio_world, title=f"Type-specific practice: {kind}", type=kind, answer=correct, options=options)
    session = signals.build_adaptive(db, student_user.id, studio_world[1].id, 3, ["fractions"], focus_only=True)
    result = signals.grade_adaptive(db, session, {str(-row["id"]): given})
    assert result["score"] == result["max_score"] == 1
    if kind in ("short_answer", "fill_in_blanks"):
        assert signals.adaptive_questions(db, session)[0]["options"] == []


def test_incomplete_bank_question_can_be_copied_but_must_be_fixed_before_review(client, db, studio_world):
    teacher, course = studio_world
    bank = QuestionBank(instructor_id=teacher.id, title="Imported bank")
    db.add(bank); db.flush()
    q = BankQuestion(bank_id=bank.id, question_title="Incomplete source question", question_type="short_answer", correct_answer="HTML", answer_explanation="")
    db.add(q); db.commit(); auth(client, teacher)
    r = client.post(f"/api/v1/assessment-studio/courses/{course.id}/import", json={"bank_question_id": q.id, "concept": "fractions"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    row = r.json()
    r = client.post(f"/api/v1/assessment-studio/questions/{row['id']}/action", json={"action": "review", "version": 1, "note": "Try incomplete question"})
    assert r.status_code == 422
    r = client.put(f"/api/v1/assessment-studio/questions/{row['id']}", json=payload(version=1))
    assert r.status_code == 200
    action(client, action(client, r.json(), "review"), "publish")


def test_legacy_bank_push_cannot_bypass_studio_review(client, db, studio_world):
    row = draft(client, studio_world)
    bq = db.query(BankQuestion).filter_by(id=row["bank_question_id"]).one()
    quiz = Quiz(post_author=studio_world[0].id, post_parent=studio_world[1].id, post_title="Existing graded quiz")
    db.add(quiz); db.commit()
    uri = f"/api/v1/question-banks/{bq.bank_id}/push-to-quiz/{quiz.id}"
    assert client.post(uri, json={"count": 1}).status_code == 422
    action(client, row, "review")
    assert client.post(uri, json={"count": 1}).status_code == 422
    assert db.query(QuizQuestion).count() == 0
