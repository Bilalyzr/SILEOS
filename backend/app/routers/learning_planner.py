"""Learner-owned planner and course-editor intervention queue."""
from datetime import date, timedelta
from typing import Any, Dict, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.communication_automation import CommunicationTopicPreference
from app.models.course import Course
from app.models.learning_planner import LearningGoal, LearningPlanTask, LearningIntervention
from app.models.user import User, UserProfile
from app.services.auth_service import AuthService
from app.services.course_access import can_edit, collaborated_course_ids, ADMIN_ROLES
from app.services import learning_planner_service as svc
from app.services.learning_signals_service import adaptive_questions
from app.services.notification_service import create_notification, _send_notification_email

router = APIRouter()


def planner_db(db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    try:
        yield db
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "The plan changed during this request. Refresh and try again.")


class GoalIn(BaseModel):
    course_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=200)
    target_date: date
    daily_minutes: int = Field(ge=5, le=180)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)
    status: Literal["active", "paused"] = "active"


class TaskAction(BaseModel):
    action: Literal["done", "snooze"]


class AnswersIn(BaseModel):
    answers: Dict[str, Any]


class ReviewIn(BaseModel):
    action: Literal["dismiss", "request_check"]
    note: str = Field(min_length=3, max_length=2000)


class RiskInterventionIn(BaseModel):
    course_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    note: str = Field(default="", max_length=2000)
    concept: str | None = Field(default=None, max_length=80)


def _send_learning_notification(db, *, user_id: int, title: str, message: str,
                                related_id: int, background_tasks: BackgroundTasks):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    topic = db.query(CommunicationTopicPreference).filter_by(
        user_id=user_id, topic="learning_interventions"
    ).first()
    in_app_enabled = True if topic is None else bool(topic.in_app_enabled)
    email_enabled = True if topic is None else bool(topic.email_enabled)
    email_allowed = email_enabled and (True if profile is None else bool(profile.receive_notifications))
    if in_app_enabled:
        create_notification(
            db,
            user_id=user_id,
            type="learning_intervention",
            title=title,
            message=message,
            link="/student/learning-plan",
            related_id=related_id,
            send_email=email_allowed,
            background_tasks=background_tasks,
        )
    elif email_allowed:
        account = db.query(User).filter(User.id == user_id).first()
        if account and account.user_email:
            background_tasks.add_task(
                _send_notification_email, account.user_email, title, message
            )


def _own_goal(db, gid, user, active=False):
    goal = db.query(LearningGoal).filter_by(id=gid, user_id=user.id).with_for_update().first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    if not svc.enrolled(db, user.id, goal.course_id):
        raise HTTPException(403, "An active course enrollment is required")
    if active and goal.status != "active":
        raise HTTPException(409, "Resume this goal first")
    return goal


def _own_task(db, tid, user):
    task = db.query(LearningPlanTask).filter_by(id=tid).first()
    if not task:
        raise HTTPException(404, "Task not found")
    goal = _own_goal(db, task.goal_id, user, active=True)
    db.refresh(task)
    return goal, task


@router.get("/me")
def my_planner(db: Session = Depends(planner_db), user: User = Depends(AuthService.get_current_active_user)):
    from app.models.enrollment import Enrollment
    courses = db.query(Course).join(Enrollment, Enrollment.course_id == Course.id).filter(
        Enrollment.user_id == user.id, Enrollment.enrollment_status.in_(svc.ACTIVE_ENROLLMENTS)).order_by(Course.post_title).all()
    ids = [c.id for c in courses]
    goals = db.query(LearningGoal).filter(LearningGoal.user_id == user.id, LearningGoal.course_id.in_(ids)).order_by(LearningGoal.id).all()
    return {"courses": [{"id": c.id, "title": c.post_title} for c in courses], "goals": [svc.goal_dict(db, g) for g in goals]}


@router.post("/goals")
def save_goal(body: GoalIn, db: Session = Depends(planner_db), user: User = Depends(AuthService.get_current_active_user)):
    if not svc.enrolled(db, user.id, body.course_id):
        raise HTTPException(403, "Enroll in the course before creating a goal")
    try:
        zone = ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Use a valid IANA time zone")
    today = svc.utcnow().astimezone(zone).date()
    if (body.status == "active" and body.target_date < today) or body.target_date > today + timedelta(days=730):
        raise HTTPException(422, "Target date must be today or within the next two years")
    if len(body.title.strip()) < 3:
        raise HTTPException(422, "Describe your goal in at least three characters")
    goal = db.query(LearningGoal).filter_by(user_id=user.id, course_id=body.course_id).with_for_update().first()
    if not goal:
        goal = LearningGoal(user_id=user.id, course_id=body.course_id)
        db.add(goal)
    for key in ("title", "target_date", "daily_minutes", "timezone", "status"):
        setattr(goal, key, getattr(body, key))
    goal.title = goal.title.strip()
    db.flush()
    if goal.status == "active":
        svc.refresh_goal(db, goal)
    else:
        db.commit()
    return svc.goal_dict(db, goal)


@router.post("/goals/{goal_id}/refresh")
def refresh(goal_id: int, db: Session = Depends(planner_db), user: User = Depends(AuthService.get_current_active_user)):
    goal = _own_goal(db, goal_id, user, active=True)
    svc.refresh_goal(db, goal)
    return svc.goal_dict(db, goal)


