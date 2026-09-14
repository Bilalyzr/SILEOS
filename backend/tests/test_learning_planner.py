"""Planner lifecycle, privacy, evidence semantics, and migration regression tests."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import pytest
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.learning_planner import LearningGoal, LearningIntervention, LearningPlanTask
from app.models.learning_signals import AdaptiveSession, LearningSignal
from app.models.mastery import MasteryEvidence
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
from app.services import learning_planner_service as svc
from app.services.mastery_service import set_links


@pytest.fixture
def world(db, make_user, student_user):
    from app.models.user import InstructorProfile
    instructor = make_user(role="instructor", email="planner-instructor@example.com")
    db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    course = Course(post_title="Planning course", post_author=instructor.id, post_status="publish", course_price=0)
    db.add(course); db.flush()
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    lessons = []
    for i in range(4):
        lesson = Lesson(post_author=instructor.id, post_parent=course.id, post_title=f"Lesson {i}", post_status="publish", post_type="lesson", menu_order=i, lesson_video_duration="10:00")
        db.add(lesson); db.flush(); lessons.append(lesson)
    quiz = Quiz(post_author=instructor.id, post_parent=course.id, post_title="Concept check", post_status="publish")
    db.add(quiz); db.flush()
    questions = []
    for i in range(3):
        q = QuizQuestion(quiz_id=quiz.id, question_title=f"Check item {i}", question_type="multiple_choice", question_mark=1, question_order=i)
        db.add(q); db.flush()
        db.add_all([QuizQuestionAnswer(belongs_question_id=q.question_id, answer_title="yes", is_correct=True),
                    QuizQuestionAnswer(belongs_question_id=q.question_id, answer_title="no", is_correct=False)])
        questions.append(q)
    db.commit()
    set_links(db, "lesson", lessons[0].id, ["fractions"], course_id=course.id)
    for q in questions: set_links(db, "question", q.question_id, ["fractions"], course_id=course.id)
    return course, instructor, lessons, quiz, questions


def payload(course, **changes):
    return {"course_id": course.id, "title": "Understand fractions", "target_date": (svc.utcnow().date() + timedelta(days=30)).isoformat(),
            "daily_minutes": 30, "timezone": "UTC", **changes}


def create(client, as_user, student_user, world, **changes):
    as_user(student_user)
    r = client.post("/api/v1/planner/goals", json=payload(world[0], **changes))
    assert r.status_code == 200, r.text
    return r.json()


def struggle(db, student, course, lesson=None):
    if lesson:
        db.add_all([LearningSignal(user_id=student.id, course_id=course.id, lesson_id=lesson.id, kind="video_rewind", position_s=10, segment=1) for _ in range(3)])
    else:
        db.add(MasteryEvidence(user_id=student.id, course_id=course.id, concept="fractions", source_kind="quiz", source_ref="1", score_pct=30, weight=1))
    db.commit()


def check_task(goal, kind="practice"):
    return next(t for t in goal["tasks"] if t["kind"] == kind and t["status"] == "pending")


def answer(client, task, value="yes"):
    r = client.post(f"/api/v1/planner/tasks/{task['id']}/start")
    assert r.status_code == 200, r.text
    assert all("expected" not in q for q in r.json()["questions"])
    answers = {str(q["question_id"]): value for q in r.json()["questions"]}
    r = client.post(f"/api/v1/planner/tasks/{task['id']}/submit", json={"answers": answers})
    assert r.status_code == 200, r.text
    return r.json()


def test_goal_budget_refresh_and_study_do_not_award_mastery(client, db, world, as_user, student_user):
    goal = create(client, as_user, student_user, world, daily_minutes=20)
    assert len(goal["tasks"]) == 4
    sums = {}
    for t in goal["tasks"]: sums[t["due_date"]] = sums.get(t["due_date"], 0) + t["minutes"]
    assert max(sums.values()) <= 20
    refresh = client.post(f"/api/v1/planner/goals/{goal['id']}/refresh")
    assert refresh.status_code == 200 and len(refresh.json()["tasks"]) == 4
    assert db.query(LearningGoal).count() == 1
    assert create(client, as_user, student_user, world)["id"] == goal["id"]
    tid = goal["tasks"][0]["id"]
    assert client.post(f"/api/v1/planner/tasks/{tid}/action", json={"action": "done"}).status_code == 200
    assert db.query(MasteryEvidence).count() == 0
    assert client.post(f"/api/v1/planner/tasks/{tid}/action", json={"action": "done"}).status_code == 409


def test_behaviour_is_diagnostic_not_a_mastery_verdict(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0], world[2][0])
    goal = create(client, as_user, student_user, world)
    item = goal["interventions"][0]
    assert item["status"] == "suggested" and item["baseline_score"] is None
    assert "Behaviour alone" in item["reason"] and item["evidence"]["basis"] == "diagnostic"


def test_successful_check_requires_delayed_verification_and_is_idempotent(client, db, world, as_user, student_user, monkeypatch):
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    task = check_task(goal)
    assert client.post(f"/api/v1/planner/tasks/{task['id']}/action", json={"action": "done"}).status_code == 422
    first = client.post(f"/api/v1/planner/tasks/{task['id']}/start").json()
    assert client.post(f"/api/v1/planner/tasks/{task['id']}/start").json()["session_id"] == first["session_id"]
    assert db.query(AdaptiveSession).count() == 1
    result = answer(client, task)
    assert result["outcome"]["intervention_status"] == "monitoring"
    follow = check_task(result["goal"], "followup")
    assert client.post(f"/api/v1/planner/tasks/{follow['id']}/start").status_code == 422
    n = db.query(MasteryEvidence).count()
    again = client.post(f"/api/v1/planner/tasks/{task['id']}/submit", json={"answers": {}})
    assert again.status_code == 200 and again.json()["outcome"] == result["outcome"]
    assert db.query(MasteryEvidence).count() == n
    assert db.query(LearningPlanTask).filter_by(kind="followup").count() == 1
    later = svc.utcnow() + timedelta(days=4)
    monkeypatch.setattr(svc, "utcnow", lambda: later)
    final = answer(client, follow)
    assert final["outcome"]["intervention_status"] == "resolved"
    assert final["goal"]["interventions"][0]["followup_score"] == 100


def test_wrong_answers_escalate_and_instructor_can_close_or_request_check(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    result = answer(client, check_task(goal), "no")
    assert result["outcome"]["intervention_status"] == "needs_instructor"
    iid = goal["interventions"][0]["id"]
    as_user(world[1])
    from app.core.security import create_access_token
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": str(world[1].id)})
    queue = client.get("/api/v1/planner/instructor/interventions")
    assert queue.status_code == 200 and queue.json()["interventions"][0]["learner_id"] == student_user.id
    r = client.post(f"/api/v1/planner/instructor/interventions/{iid}/review", json={"action": "request_check", "note": "Review the worked example first."})
    assert r.status_code == 200, r.text
    assert db.query(LearningPlanTask).filter_by(kind="practice", status="pending").count() == 1
    n = db.query(MasteryEvidence).count()
    r = client.post(f"/api/v1/planner/instructor/interventions/{iid}/review", json={"action": "dismiss", "note": "Discussed this with the learner."})
    assert r.status_code == 200 and r.json()["status"] == "dismissed"
    assert db.query(MasteryEvidence).count() == n
    as_user(student_user)
    assert client.post(f"/api/v1/planner/goals/{goal['id']}/refresh").json()["interventions"][0]["status"] == "dismissed"


@pytest.mark.parametrize("count", [0, 1])
def test_missing_or_insufficient_questions_never_claim_resolution(client, db, world, as_user, student_user, count):
    from app.models.mastery import ConceptLink
    for q in world[4][count:]:
        db.query(ConceptLink).filter_by(kind="question", ref_id=str(q.question_id)).delete()
    db.commit()
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    task = check_task(goal)
    if count == 0:
        assert client.post(f"/api/v1/planner/tasks/{task['id']}/start").status_code == 422
        assert db.query(AdaptiveSession).count() == 0
    else:
        assert answer(client, task)["outcome"]["enough_evidence"] is False
    assert db.query(LearningIntervention).one().status == "needs_instructor"


def test_access_control_for_other_learners_unrelated_instructors_and_collaborators(client, db, world, as_user, student_user, make_user):
    from app.models.course_ops import CourseCollaborator
    from app.models.user import InstructorProfile
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    tid = check_task(goal)["id"]; iid = goal["interventions"][0]["id"]
    other = make_user(role="student", email="planner-other@example.com")
    as_user(other)
    assert client.get("/api/v1/planner/me").json()["goals"] == []
    assert client.post("/api/v1/planner/goals", json=payload(world[0])).status_code == 403
    for path in (f"goals/{goal['id']}/refresh", f"tasks/{tid}/start", f"tasks/{tid}/submit"):
        assert client.post('/api/v1/planner/' + path, json={"answers": {}}).status_code == 404
    other_inst = make_user(role="instructor", email="planner-otherinst@example.com")
    db.add(InstructorProfile(user_id=other_inst.id, is_approved=True)); db.commit()
    as_user(other_inst)
    from app.core.security import create_access_token
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": str(other_inst.id)})
    assert client.get("/api/v1/planner/instructor/interventions").json()["interventions"] == []
    body = {"action": "dismiss", "note": "No longer needed"}
    assert client.post(f"/api/v1/planner/instructor/interventions/{iid}/review", json=body).status_code == 403
    db.add(CourseCollaborator(course_id=world[0].id, user_id=other_inst.id)); db.commit()
    assert len(client.get("/api/v1/planner/instructor/interventions").json()["interventions"]) == 1
    assert client.post(f"/api/v1/planner/instructor/interventions/{iid}/review", json=body).status_code == 200


def test_pause_snooze_and_revoked_enrollment(client, db, world, as_user, student_user):
    goal = create(client, as_user, student_user, world)
    tid = goal["tasks"][0]["id"]
    r = client.post(f"/api/v1/planner/tasks/{tid}/action", json={"action": "snooze"})
    assert next(t for t in r.json()["tasks"] if t["id"] == tid)["due_date"] > goal["today"]
    create(client, as_user, student_user, world, status="paused")
    assert client.post(f"/api/v1/planner/goals/{goal['id']}/refresh").status_code == 409
    assert client.post(f"/api/v1/planner/tasks/{tid}/action", json={"action": "done"}).status_code == 409
    create(client, as_user, student_user, world)
    db.query(Enrollment).filter_by(user_id=student_user.id, course_id=world[0].id).update({"enrollment_status": "suspended"}); db.commit()
    assert client.get("/api/v1/planner/me").json()["goals"] == []
    assert client.post(f"/api/v1/planner/goals/{goal['id']}/refresh").status_code == 403


@pytest.mark.parametrize("changes", [{"daily_minutes": 0}, {"timezone": "not/a-zone"}, {"target_date": "2020-01-01"}, {"title": "   "}])
def test_goal_validation(client, world, as_user, student_user, changes):
    as_user(student_user)
    assert client.post("/api/v1/planner/goals", json=payload(world[0], **changes)).status_code == 422


def test_scheduler_refresh_is_idempotent_and_ignores_paused_goals(client, db, world, as_user, student_user):
    goal = create(client, as_user, student_user, world)
    n = db.query(LearningPlanTask).count()
    assert svc.planner_pass(db) == 1 and db.query(LearningPlanTask).count() == n
    db.query(LearningGoal).filter_by(id=goal["id"]).update({"status": "paused"}); db.commit()
    assert svc.planner_pass(db) == 0


def test_unpublished_questions_are_not_used(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0])
    world[3].post_status = "draft"; db.commit()
    goal = create(client, as_user, student_user, world)
    assert client.post(f"/api/v1/planner/tasks/{check_task(goal)['id']}/start").status_code == 422


def test_migration_roundtrip_and_schema_parity(tmp_path):
    from sqlalchemy import create_engine, inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.core.database import Base
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0021_learning_planner.py"
    spec = importlib.util.spec_from_file_location("planner_migration_test", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    engine = create_engine(f"sqlite:///{tmp_path / 'planner.sqlite'}")
    tables = ("learning_goals", "learning_interventions", "learning_plan_tasks")
    with engine.begin() as connection:
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade(); module.upgrade()
        for name in tables:
            assert {c["name"] for c in inspect(connection).get_columns(name)} == set(Base.metadata.tables[name].columns.keys())
        module.downgrade()
        assert not set(tables).intersection(inspect(connection).get_table_names())
        module.upgrade()
    engine.dispose()



def test_single_answer_question_cannot_be_passed_by_sending_all_options(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    task = check_task(goal)
    r = client.post(f"/api/v1/planner/tasks/{task['id']}/start").json()
    # Even the generic adaptive endpoint must not allow bypassing the planner.
    r = client.post(f"/api/v1/signals/adaptive/{r['session_id']}/submit", json={"answers": {str(q.question_id): ["yes", "no"] for q in world[4]}})
    assert r.status_code == 200 and r.json()["score"] == 0
    r = client.post(f"/api/v1/planner/tasks/{task['id']}/submit", json={"answers": {}})
    assert r.json()["outcome"]["intervention_status"] == "needs_instructor"


def test_real_quiz_answers_create_intervention_without_quiz_concept_links(client, db, world, as_user, student_user):
    from app.models.quiz import QuizAttempt, QuizAttemptAnswer
    attempt = QuizAttempt(user_id=student_user.id, quiz_id=world[3].id, course_id=world[0].id, attempt_status="attempt_ended")
    db.add(attempt); db.flush()
    for q in world[4]:
        db.add(QuizAttemptAnswer(user_id=student_user.id, quiz_id=world[3].id, question_id=q.question_id,
            quiz_attempt_id=attempt.attempt_id, is_correct=False, question_mark=1, achieved_mark=0))
    db.commit()
    goal = create(client, as_user, student_user, world)
    assert goal["interventions"][0]["concept"] == "fractions"
    assert goal["interventions"][0]["baseline_score"] == 0


def test_resolved_intervention_reopens_only_on_fresh_failed_evidence(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    item = db.query(LearningIntervention).one()
    item.status = "resolved"
    item.followup_score = 100
    item.updated_at = svc.utcnow() - timedelta(days=1)
    for task in db.query(LearningPlanTask).filter_by(intervention_id=item.id): task.status = "done"
    db.commit()
    db.add(MasteryEvidence(user_id=student_user.id, course_id=world[0].id, concept="fractions", source_kind="question", source_ref="new-check", score_pct=0, weight=1, created_at=svc.utcnow()))
    db.commit()
    r = client.post(f"/api/v1/planner/goals/{goal['id']}/refresh")
    assert r.status_code == 200, r.text
    assert r.json()["interventions"][0]["status"] == "suggested"
    assert r.json()["interventions"][0]["history"][-1]["action"] == "reopened"
    assert len([t for t in r.json()["tasks"] if t["kind"] == "practice" and t["status"] == "pending"]) == 1


def test_local_day_and_overloaded_deadline_are_explicit(client, db, world, as_user, student_user, monkeypatch):
    now = datetime(2026, 9, 6, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(svc, "utcnow", lambda: now)
    goal = create(client, as_user, student_user, world, timezone="Asia/Kolkata", daily_minutes=5, target_date="2026-09-07")
    assert goal["today"] == "2026-09-07"
    assert len(goal["warnings"]) == 2
    assert goal["estimated_finish"] > goal["target_date"]



def test_quiz_submission_replans_existing_goal_and_hidden_feedback_is_respected(client, db, world, as_user, student_user):
    goal = create(client, as_user, student_user, world)
    assert goal["interventions"] == []
    # Ordinarily this endpoint also requires JWT get_current_user rather than only active-user override.
    from app.core.security import create_access_token
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": str(student_user.id)})
    r = client.post(f"/api/v1/courses/{world[0].id}/quizzes/{world[3].id}/submit", json={"answers": {str(q.question_id): 1 for q in world[4]}})
    assert r.status_code == 200, r.text
    assert db.query(LearningIntervention).filter_by(goal_id=goal["id"]).count() == 1
    world[3].quiz_feedback_mode = "reveal_never"; db.commit()
    assert svc._assessment(db, db.query(LearningGoal).one()) == {}
    assert client.post(f"/api/v1/planner/tasks/{check_task(client.get('/api/v1/planner/me').json()['goals'][0])['id']}/start").status_code == 422


def test_review_covers_curriculum_once_and_dismissal_restores_it(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0])
    data = create(client, as_user, student_user, world)
    goal = db.query(LearningGoal).one()
    review = db.query(LearningPlanTask).filter_by(goal_id=goal.id, kind="review").one()
    curriculum = db.query(LearningPlanTask).filter_by(goal_id=goal.id, kind="lesson", lesson_id=review.lesson_id).one()
    assert curriculum.status == "skipped"
    assert data["remaining_minutes"] == 50  # four ten-minute lessons, plus one check
    row = db.query(LearningIntervention).one()
    svc.review_intervention(db, goal, row, "dismiss", "Continue the curriculum", world[0].post_author)
    assert curriculum.status == "pending"
    assert svc.goal_dict(db, goal)["remaining_minutes"] == 40


def test_studied_review_does_not_return_as_duplicate_curriculum(client, db, world, as_user, student_user):
    struggle(db, student_user, world[0])
    goal = create(client, as_user, student_user, world)
    review = next(t for t in goal["tasks"] if t["kind"] == "review")
    assert client.post(f"/api/v1/planner/tasks/{review['id']}/action", json={"action": "done"}).status_code == 200
    refreshed = client.post(f"/api/v1/planner/goals/{goal['id']}/refresh").json()
    assert not any(t["kind"] == "lesson" and t["lesson_url"] == review["lesson_url"] and t["status"] == "pending" for t in refreshed["tasks"])
