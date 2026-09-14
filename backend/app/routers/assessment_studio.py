"""Course-editor Assessment Studio. No student answer-key surface."""
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.course import Course
from app.models.assessment_studio import StudioQuestion
from app.models.mastery import ConceptLink
from app.models.sileos_pack import QuestionBank, BankQuestion
from app.services.auth_service import AuthService
from app.services.course_access import can_edit, collaborated_course_ids, ADMIN_ROLES
from app.services.mastery_service import normalize_concept
from app.services import assessment_studio_service as svc

router = APIRouter()


def studio_db(db: Session = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    try:
        yield db
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Content changed during this request. Refresh and try again.")


def course_editor(db, course_id, user):
    course = db.query(Course).filter_by(id=course_id).with_for_update().first()
    if not course:
        raise HTTPException(404, "Course not found")
    if not can_edit(db, course, user):
        raise HTTPException(403, "Not your course")
    return course


def concept_name(raw):
    value = normalize_concept(raw)
    if not value or len(raw) > 80:
        raise HTTPException(422, "Enter a concept of one to eighty characters.")
    return value


class DraftIn(BaseModel):
    title: str = Field(min_length=3, max_length=3000)
    type: Literal["multiple_choice", "multiple_select", "true_false", "fill_in_blanks", "short_answer"]
    options: list[str] = Field(default_factory=list, max_length=8)
    answer: Any
    explanation: str = Field(min_length=3, max_length=5000)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    concept: str = Field(min_length=1, max_length=80)
    purpose: Literal["practice", "followup"] = "practice"
    version: int | None = None


class ActionIn(BaseModel):
    action: Literal["review", "publish", "retire"]
    version: int = Field(ge=1)
    note: str = Field(min_length=3, max_length=2000)


class LinkIn(BaseModel):
    kind: Literal["lesson", "question"]
    ref_id: int = Field(gt=0)
    concept: str = Field(min_length=1, max_length=80)


class ImportIn(BaseModel):
    bank_question_id: int = Field(gt=0)
    concept: str = Field(min_length=1, max_length=80)
    purpose: Literal["practice", "followup"] = "practice"


@router.get("/courses")
def courses(db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    query = db.query(Course)
    if user.role not in ADMIN_ROLES:
        query = query.filter(or_(Course.post_author == user.id, Course.id.in_(collaborated_course_ids(db, user.id))))
    return {"courses": [{"id": c.id, "title": c.post_title} for c in query.order_by(Course.post_title).all()]}


@router.get("/courses/{course_id}")
def detail(course_id: int, db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    course_editor(db, course_id, user)
    return svc.coverage(db, course_id)


@router.get("/bank-questions")
def reusable(db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    query = db.query(BankQuestion, QuestionBank).join(QuestionBank, QuestionBank.id == BankQuestion.bank_id)
    # Even course collaborators never inherit access to another editor's banks.
    query = query.filter(QuestionBank.instructor_id == user.id)
    return {"questions": [{"id": q.id, "bank_title": b.title, **svc.bank_content(q)} for q, b in query.order_by(BankQuestion.id.desc()).limit(500).all()]}


@router.post("/courses/{course_id}/questions", status_code=201)
def create(course_id: int, body: DraftIn, db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    course_editor(db, course_id, user)
    try:
        row = svc.save_draft(db, course_id, user.id, body.model_dump(), concept_name(body.concept), body.purpose)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    return svc.question_dict(db, row)


@router.post("/courses/{course_id}/import", status_code=201)
def import_question(course_id: int, body: ImportIn, db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    course_editor(db, course_id, user)
    result = db.query(BankQuestion, QuestionBank).join(QuestionBank, QuestionBank.id == BankQuestion.bank_id).filter(BankQuestion.id == body.bank_question_id).first()
    if not result or (result[1].instructor_id != user.id and user.role not in ADMIN_ROLES):
        raise HTTPException(404, "Reusable question not found")
    try:
        row = svc.save_draft(db, course_id, user.id, svc.bank_content(result[0]), concept_name(body.concept), body.purpose, allow_incomplete=True)
    except ValueError as exc:
        raise HTTPException(422, f"Update the source question before importing: {exc}")
    svc.audit(row, user.id, "imported", f"Snapshot of bank question {body.bank_question_id}")
    db.commit()
    return svc.question_dict(db, row)


def owned_question(db, qid, user, version):
    row = db.query(StudioQuestion).filter_by(id=qid).first()
    if not row:
        raise HTTPException(404, "Studio question not found")
    course_editor(db, row.course_id, user)
    db.refresh(row)
    if row.version != version:
        raise HTTPException(409, "This question changed. Refresh before reviewing or saving.")
    return row


@router.put("/questions/{question_id}")
def edit(question_id: int, body: DraftIn, db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    row = owned_question(db, question_id, user, body.version)
    if row.status in ("published", "retired"):
        raise HTTPException(409, "Published content is preserved. Create a new draft to revise it.")
    try:
        svc.save_draft(db, row.course_id, user.id, body.model_dump(), concept_name(body.concept), body.purpose, row)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    return svc.question_dict(db, row)


@router.post("/questions/{question_id}/action")
def action(question_id: int, body: ActionIn, db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    row = owned_question(db, question_id, user, body.version)
    if len(body.note.strip()) < 3:
        raise HTTPException(422, "Explain your review decision.")
    bq = db.query(BankQuestion).filter_by(id=row.bank_question_id).one()
    try:
        if body.action == "review":
            if row.status != "draft":
                raise HTTPException(409, "Only a draft can be reviewed.")
            svc.validate(svc.bank_content(bq))
            row.status = "reviewed"
        elif body.action == "publish":
            if row.status != "reviewed":
                raise HTTPException(409, "Review the answer, explanation and concept before publishing.")
            last_review = next((h for h in reversed(row.history or []) if h["action"] == "review"), {})
            if last_review.get("signature") != svc.content_signature(db, row):
                raise HTTPException(409, "The bank content changed after review. Edit and review this draft again.")
            snapshot = svc.publish_snapshot(db, row)
            if any(svc.prompt_key(q["title"]) == svc.prompt_key(snapshot["title"]) for q in svc.catalog(db, row.course_id)):
                raise HTTPException(409, "This prompt is already available in this course. Use a distinct question.")
            row.published_snapshot = snapshot
            row.status = "published"
            bq.tags = ["studio-published", "reviewed"]
            db.add(ConceptLink(
                kind="practice_question", ref_id=str(row.id), concept=row.concept, course_id=row.course_id, created_by=user.id))
        else:
            if row.status != "published":
                raise HTTPException(409, "Only published questions can be retired.")
            row.status = "retired"
            bq.tags = ["studio-retired"]
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    row.version += 1
    svc.audit(row, user.id, body.action, body.note.strip(), **({"signature": svc.content_signature(db, row)} if body.action == "review" else {}))
    db.commit()
    return svc.question_dict(db, row)


@router.post("/courses/{course_id}/links")
def link(course_id: int, body: LinkIn, db: Session = Depends(studio_db), user=Depends(AuthService.require_instructor)):
    course_editor(db, course_id, user)
    try:
        svc.add_link(db, course_id, user.id, body.kind, body.ref_id, concept_name(body.concept))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    return {"linked": True}
