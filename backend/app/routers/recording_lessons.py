"""Private instructor recording workbench and publication-gated learner reader."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.live_class import LiveClass
from app.models.live_class_report import ClassReport
from app.models.recording_lesson import RecordingLesson
from app.services.auth_service import AuthService
from app.services.course_access import can_edit, ADMIN_ROLES
from app.services.mastery_service import clean_concepts
from app.services import recording_lesson_service as svc, transcription_provider as provider
from app.services import assessment_studio_service as studio

router = APIRouter()


def recording_db(db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    try:
        yield db
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "The recording changed. Refresh and try again.")


def editor(db, class_id, user):
    lc = db.query(LiveClass).filter_by(id=class_id).with_for_update().first()
    if not lc or lc.deleted_at:
        raise HTTPException(404, "Class not found")
    if user.role not in ADMIN_ROLES and lc.instructor_id != user.id:
        raise HTTPException(403, "Only the class instructor or an administrator can edit this recording.")
    if not can_edit(db, db.get(Course, lc.course_id), user):
        raise HTTPException(403, "Course editing access is required to create recording lessons.")
    if not db.query(ClassReport.id).filter_by(class_id=lc.id).first():
        raise HTTPException(409, "End the class before creating a recording lesson.")
    return lc


def work(db, class_id, version=None):
    row = db.query(RecordingLesson).filter_by(class_id=class_id).first()
    if not row:
        raise HTTPException(404, "Transcribe this recording first.")
    if version is not None:
        updated = db.query(RecordingLesson).filter_by(id=row.id, version=version).update(
            {"version": version + 1}, synchronize_session=False)
        if not updated:
            raise HTTPException(409, "This recording changed. Refresh before trying again.")
        db.expire(row)
    return row


class VersionIn(BaseModel):
    version: int = Field(ge=1)


class TranscribeIn(BaseModel):
    language: Literal["auto", "en", "ta"] = "auto"
    version: int | None = Field(default=None, ge=1)


class ChapterIn(BaseModel):
    start: float = Field(ge=0, le=86400, allow_inf_nan=False)
    title: str = Field(min_length=1, max_length=100)


class SegmentIn(BaseModel):
    start: float = Field(ge=0, le=86400, allow_inf_nan=False)
    end: float = Field(ge=0, le=86400, allow_inf_nan=False)
    text: str = Field(min_length=1, max_length=5000)


class EditIn(VersionIn):
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=20, max_length=20000)
    chapters: list[ChapterIn] = Field(min_length=1, max_length=500)
    concepts: list[str] = Field(default_factory=list, max_length=20)
    segments: list[SegmentIn] | None = Field(default=None, min_length=1, max_length=20000)


@router.get("")
def recordings(db: Session = Depends(recording_db), user=Depends(AuthService.require_instructor)):
    query = db.query(LiveClass, ClassReport).join(ClassReport, ClassReport.class_id == LiveClass.id).filter(LiveClass.deleted_at.is_(None))
    if user.role not in ADMIN_ROLES:
        query = query.filter(LiveClass.instructor_id == user.id)
    rows = []
    for lc, report in query.order_by(ClassReport.generated_at.desc()).limit(200):
        if not can_edit(db, db.get(Course, lc.course_id), user):
            continue
        row = db.query(RecordingLesson).filter_by(class_id=lc.id).first()
        rows.append({"class_id": lc.id, "course_id": lc.course_id, "title": lc.title,
                     "status": row.status if row else "not_started", "lesson_id": row.lesson_id if row else None,
                     "has_recording": bool(lc.recording_video_id) and not lc.recording_deleted_at})
    return {"classes": rows, "transcription": provider.configuration()}


@router.get("/{class_id}")
def detail(class_id: int, db: Session = Depends(recording_db), user=Depends(AuthService.require_instructor)):
    lc = editor(db, class_id, user)
    row = db.query(RecordingLesson).filter_by(class_id=class_id).first()
    return {"work": svc.serialize(db, row, lc) if row else None, "transcription": provider.configuration()}


@router.post("/{class_id}/transcribe", status_code=202)
def transcribe(class_id: int, body: TranscribeIn, db: Session = Depends(recording_db), user=Depends(AuthService.require_instructor)):
    lc = editor(db, class_id, user)
    if not provider.configuration()["configured"]:
        raise HTTPException(503, provider.configuration()["note"])
    row = db.query(RecordingLesson).filter_by(class_id=class_id).first()
    if row:
        if body.version is None:
            raise HTTPException(409, "Refresh before retrying transcription.")
        row = work(db, class_id, body.version)
        if row.status not in ("failed", "queued"):
            raise HTTPException(409, "Transcription is already running or ready for review.")
    try:
        path = svc.source_for(lc, row.source_path if row else "")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if row is None:
        row = RecordingLesson(class_id=class_id, title=lc.title, source_path=str(path))
        db.add(row)
    row.language, row.status, row.error = body.language, "queued", None
    db.commit()
    return svc.serialize(db, row, lc)


@router.put("/{class_id}")
def edit(class_id: int, body: EditIn, db: Session = Depends(recording_db), user=Depends(AuthService.require_instructor)):
    lc = editor(db, class_id, user)
    row = work(db, class_id, body.version)
    if row.status != "draft":
        raise HTTPException(409, "Only unconverted drafts can be edited here. Edit created lessons in the course editor.")
    chapters = [c.model_dump() for c in body.chapters]
    if not body.title.strip() or len(body.notes.strip()) < 20 or any(not c["title"].strip() for c in chapters):
        raise HTTPException(422, "Provide a title, notes and chapter titles.")
    starts = [c["start"] for c in chapters]
    if starts != sorted(set(starts)) or starts[-1] > row.segments[-1]["end"]:
        raise HTTPException(422, "Chapter times must increase and stay within the recording.")
    if any(not c.strip() or len(c) > 80 for c in body.concepts):
        raise HTTPException(422, "Concepts must contain one to eighty characters.")
    if body.segments is not None:
        segments = [s.model_dump() for s in body.segments]
        if len(segments) != len(row.segments) or any(s["start"] != old["start"] or s["end"] != old["end"] or not s["text"].strip() for s, old in zip(segments, row.segments)) or sum(len(s["text"]) for s in segments) > 400000:
            raise HTTPException(422, "Correct transcript text without changing its segment timestamps.")
        row.segments = segments
    row.title, row.notes, row.chapters, row.concepts = body.title.strip(), body.notes.strip(), chapters, clean_concepts(body.concepts)
    db.commit()
    return svc.serialize(db, row, lc)


@router.post("/{class_id}/create-lesson")
def create(class_id: int, body: VersionIn, db: Session = Depends(recording_db), user=Depends(AuthService.require_instructor)):
    lc = editor(db, class_id, user)
    row = work(db, class_id, body.version)
    if row.status not in ("draft", "lesson_created"):
        raise HTTPException(409, "Wait for transcription and review the draft first.")
    if len(row.notes.strip()) < 20:
        raise HTTPException(422, "Add at least twenty characters of reviewed lesson notes.")
    svc.create_lesson(db, row, lc, user)
    db.commit()
    return svc.serialize(db, row, lc)


@router.post("/{class_id}/assessment-drafts")
def questions(class_id: int, body: VersionIn, db: Session = Depends(recording_db), user=Depends(AuthService.require_instructor)):
    lc = editor(db, class_id, user)
    row = work(db, class_id, body.version)
    if row.status not in ("draft", "lesson_created"):
        raise HTTPException(409, "Review the transcript before creating assessment drafts.")
    if not row.question_ids:
        suggestions = svc.question_suggestions(row)
        if not suggestions:
            raise HTTPException(422, "Add a concept that appears in the transcript to suggest an excerpt question.")
        row.question_ids = [studio.save_draft(db, lc.course_id, user.id, s, s["concept"], "practice").id for s in suggestions]
    db.commit()
    return svc.serialize(db, row, lc)


@router.get("/{class_id}/reader")
def reader(class_id: int, db: Session = Depends(recording_db), user=Depends(AuthService.get_current_active_user)):
    lc = db.get(LiveClass, class_id)
    row = db.query(RecordingLesson).filter_by(class_id=class_id).first()
    if not lc or lc.deleted_at or not row:
        raise HTTPException(404, "Recording lesson not found")
    course = db.get(Course, lc.course_id)
    staff = user.role in ADMIN_ROLES or (user.role == "instructor" and lc.instructor_id == user.id and can_edit(db, course, user))
    if not staff:
        lesson = db.get(Lesson, row.lesson_id) if row.lesson_id else None
        enrolled = db.query(Enrollment.id).filter(Enrollment.course_id == lc.course_id, Enrollment.user_id == user.id,
                                                 Enrollment.enrollment_status.in_(["enrolled", "completed"])).first()
        if user.role != "student" or not enrolled or not lesson or lesson.post_parent != lc.course_id or lesson.post_status not in ("publish", "published") or course.post_status not in ("publish", "published"):
            raise HTTPException(403, "An enrolled learner can open this after the lesson is published.")
    # Never expose source_path, question answer keys or private processing errors.
    return {"class_id": class_id, "course_id": lc.course_id, "title": row.title, "notes": row.notes,
            "segments": row.segments, "chapters": row.chapters, "language": row.language,
            "recording_available": bool(lc.recording_video_id) and not lc.recording_deleted_at}
