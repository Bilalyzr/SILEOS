"""SILEOS feature pack — prerequisites, learning paths, xAPI spine,
mastery and at-risk analytics (blueprint §3.2, §3.5, §3.6/§15).

Backend-only integration: nothing here changes existing UI. Endpoints are
the contract future UI (or the existing app's next iteration) consumes.

Gating philosophy: prerequisites are EXPOSED (GET /unlock-status) but not
yet ENFORCED on enrollment/mark-complete — enforcement flips behind the
existing flows once the UI shows unlock states (documented in
docs/SILEOS_FEATURES.md §Rollout).
"""
from datetime import datetime, timedelta, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import QuizAttempt
from app.models.sileos_pack import (CoursePrerequisite, LearningPath,
                                    StudentRiskFlag, XapiStatement)
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()


def _course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


def _require_course_owner(user, course: Course) -> None:
    if user.role != "admin" and course.post_author != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Not your course")


# --------------------------------------------------------------------- prereqs

@router.put("/courses/{course_id}/prerequisites")
def set_prerequisites(
    course_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Replace the prerequisite set for a course. Body:
    {"items": [{"requires_course_id": int, "min_progress_percentage": int}]}
    Self-reference and duplicates are rejected; the required course must exist."""
    course = _course_or_404(db, course_id)
    _require_course_owner(current_user, course)

    items = payload.get("items")
    if not isinstance(items, list):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail='body must be {"items": [...]}')

    seen = set()
    clean: list[tuple[int, int]] = []
    for item in items:
        req_id = item.get("requires_course_id")
        min_pct = int(item.get("min_progress_percentage", 100))
        if not isinstance(req_id, int):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="requires_course_id must be int")
        if req_id == course_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="a course cannot require itself")
        if not 0 <= min_pct <= 100:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="min_progress_percentage must be 0-100")
        _course_or_404(db, req_id)
        if req_id in seen:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"duplicate prerequisite {req_id}")
        seen.add(req_id)
        clean.append((req_id, min_pct))

    db.query(CoursePrerequisite).filter(
        CoursePrerequisite.course_id == course_id).delete()
    for req_id, min_pct in clean:
        db.add(CoursePrerequisite(
            course_id=course_id,
            requires_course_id=req_id,
            min_progress_percentage=min_pct,
        ))
    db.commit()
    return {"course_id": course_id,
            "prerequisites": [{"requires_course_id": r, "min_progress_percentage": m}
                              for r, m in clean]}


@router.get("/courses/{course_id}/prerequisites")
def get_prerequisites(
    course_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(AuthService.get_current_user),
):
    rules = (db.query(CoursePrerequisite)
             .filter(CoursePrerequisite.course_id == course_id).all())
    return {
        "course_id": course_id,
        "prerequisites": [
            {"requires_course_id": r.requires_course_id,
             "min_progress_percentage": r.min_progress_percentage}
            for r in rules
        ],
    }


def _prereq_status(db: Session, user_id: int, course_id: int) -> list[dict]:
    rules = (db.query(CoursePrerequisite)
             .filter(CoursePrerequisite.course_id == course_id).all())
    out = []
    for rule in rules:
        enrollment = (db.query(Enrollment)
                      .filter(Enrollment.course_id == rule.requires_course_id,
                              Enrollment.user_id == user_id,
                              Enrollment.enrollment_status.in_(["enrolled", "completed"]))
                      .first())
        progress = int(enrollment.course_progress_percentage or 0) if enrollment else 0
        out.append({
            "requires_course_id": rule.requires_course_id,
            "min_progress_percentage": rule.min_progress_percentage,
            "enrolled": enrollment is not None,
            "progress_percentage": progress,
            "met": progress >= rule.min_progress_percentage,
        })
    return out


@router.get("/courses/{course_id}/unlock-status")
def unlock_status(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    """Can THIS student start `course_id`? Every unmet rule comes back with
    its numbers so the UI can explain the lock (blueprint §11.4: explain,
    never just block)."""
    _course_or_404(db, course_id)
    rules = _prereq_status(db, current_user.id, course_id)
    unmet = [r for r in rules if not r["met"]]
    return {
        "course_id": course_id,
        "unlocked": len(unmet) == 0,
        "rules": rules,
        "unmet_count": len(unmet),
    }


# -------------------------------------------------------------- learning paths

@router.post("/learning-paths")
def create_path(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    title = (payload.get("title") or "").strip()
    course_ids = payload.get("course_ids") or []
    if not title or not isinstance(course_ids, list) or not course_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="title and a non-empty course_ids list are required")
    for cid in course_ids:
        _course_or_404(db, int(cid))
    path = LearningPath(
        owner_id=current_user.id,
        title=title[:200],
        description=payload.get("description", ""),
        course_ids=[int(c) for c in course_ids],
    )
    db.add(path)
    db.commit()
    db.refresh(path)
    return {"id": path.id, "title": path.title, "course_ids": path.course_ids}


@router.get("/learning-paths")
def list_paths(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    rows = (db.query(LearningPath)
            .filter(LearningPath.owner_id == current_user.id)
            .order_by(LearningPath.created_at.desc()).all())
    return {"paths": [
        {"id": r.id, "title": r.title, "description": r.description,
         "course_ids": r.course_ids}
        for r in rows
    ]}


@router.get("/learning-paths/{path_id}/progress")
def path_progress(
    path_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    """The student's course-by-course progress along a path — the blueprint's
    "learning-path progress" analytics line, computed from enrollments."""
    path = db.query(LearningPath).filter(LearningPath.id == path_id).first()
    if not path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    enrollments = {
        e.course_id: e for e in db.query(Enrollment)
        .filter(Enrollment.user_id == current_user.id,
                Enrollment.course_id.in_(path.course_ids)).all()
    }
    steps = []
    for cid in path.course_ids:
        e = enrollments.get(cid)
        steps.append({
            "course_id": cid,
            "enrolled": e is not None,
            "progress_percentage": int(e.course_progress_percentage or 0) if e else 0,
            "completed": bool(e and e.enrollment_status == "completed"),
        })
    done = sum(1 for s in steps if s["completed"])
    return {
        "path_id": path_id,
        "title": path.title,
        "steps": steps,
        "completed_steps": done,
        "total_steps": len(steps),
    }


# ------------------------------------------------------------------ xAPI spine

VALID_VERBS = {"launched", "watched", "interacted", "completed", "passed",
               "failed", "attempted", "answered", "paused", "resumed",
               "experienced", "downloaded", "submitted"}
VALID_OBJECTS = {"lesson", "course", "quiz", "h5p", "game", "ebook", "live_class", "geogebra"}


@router.post("/xapi/statements")
def ingest_statement(
    payload: dict,
    request=None,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    """Ingest one xAPI-lite statement. The ACTOR is always the authenticated
    user — clients cannot forge someone else's stream (admin batch-import
    arrives with the analytics ETL, not here)."""
    verb = payload.get("verb")
    object_type = payload.get("object_type")
    object_id = payload.get("object_id")
    if verb not in VALID_VERBS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"verb must be one of {sorted(VALID_VERBS)}")
    if object_type not in VALID_OBJECTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"object_type must be one of {sorted(VALID_OBJECTS)}")
    if object_id in (None, ""):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="object_id is required")

    statement = XapiStatement(
        actor_user_id=current_user.id,
        verb=verb,
        object_type=object_type,
        object_id=str(object_id),
        object_ref=f"https://sashainfinity.com/lms/{object_type}/{object_id}",
        result=payload.get("result") or {},
        context=payload.get("context") or {},
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return {"id": statement.id, "stored": True}


@router.get("/xapi/me/statements")
def my_statements(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    limit = max(1, min(limit, 200))
    rows = (db.query(XapiStatement)
            .filter(XapiStatement.actor_user_id == current_user.id)
            .order_by(XapiStatement.stored_at.desc()).limit(limit).all())
    return {"statements": [
        {"verb": r.verb, "object_type": r.object_type, "object_id": r.object_id,
         "result": r.result, "stored_at": r.stored_at.isoformat() if r.stored_at else None}
        for r in rows
    ]}


@router.get("/xapi/statements")
def all_statements(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_admin),
):
    limit = max(1, min(limit, 500))
    rows = (db.query(XapiStatement)
            .order_by(XapiStatement.stored_at.desc()).limit(limit).all())
    return {"statements": [
        {"actor_user_id": r.actor_user_id, "verb": r.verb,
         "object_type": r.object_type, "object_id": r.object_id,
         "result": r.result,
         "stored_at": r.stored_at.isoformat() if r.stored_at else None}
        for r in rows
    ]}


# ------------------------------------------------------------------- mastery

def _course_mastery(db: Session, user_id: int, course_id: int) -> dict | None:
    enrollment = (db.query(Enrollment)
                  .filter(Enrollment.course_id == course_id,
                          Enrollment.user_id == user_id,
                          Enrollment.enrollment_status.in_(["enrolled", "completed"]))
                  .first())
    if not enrollment:
        return None
    attempts = (db.query(QuizAttempt)
                .filter(QuizAttempt.course_id == course_id,
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.attempt_status == "attempt_submitted")
                .all())
    passed = 0
    quiz_ids = set()
    for a in attempts:
        quiz_ids.add(a.quiz_id)
        earned = float(a.earned_marks or 0)
        total = float(a.total_marks or 0)
        if total > 0 and (earned / total) * 100 >= 80.0:
            passed += 1
    completion = int(enrollment.course_progress_percentage or 0)
    quiz_rate = (passed / len(quiz_ids) * 100) if quiz_ids else None
    # Mastery = 60% lesson completion + 40% unique-quiz pass rate. A course
    # with no quizzes is mastery = completion (documented weighting).
    if quiz_rate is None:
        mastery = completion
    else:
        mastery = round(0.6 * completion + 0.4 * quiz_rate, 1)
    level = ("novice" if mastery < 40 else
             "developing" if mastery < 70 else
             "proficient" if mastery < 90 else "mastered")
    return {
        "course_id": course_id,
        "completion_percentage": completion,
        "quizzes_passed": passed,
        "quizzes_attempted_distinct": len(quiz_ids),
        "quiz_pass_rate": round(quiz_rate, 1) if quiz_rate is not None else None,
        "mastery": mastery,
        "level": level,
    }


@router.get("/analytics/students/{user_id}/mastery")
def student_mastery(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    """Per-course mastery for one student (blueprint §15 adaptive/Mastery
    learning graph, lite). Students see their own; instructors/admins see all."""
    if current_user.id != user_id and current_user.role == "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Students may only view their own mastery")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    enrollments = (db.query(Enrollment)
                   .filter(Enrollment.user_id == user_id,
                           Enrollment.enrollment_status.in_(["enrolled", "completed"]))
                   .all())
    courses = [
        m for m in (_course_mastery(db, user_id, e.course_id) for e in enrollments)
        if m is not None
    ]
    overall = round(sum(c["mastery"] for c in courses) / len(courses), 1) if courses else 0.0
    return {"student": {"id": user_id, "name": target.display_name},
            "courses": courses,
            "overall_mastery": overall,
            "overall_level": ("novice" if overall < 40 else
                              "developing" if overall < 70 else
                              "proficient" if overall < 90 else "mastered")}


# --------------------------------------------------- cumulative grading

@router.get("/analytics/courses/{course_id}/students/{user_id}/cumulative-grade")
def cumulative_grade(
    course_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_user),
):
    """Owner rule: the course grade is the CUMULATIVE of quiz + assignment +
    scored interactive modules (H5P/Game). Weights: quizzes 40%, assignments
    40%, interactive modules 20% (no module results -> their weight
    redistributes to quizzes+assignments 50/50). The breakdown is returned
    so the UI can show the math, not just a number."""
    if current_user.id != user_id and current_user.role == "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Students may only view their own grade")
    enrollment = (db.query(Enrollment)
                  .filter(Enrollment.course_id == course_id,
                          Enrollment.user_id == user_id,
                          Enrollment.enrollment_status.in_(["enrolled", "completed"]))
                  .first())
    if not enrollment:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail="Student is not enrolled in this course")

    from app.models.quiz import Quiz, QuizAttempt
    from app.models.assignment import Assignment, AssignmentSubmission

    # Weights default from type_profiles (v2.0 spec §5.3) — MP: quiz 25 /
    # 3D 50 / modules 10 / assignments 15; SP: 30/10/25/15 + live 20;
    # UP: 40/15/15/20 + live 10. Module weight redistributes when empty.
    weights = {"quizzes": 40, "three_d_tasks": 15, "games_h5p": 15,
               "assignments": 20, "live_participation": 10}
    from sqlalchemy import text
    # v2.0 §5.3 defaults by type — used when type_profiles has no row (or the
    # table is absent, e.g. the create_all test DB: it is a raw-SQL table).
    TYPE_DEFAULT_WEIGHTS = {
        "meiporul": {"quizzes": 25, "three_d_tasks": 50, "games_h5p": 10, "assignments": 15, "live_participation": 0},
        "seyappaduporul": {"quizzes": 30, "three_d_tasks": 10, "games_h5p": 25, "assignments": 15, "live_participation": 20},
        "utporul": {"quizzes": 40, "three_d_tasks": 15, "games_h5p": 15, "assignments": 20, "live_participation": 10},
    }
    course_type = db.execute(text("SELECT course_type FROM courses WHERE id = :cid"),
                             {"cid": course_id}).scalar() or ""
    if course_type in TYPE_DEFAULT_WEIGHTS:
        weights.update(TYPE_DEFAULT_WEIGHTS[course_type])
    wrow = None
    if course_type:
        try:
            wrow = db.execute(text(
                "SELECT default_assessment_weights FROM type_profiles WHERE type = :t"),
                {"t": course_type}).first()
        except Exception:
            db.rollback()
            wrow = None
    if wrow is not None and wrow[0]:
        w = wrow[0]
        if isinstance(w, str):
            w = json.loads(w)
        weights.update({k: v for k, v in w.items() if isinstance(v, (int, float))})

    quiz_ids = [r[0] for r in db.query(Quiz.id).filter(
        Quiz.post_parent == course_id).all()]
    quiz_scores = []
    for qid in quiz_ids:
        attempts = (db.query(QuizAttempt)
                    .filter(QuizAttempt.quiz_id == qid,
                            QuizAttempt.user_id == user_id,
                            QuizAttempt.attempt_status == "attempt_submitted")
                    .all())
        best = 0.0
        for a in attempts:
            total = float(a.total_marks or 0)
            if total > 0:
                best = max(best, float(a.earned_marks or 0) / total * 100)
        if attempts:
            quiz_scores.append(best)

    subs = (db.query(AssignmentSubmission, Assignment)
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(Assignment.course_id == course_id,
                    AssignmentSubmission.user_id == user_id,
                    AssignmentSubmission.status == "graded")
            .all())
    assignments_by_id = {a.id: a for _, a in subs}
    subs = [sub for sub, _a in subs]
    assignment_scores = []
    for sub in subs:
        assignment = assignments_by_id.get(sub.assignment_id)
        max_points = float(getattr(assignment, 'total_points', 0) or 0) if assignment else 0
        if max_points > 0:
            assignment_scores.append(
                float(sub.grade if sub.grade is not None else 0) / max_points * 100)

    # ---- scorable items (v2.0 §5): per-item best score × weight, practice
    # items excluded, bucketed into games_h5p (H5P/games) or three_d_tasks
    # (labs / 3D tasks) per app/schemas/scorable.KIND_BUCKET.
    from app.schemas.scorable import KIND_BUCKET, best_item_score
    declared = []
    for q in db.query(Quiz).filter(Quiz.post_parent == course_id).all():
        for m in (q.interactive_modules or []):
            declared.append(m)
    graded_items = [m for m in declared if not m.get("practice_only")]
    bucket_acc = {"games_h5p": [0.0, 0.0], "three_d_tasks": [0.0, 0.0]}  # [weighted sum, weight]
    items_with_results = 0
    for m in graded_items:
        res = best_item_score(db, m, user_id)
        if not res or res[1] <= 0:
            continue
        pct = res[0] / res[1] * 100.0
        w = float(m.get("weight", 1.0) or 0.0)
        if w <= 0:
            continue
        b = KIND_BUCKET.get(m.get("kind"), "games_h5p")
        bucket_acc[b][0] += pct * w
        bucket_acc[b][1] += w
        items_with_results += 1
    module_avg = (round(bucket_acc["games_h5p"][0] / bucket_acc["games_h5p"][1], 1)
                  if bucket_acc["games_h5p"][1] else None)
    three_d_avg = (round(bucket_acc["three_d_tasks"][0] / bucket_acc["three_d_tasks"][1], 1)
                   if bucket_acc["three_d_tasks"][1] else None)

    # ---- live participation (§5.3): share of this course's ENDED classes
    # the learner was marked present in. None when no class has ended.
    live_avg = None
    ended = []
    try:
        from app.models.live_class import LiveClass, LiveClassAttendance, LiveClassStatus
        ended = [c.id for c in db.query(LiveClass)
                 .filter(LiveClass.course_id == course_id, LiveClass.status == LiveClassStatus.ENDED,
                         LiveClass.deleted_at.is_(None)).all()]
        if ended:
            present = (db.query(LiveClassAttendance)
                       .filter(LiveClassAttendance.class_id.in_(ended),
                               LiveClassAttendance.user_id == user_id,
                               LiveClassAttendance.present == True).count())  # noqa: E712
            live_avg = round(present / len(ended) * 100.0, 1)
    except Exception:
        live_avg = None

    def avg(xs):
        return round(sum(xs) / len(xs), 1) if xs else None

    quiz_avg = avg(quiz_scores)
    assign_avg = avg(assignment_scores)
    # Weighted roll-up per type profile (v2.0 §5.3); components with no
    # results redistribute their weight proportionally.
    components = {
        "quizzes": quiz_avg, "assignments": assign_avg, "games_h5p": module_avg,
        "three_d_tasks": three_d_avg, "live_participation": live_avg,
    }
    live_w = sum(float(weights.get(k, 0) or 0) for k, v in components.items() if v is not None)
    if live_w > 0:
        cumulative = round(sum(float(v) * float(weights.get(k, 0) or 0)
                               for k, v in components.items() if v is not None) / live_w, 1)
    else:
        cumulative = 0.0

    def pct(k):
        return f"{int(weights.get(k, 0) or 0)}%"

    return {
        "course_id": course_id,
        "user_id": user_id,
        "course_type": course_type,
        "weights": {k: int(weights.get(k, 0) or 0) for k in components},
        "breakdown": {
            "quizzes": {"average": quiz_avg,
                        "graded_quizzes": len(quiz_scores), "weight": pct("quizzes")},
            "assignments": {"average": assign_avg,
                            "graded_submissions": len(assignment_scores),
                            "weight": pct("assignments")},
            "interactive_modules": {"average": module_avg,
                                    "modules_declared": len(graded_items),
                                    "modules_with_results": items_with_results,
                                    "practice_only": len(declared) - len(graded_items),
                                    "weight": pct("games_h5p")},
            "three_d_tasks": {"average": three_d_avg, "weight": pct("three_d_tasks")},
            "live_participation": {"average": live_avg, "classes_ended": len(ended),
                                   "weight": pct("live_participation")},
        },
        "cumulative_grade": cumulative,
        "letter": ("A" if cumulative >= 90 else "B" if cumulative >= 75 else
                   "C" if cumulative >= 60 else "D" if cumulative >= 40 else "F"),
    }


# -------------------------------------------------------------------- at-risk

STALL_DAYS = 7
LOW_VELOCITY_PCT_PER_WEEK = 5.0
QUIZ_FAIL_THRESHOLD = 2
POINTS = {"stalled": 45, "low_velocity": 25, "quiz_struggle": 30}


def _compute_risk(db: Session, course: Course, enrollment: Enrollment,
                  now: datetime) -> dict:
    reasons: list[str] = []
    score = 0

    last_stmt = (db.query(XapiStatement)
                 .filter(XapiStatement.actor_user_id == enrollment.user_id,
                         XapiStatement.context.contains({"course_id": course.id}))
                 .order_by(XapiStatement.stored_at.desc()).first())
    reference_dt = last_stmt.stored_at.replace(tzinfo=timezone.utc) if last_stmt and last_stmt.stored_at else None
    enrolled_dt = enrollment.enrollment_date
    if enrolled_dt and enrolled_dt.tzinfo is None:
        enrolled_dt = enrolled_dt.replace(tzinfo=timezone.utc)

    days_since_activity = None
    if reference_dt:
        days_since_activity = (now - reference_dt).days
        if days_since_activity >= STALL_DAYS and enrollment.enrollment_status != "completed":
            score += POINTS["stalled"]
            reasons.append(
                f"stalled: no recorded activity for {days_since_activity} days "
                f"(threshold {STALL_DAYS})")
    elif enrolled_dt and not reference_dt:
        days_since_activity = (now - enrolled_dt).days
        if days_since_activity >= STALL_DAYS and enrollment.enrollment_status != "completed":
            score += POINTS["stalled"]
            reasons.append(
                f"never started: enrolled {days_since_activity} days ago with "
                f"zero recorded activity (threshold {STALL_DAYS})")

    progress = int(enrollment.course_progress_percentage or 0)
    if enrolled_dt and enrollment.enrollment_status != "completed":
        weeks = max((now - enrolled_dt).days / 7.0, 0.25)
        velocity = progress / weeks
        if velocity < LOW_VELOCITY_PCT_PER_WEEK and progress < 100:
            score += POINTS["low_velocity"]
            reasons.append(
                f"low velocity: {velocity:.1f}%/week (needs "
                f"{LOW_VELOCITY_PCT_PER_WEEK}%/week) at {progress}% complete")

    attempts = (db.query(QuizAttempt)
                .filter(QuizAttempt.course_id == course.id,
                        QuizAttempt.user_id == enrollment.user_id,
                        QuizAttempt.attempt_status == "attempt_submitted")
                .order_by(QuizAttempt.attempt_started_at.desc())
                .all())
    fails_by_quiz: dict[int, int] = {}
    for a in attempts:
        earned = float(a.earned_marks or 0)
        total = float(a.total_marks or 0)
        pct = (earned / total * 100) if total > 0 else 0
        if pct < 80:
            fails_by_quiz[a.quiz_id] = fails_by_quiz.get(a.quiz_id, 0) + 1
    struggling = {qid: n for qid, n in fails_by_quiz.items() if n >= QUIZ_FAIL_THRESHOLD}
    if struggling:
        score += POINTS["quiz_struggle"]
        reasons.append(
            f"quiz struggle: {len(struggling)} quiz(es) with >= {QUIZ_FAIL_THRESHOLD} "
            f"failing attempts (quizzes {sorted(struggling)})")

    # v2.0 §9.5: weak concepts in the LEARNER-scoped mastery graph (evidence
    # from any course counts — that is the cross-type point).
    try:
        from app.services.mastery_service import weak_concepts
        weak = [w for w in weak_concepts(db, enrollment.user_id, limit=50) if w["confidence"] >= 0.4]
        if len(weak) >= 3:
            score += 20
            reasons.append(f"weak concepts: {len(weak)} below 50% mastery "
                           f"(e.g. {', '.join(w['concept'] for w in weak[:3])})")
    except Exception:
        pass

    score = min(score, 100)
    severity = ("high" if score >= 60 else "medium" if score >= 30 else "low")
    return {
        "user_id": enrollment.user_id,
        "risk_score": score,
        "severity": severity,
        "reasons": reasons,
    }


@router.get("/analytics/courses/{course_id}/at-risk")
def at_risk(
    course_id: int,
    persist: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Blueprint §3.6 'predictive at-risk flagging with explainability' —
    rule-based, no black box: every flag ships the numbers behind it.
    Recompute is idempotent (UNIQUE course+student upsert into
    student_risk_flags). No xAPI history yet → the stalled rule falls back
    to enrollment age, which is why emitters were wired into lesson/watch
    events."""
    course = _course_or_404(db, course_id)
    _require_course_owner(current_user, course)

    enrollments = (db.query(Enrollment)
                   .filter(Enrollment.course_id == course_id,
                           Enrollment.enrollment_status.in_(["enrolled", "completed"]))
                   .all())
    now = datetime.now(timezone.utc)
    flagged = []
    for enrollment in enrollments:
        result = _compute_risk(db, course, enrollment, now)
        if result["severity"] == "low" and not result["reasons"]:
            continue
        flagged.append(result)
        if persist:
            existing = (db.query(StudentRiskFlag)
                        .filter(StudentRiskFlag.course_id == course_id,
                                StudentRiskFlag.user_id == enrollment.user_id)
                        .first())
            if existing:
                existing.risk_score = result["risk_score"]
                existing.severity = result["severity"]
                existing.reasons = result["reasons"]
                existing.computed_at = now
            else:
                db.add(StudentRiskFlag(
                    course_id=course_id,
                    user_id=enrollment.user_id,
                    risk_score=result["risk_score"],
                    severity=result["severity"],
                    reasons=result["reasons"],
                    computed_at=now,
                ))
    if persist:
        db.commit()

    order = {"high": 0, "medium": 1, "low": 2}
    flagged.sort(key=lambda r: (-r["risk_score"], order[r["severity"]]))
    return {
        "course_id": course_id,
        "students_scanned": len(enrollments),
        "flagged": len(flagged),
        "rules": {
            "stalled_days": STALL_DAYS,
            "low_velocity_pct_per_week": LOW_VELOCITY_PCT_PER_WEEK,
            "quiz_fail_threshold": QUIZ_FAIL_THRESHOLD,
        },
        "results": flagged,
    }