@router.post("/tasks/{task_id}/action")
def task_action(task_id: int, body: TaskAction, db: Session = Depends(planner_db), user: User = Depends(AuthService.get_current_active_user)):
    goal, task = _own_task(db, task_id, user)
    if task.status != "pending":
        raise HTTPException(409, "This task is already finished")
    if body.action == "done":
        if task.kind not in ("lesson", "review"):
            raise HTTPException(422, "Understanding checks must be submitted and graded")
        task.status = "done"
        task.completed_at = svc.utcnow()
        task.outcome = {"note": "Marked studied by you. This does not award course progress or mastery."}
    else:
        task.not_before = max(task.not_before, task.due_date, svc.today_for(goal)) + timedelta(days=1)
    svc._schedule(db, goal, svc.today_for(goal))
    db.commit()
    return svc.goal_dict(db, goal)


@router.post("/tasks/{task_id}/start")
def start(task_id: int, db: Session = Depends(planner_db), user: User = Depends(AuthService.get_current_active_user)):
    goal, task = _own_task(db, task_id, user)
    try:
        session = svc.start_check(db, goal, task)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"session_id": session.id, "questions": adaptive_questions(db, session), "plan": session.plan}


@router.post("/tasks/{task_id}/submit")
def submit(task_id: int, body: AnswersIn, db: Session = Depends(planner_db), user: User = Depends(AuthService.get_current_active_user)):
    goal, task = _own_task(db, task_id, user)
    if task.kind not in ("practice", "followup") or task.status == "skipped":
        raise HTTPException(422, "This is not an active understanding check")
    try:
        outcome = svc.finish_check(db, goal, task, body.answers)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"outcome": outcome, "goal": svc.goal_dict(db, goal)}


@router.get("/instructor/interventions")
def instructor_queue(db: Session = Depends(planner_db), user: User = Depends(AuthService.require_instructor)):
    from sqlalchemy import or_, case
    query = db.query(LearningIntervention, LearningGoal, Course, User).join(
        LearningGoal, LearningGoal.id == LearningIntervention.goal_id).join(
        Course, Course.id == LearningGoal.course_id).join(User, User.id == LearningGoal.user_id)
    if user.role not in ADMIN_ROLES:
        query = query.filter(or_(Course.post_author == user.id, Course.id.in_(collaborated_course_ids(db, user.id))))
    from app.models.enrollment import Enrollment
    query = query.filter(db.query(Enrollment.id).filter(
        Enrollment.user_id == LearningGoal.user_id, Enrollment.course_id == LearningGoal.course_id,
        Enrollment.enrollment_status.in_(svc.ACTIVE_ENROLLMENTS)).exists())
    priority = case((LearningIntervention.status == "needs_instructor", 0),
                    (LearningIntervention.status == "suggested", 1),
                    (LearningIntervention.status == "monitoring", 2), else_=3)
    rows = query.order_by(priority, LearningIntervention.updated_at.desc(), LearningIntervention.id.desc()).limit(300).all()
    out = []
    for row, goal, course, learner in rows:
        if not svc.enrolled(db, goal.user_id, goal.course_id):
            continue
        out.append({**svc.intervention_dict(row), "goal_id": goal.id, "goal_status": goal.status,
                    "course_id": course.id, "course_title": course.post_title,
                    "learner_id": learner.id, "learner_name": learner.display_name or "Learner"})
    rank = {"needs_instructor": 0, "suggested": 1, "monitoring": 2, "resolved": 3, "dismissed": 4}
    out.sort(key=lambda r: (rank[r["status"]], -r["id"]))
    return {"interventions": out, "limit": 300}


@router.post("/instructor/risk-interventions")
def create_from_risk(
    body: RiskInterventionIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(planner_db),
    user: User = Depends(AuthService.require_instructor),
):
    course = db.query(Course).filter_by(id=body.course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if not can_edit(db, course, user):
        raise HTTPException(403, "Not your course")
    learner = db.query(User).filter_by(id=body.user_id).first()
    if not learner:
        raise HTTPException(404, "Learner not found")
    try:
        row, goal, created, goal_created = svc.create_risk_intervention(
            db,
            course=course,
            learner=learner,
            reviewer_id=user.id,
            note=body.note.strip(),
            concept=body.concept,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))

    _send_learning_notification(
        db,
        user_id=goal.user_id,
        title="Your instructor added a support step",
        message=body.note.strip() or row.reason,
        related_id=row.id,
        background_tasks=background_tasks,
    )
    return {
        **svc.intervention_dict(row),
        "goal_id": goal.id,
        "goal_status": goal.status,
        "course_id": course.id,
        "course_title": course.post_title,
        "learner_id": learner.id,
        "learner_name": learner.display_name or "Learner",
        "created": created,
        "goal_created": goal_created,
    }


@router.post("/instructor/interventions/{intervention_id}/review")
def review(
    intervention_id: int,
    body: ReviewIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(planner_db),
    user: User = Depends(AuthService.require_instructor),
):
    row = db.query(LearningIntervention).filter_by(id=intervention_id).first()
    if not row:
        raise HTTPException(404, "Intervention not found")
    goal = db.query(LearningGoal).filter_by(id=row.goal_id).with_for_update().one()
    course = db.query(Course).filter_by(id=goal.course_id).first()
    if not can_edit(db, course, user):
        raise HTTPException(403, "Not your course")
    if goal.status != "active" or not svc.enrolled(db, goal.user_id, goal.course_id):
        raise HTTPException(409, "The learner must have an active goal and enrollment")
    if len(body.note.strip()) < 3:
        raise HTTPException(422, "Explain the intervention decision")
    svc.review_intervention(db, goal, row, body.action, body.note.strip(), user.id)
    title = (
        "Your instructor requested an understanding check"
        if body.action == "request_check"
        else "Your instructor added a learning-plan note"
    )
    _send_learning_notification(
        db,
        user_id=goal.user_id,
        title=title,
        message=body.note.strip(),
        related_id=row.id,
        background_tasks=background_tasks,
    )
    return svc.intervention_dict(row)
