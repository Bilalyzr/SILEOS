"""Private campus learning has no public catalog, file paths, or legacy LMS grants."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.campus_operations import (
    CampusLearningCourse,
    CampusLesson,
    CampusLessonProgress,
    CampusResource,
)
from app.models.institution import (
    InstitutionBatch,
    InstitutionBatchMember,
    InstitutionMember,
)
from app.models.user import User
from app.schemas.campus_operations import (
    CampusCourseDraft,
    CampusLessonDraft,
    CampusPublish,
)
from app.services.auth_service import AuthService
from app.services import institution_service as svc

router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


def allowed_courses(db, iid, actor):
    q = db.query(CampusLearningCourse).filter_by(institution_id=iid)
    if actor.role not in svc.STAFF:
        batches = db.query(InstitutionBatchMember.batch_id).filter_by(
            member_id=actor.id
        )
        q = q.filter(
            CampusLearningCourse.published.is_(True),
            (CampusLearningCourse.batch_id.is_(None))
            | CampusLearningCourse.batch_id.in_(batches),
        )
    return q


def course_scope(db, iid, cid, user, write=False):
    _, actor = svc.scope(db, iid, user, svc.STAFF if write else None, lock=write)
    row = allowed_courses(db, iid, actor).filter_by(id=cid).first()
    if not row:
        raise HTTPException(404, "Campus course not found.")
    if write and actor.role not in svc.MANAGERS and row.created_by != user.id:
        raise HTTPException(
            403, "Only the course author or campus managers can edit this course."
        )
    return row, actor


def summary(db, row, actor, user):
    lesson_ids = [i for i, in db.query(CampusLesson.id).filter_by(course_id=row.id)]
    completed = (
        db.query(CampusLessonProgress)
        .filter(
            CampusLessonProgress.lesson_id.in_(lesson_ids),
            CampusLessonProgress.member_id == actor.id,
        )
        .count()
    )
    return {
        "id": row.id,
        "title": row.title,
        "summary": row.summary,
        "batch_id": row.batch_id,
        "published": row.published,
        "can_edit": actor.role in svc.STAFF
        and (actor.role in svc.MANAGERS or row.created_by == user.id),
        "lessons": len(lesson_ids),
        "completed": completed,
    }


@router.get("/{institution_id}/learning-courses")
def courses(institution_id: int, db: Session = Depends(get_db), user=Current):
    _, actor = svc.scope(db, institution_id, user)
    return [
        summary(db, c, actor, user)
        for c in allowed_courses(db, institution_id, actor)
        .order_by(CampusLearningCourse.id.desc())
        .limit(200)
    ]


@router.post("/{institution_id}/learning-courses", status_code=201)
def create(
    institution_id: int,
    data: CampusCourseDraft,
    db: Session = Depends(get_db),
    user=Current,
):
    inst, _ = svc.scope(db, institution_id, user, svc.STAFF, lock=True)
    svc.verified(user)
    svc.capacity(db, inst, "courses")
    if (
        data.batch_id
        and not db.query(InstitutionBatch)
        .filter_by(id=data.batch_id, institution_id=institution_id)
        .first()
    ):
        raise HTTPException(404, "Batch not found.")
    row = CampusLearningCourse(
        institution_id=institution_id, **data.model_dump(), created_by=user.id
    )
    db.add(row)
    svc.audit(db, institution_id, user, "campus_course.created", data.title)
    svc.save(db)
    return {"id": row.id}


@router.get("/{institution_id}/learning-courses/{course_id}")
def detail(
    institution_id: int, course_id: int, db: Session = Depends(get_db), user=Current
):
    row, actor = course_scope(db, institution_id, course_id, user)
    result = summary(db, row, actor, user)
    result["content"] = [
        {
            "id": l.id,
            "title": l.title,
            "body": l.body,
            "resource_id": l.resource_id,
            "completed": bool(
                db.query(CampusLessonProgress)
                .filter_by(lesson_id=l.id, member_id=actor.id)
                .first()
            ),
        }
        for l in db.query(CampusLesson)
        .filter_by(course_id=row.id)
        .order_by(CampusLesson.position)
    ]
    return result


def resource_check(db, row, resource_id):
    if resource_id:
        resource = (
            db.query(CampusResource)
            .filter_by(id=resource_id, institution_id=row.institution_id)
            .first()
        )
        if not resource or (
            resource.batch_id is not None and resource.batch_id != row.batch_id
        ):
            raise HTTPException(
                422, "Choose a resource available to this course's audience."
            )


@router.post("/{institution_id}/learning-courses/{course_id}/lessons", status_code=201)
def add_lesson(
    institution_id: int,
    course_id: int,
    data: CampusLessonDraft,
    db: Session = Depends(get_db),
    user=Current,
):
    row, _ = course_scope(db, institution_id, course_id, user, write=True)
    count = db.query(CampusLesson).filter_by(course_id=row.id).count()
    if count >= 100:
        raise HTTPException(409, "A campus course supports up to 100 lessons.")
    resource_check(db, row, data.resource_id)
    lesson = CampusLesson(course_id=row.id, position=count, **data.model_dump())
    db.add(lesson)
    svc.audit(db, institution_id, user, "campus_lesson.created", data.title)
    svc.save(db)
    return {"id": lesson.id}


@router.put("/{institution_id}/learning-courses/{course_id}/lessons/{lesson_id}")
def edit_lesson(
    institution_id: int,
    course_id: int,
    lesson_id: int,
    data: CampusLessonDraft,
    db: Session = Depends(get_db),
    user=Current,
):
    row, _ = course_scope(db, institution_id, course_id, user, write=True)
    lesson = db.query(CampusLesson).filter_by(id=lesson_id, course_id=row.id).first()
    if not lesson:
        raise HTTPException(404, "Lesson not found.")
    resource_check(db, row, data.resource_id)
    for k, v in data.model_dump().items():
        setattr(lesson, k, v)
    svc.audit(db, institution_id, user, "campus_lesson.updated", data.title)
    svc.save(db)
    return {"saved": True}


@router.put("/{institution_id}/learning-courses/{course_id}/publish")
def publish(
    institution_id: int,
    course_id: int,
    data: CampusPublish,
    db: Session = Depends(get_db),
    user=Current,
):
    row, _ = course_scope(db, institution_id, course_id, user, write=True)
    if (
        data.published
        and not db.query(CampusLesson).filter_by(course_id=row.id).first()
    ):
        raise HTTPException(422, "Add a lesson before publishing.")
    row.published = data.published
    svc.audit(
        db,
        institution_id,
        user,
        "campus_course.published" if data.published else "campus_course.unpublished",
        row.title,
    )
    svc.save(db)
    return {"published": row.published}


@router.put(
    "/{institution_id}/learning-courses/{course_id}/lessons/{lesson_id}/complete"
)
def complete(
    institution_id: int,
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    _, actor = svc.scope(db, institution_id, user, lock=True)
    row, _ = course_scope(db, institution_id, course_id, user)
    if not row.published:
        raise HTTPException(
            409, "Publish the course before recording learning progress."
        )
    if not db.query(CampusLesson).filter_by(id=lesson_id, course_id=row.id).first():
        raise HTTPException(404, "Lesson not found.")
    progress = (
        db.query(CampusLessonProgress)
        .filter_by(lesson_id=lesson_id, member_id=actor.id)
        .first()
    )
    if not progress:
        db.add(CampusLessonProgress(lesson_id=lesson_id, member_id=actor.id))
        svc.save(db)
    return {"completed": True}


@router.get("/{institution_id}/learning-courses/{course_id}/progress")
def progress(
    institution_id: int, course_id: int, db: Session = Depends(get_db), user=Current
):
    row, actor = course_scope(db, institution_id, course_id, user)
    if actor.role not in svc.STAFF:
        raise HTTPException(403, "Campus staff access required.")
    q = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.status == "active",
            InstitutionMember.role == "student",
        )
    )
    if row.batch_id:
        q = q.join(
            InstitutionBatchMember,
            InstitutionBatchMember.member_id == InstitutionMember.id,
        ).filter(InstitutionBatchMember.batch_id == row.batch_id)
    lessons = [i for i, in db.query(CampusLesson.id).filter_by(course_id=row.id)]
    return [
        {
            "name": u.display_name,
            "member_id": m.id,
            "completed": db.query(CampusLessonProgress)
            .filter(
                CampusLessonProgress.member_id == m.id,
                CampusLessonProgress.lesson_id.in_(lessons),
            )
            .count(),
            "lessons": len(lessons),
        }
        for m, u in q
    ]
