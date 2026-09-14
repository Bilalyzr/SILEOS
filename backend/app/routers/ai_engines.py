"""AI layer completion (v2.0 §9 — WP7), mounted at /api/v1/ai next to ai_tutor.py.

Engine B  POST /adaptive-lesson/{course_id}        depth-adaptive mini-lesson (recover|consolidate|extend) — LLM
Engine C  POST /tutor/check-question               mastery-calibrated check question — LLM
          POST /tutor/escalate                     hand-off to the instructor WITH context — no LLM
          GET  /tutor/escalations  POST /tutor/escalations/{id}/reply
Engine D  GET  /review-queue                       ai-draft questions + auto-flagged items + open reports/escalations — derived
          POST /review-queue/questions/{id}/approve|reject
          POST /error-reports  GET /error-reports  POST /error-reports/{id}/resolve
All LLM calls: honest 503 without GLM_API_KEY, audited AiJob, output is a draft.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ai_layer import ContentErrorReport, TutorEscalation
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.sileos_pack import AiJob, BankQuestion, QuestionBank
from app.models.user import User
from app.services import ai_layer_service as svc
from app.services.auth_service import AuthService
from app.services.llm_provider import call_glm, glm_model, llm_configured, missing_key_detail
from app.services.notification_service import create_notification

router = APIRouter()

ADMIN_ROLES = ("admin", "superadmin")


def _course(db: Session, course_id: int) -> Course:
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Course not found")
    return c


def _is_owner(course: Course, user: User) -> bool:
    return course.post_author == user.id or user.role in ADMIN_ROLES


def _enrolled_or_owner(db: Session, course: Course, user: User) -> None:
    if _is_owner(course, user):
        return
    ok = db.query(Enrollment.id).filter(Enrollment.user_id == user.id, Enrollment.course_id == course.id,
                                        Enrollment.enrollment_status.in_(["enrolled", "completed"])).first()
    if not ok:
        raise HTTPException(status_code=403, detail="Enrol in the course first")


def _require_llm(feature: str) -> None:
    if not llm_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=missing_key_detail(feature))


def _job(db: Session, user_id: int, job_type: str, input_json: dict) -> AiJob:
    job = AiJob(created_by=user_id, job_type=job_type, status="pending", model=glm_model(), input_json=input_json)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _finish(db: Session, job: AiJob, output: Optional[dict] = None, error: Optional[str] = None) -> None:
    job.status = "failed" if error else "done"
    job.error = (error or "")[:2000]
    job.output_json = output or {}
    job.finished_at = svc.utcnow()
    db.commit()


# ---------------------------------------------------------------- Engine B

class AdaptiveIn(BaseModel):
    mode: Optional[str] = None
    concept: Optional[str] = Field(default=None, max_length=80)
    student_id: Optional[int] = None


@router.post("/adaptive-lesson/{course_id}")
async def adaptive_lesson(course_id: int, body: AdaptiveIn, db: Session = Depends(get_db),
                          current_user: User = Depends(AuthService.get_current_active_user)):
    course = _course(db, course_id)
    _enrolled_or_owner(db, course, current_user)
    target = current_user.id
    if body.student_id and body.student_id != current_user.id:
        if not _is_owner(course, current_user):
            raise HTTPException(status_code=403, detail="Only the course owner can target another learner")
        target = body.student_id
    if body.mode and body.mode not in svc.MODES:
        raise HTTPException(status_code=422, detail=f"mode must be one of {list(svc.MODES)}")
    state = svc.learner_concept_state(db, target, body.concept)
    mode = body.mode or svc.choose_mode(state["estimate"])
    _require_llm("Adaptive lesson")
    job = _job(db, current_user.id, "adaptive_lesson",
               {"course_id": course_id, "student_id": target, "mode": mode, "concept": state["concept"]})
    prompt = (f"COURSE: {course.post_title}\nLANGUAGE: {course.course_language or 'English'}\nMODE: {mode}\nCONCEPT: {state['concept'] or 'the course core idea'}\n"
              f"LEARNER MASTERY ESTIMATE: {state['estimate'] if state['estimate'] is not None else 'unknown'} "
              f"(weak concepts: {', '.join(state['weak']) or 'none known'})\nMATERIAL:\n{svc.course_material(db, course_id)}")
    try:
        data = svc.parse_json_object(call_glm(svc.ADAPT_SYSTEM, prompt, feature="Adaptive lesson"))
    except Exception as exc:
        _finish(db, job, error=str(exc))
        raise HTTPException(status_code=502, detail=f"AI provider failed: {str(exc)[:200]}")
    data.setdefault("mode", mode)
    data.setdefault("concept", state["concept"])
    _finish(db, job, {"title": data.get("title"), "sections": len(data.get("sections") or [])})
    return {"job_id": job.id, "mode": mode, "concept": state["concept"], "estimate": state["estimate"],
            "lesson": data, "note": "Draft for this learner only — not added to the curriculum."}


# ---------------------------------------------------------------- Engine C

class CheckIn(BaseModel):
    course_id: int
    concept: Optional[str] = Field(default=None, max_length=80)


@router.post("/tutor/check-question")
async def check_question(body: CheckIn, db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.get_current_active_user)):
    course = _course(db, body.course_id)
    _enrolled_or_owner(db, course, current_user)
    state = svc.learner_concept_state(db, current_user.id, body.concept)
    _require_llm("Check question")
    job = _job(db, current_user.id, "check_question", {"course_id": course.id, "concept": state["concept"], "level": state["level"]})
    prompt = (f"COURSE: {course.post_title}\nLANGUAGE: {course.course_language or 'English'}\nCONCEPT: {state['concept'] or 'a core idea of the course'}\n"
              f"DIFFICULTY: {state['level']}\nMATERIAL:\n{svc.course_material(db, course.id, limit=25, chars=400)}")
    try:
        data = svc.parse_json_object(call_glm(svc.CHECK_SYSTEM, prompt, feature="Tutor check question"))
    except Exception as exc:
        _finish(db, job, error=str(exc))
        raise HTTPException(status_code=502, detail=f"AI provider failed: {str(exc)[:200]}")
    _finish(db, job, {"kind": data.get("kind")})
    return {"job_id": job.id, "concept": state["concept"], "level": state["level"], "check": data}


class EscalateIn(BaseModel):
    course_id: int
    question: str = Field(min_length=3, max_length=2000)
    history: List[Dict[str, Any]] = Field(default_factory=list, max_length=12)
    lesson_id: Optional[int] = None


@router.post("/tutor/escalate", status_code=201)
async def escalate(body: EscalateIn, db: Session = Depends(get_db),
                   current_user: User = Depends(AuthService.get_current_active_user)):
    course = _course(db, body.course_id)
    _enrolled_or_owner(db, course, current_user)
    history = [{"role": str(h.get("role", ""))[:12], "content": str(h.get("content", ""))[:1000]} for h in body.history[-8:]]
    try:
        from app.services.mastery_service import weak_concepts
        weak = [w["concept"] for w in weak_concepts(db, current_user.id, limit=5)]
    except Exception:
        weak = []
    esc = TutorEscalation(course_id=course.id, student_id=current_user.id, instructor_id=course.post_author,
                          question=body.question.strip(), context={"history": history, "lesson_id": body.lesson_id, "weak_concepts": weak})
    db.add(esc)
    db.commit()
    db.refresh(esc)
    try:
        create_notification(db, user_id=course.post_author, type="tutor_escalation",
                            title=f"Learner question in {course.post_title}",
                            message=body.question.strip()[:300], link="/instructor/review-queue", related_id=esc.id)
    except Exception:
        pass
    return svc.escalation_dict(esc)


@router.get("/tutor/escalations")
async def list_escalations(status_filter: Optional[str] = Query(default=None, alias="status"),
                           db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    q = db.query(TutorEscalation)
    if current_user.role in ("instructor",) or current_user.role in ADMIN_ROLES:
        if current_user.role not in ADMIN_ROLES:
            q = q.filter(TutorEscalation.instructor_id == current_user.id)
    else:
        q = q.filter(TutorEscalation.student_id == current_user.id)
    if status_filter in ("open", "answered"):
        q = q.filter(TutorEscalation.status == status_filter)
    rows = q.order_by(TutorEscalation.id.desc()).limit(200).all()
    names = {u.id: u.display_name for u in db.query(User).filter(User.id.in_({r.student_id for r in rows} or {0})).all()}
    return {"escalations": [{**svc.escalation_dict(r), "student_name": names.get(r.student_id)} for r in rows]}


class ReplyIn(BaseModel):
    reply: str = Field(min_length=1, max_length=4000)


@router.post("/tutor/escalations/{esc_id}/reply")
async def reply_escalation(esc_id: int, body: ReplyIn, db: Session = Depends(get_db),
                           current_user: User = Depends(AuthService.get_current_active_user)):
    esc = db.query(TutorEscalation).filter(TutorEscalation.id == esc_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalation not found")
    if esc.instructor_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your learner")
    esc.instructor_reply = body.reply.strip()
    esc.status = "answered"
    esc.answered_at = svc.utcnow()
    db.commit()
    try:
        create_notification(db, user_id=esc.student_id, type="tutor_escalation_reply", title="Your instructor replied",
                            message=body.reply.strip()[:300], link=f"/courses/{esc.course_id}", related_id=esc.id)
    except Exception:
        pass
    return svc.escalation_dict(esc)


# ---------------------------------------------------------------- Engine D

KINDS = ("quiz_question", "lesson", "bank_question", "other")


class ErrorReportIn(BaseModel):
    course_id: int
    kind: str
    ref_id: Optional[int] = None
    message: str = Field(min_length=5, max_length=2000)


@router.post("/error-reports", status_code=201)
async def report_error(body: ErrorReportIn, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.get_current_active_user)):
    if body.kind not in KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {list(KINDS)}")
    course = _course(db, body.course_id)
    _enrolled_or_owner(db, course, current_user)
    rep = ContentErrorReport(reporter_id=current_user.id, course_id=course.id, instructor_id=course.post_author,
                             kind=body.kind, ref_id=body.ref_id, message=body.message.strip())
    db.add(rep)
    db.commit()
    db.refresh(rep)
    try:
        create_notification(db, user_id=course.post_author, type="content_error_report",
                            title=f"Content error reported in {course.post_title}", message=body.message.strip()[:300],
                            link="/instructor/review-queue", related_id=rep.id)
    except Exception:
        pass
    return svc.report_dict(rep)


@router.get("/error-reports")
async def list_error_reports(status_filter: Optional[str] = Query(default=None, alias="status"),
                             db: Session = Depends(get_db),
                             current_user: User = Depends(AuthService.get_current_active_user)):
    q = db.query(ContentErrorReport)
    if current_user.role in ADMIN_ROLES:
        pass
    elif current_user.role == "instructor":
        q = q.filter(ContentErrorReport.instructor_id == current_user.id)
    else:
        q = q.filter(ContentErrorReport.reporter_id == current_user.id)
    if status_filter in ("open", "resolved", "dismissed"):
        q = q.filter(ContentErrorReport.status == status_filter)
    return {"reports": [svc.report_dict(r) for r in q.order_by(ContentErrorReport.id.desc()).limit(200).all()]}


class ResolveIn(BaseModel):
    status: str
    resolution: Optional[str] = Field(default=None, max_length=2000)


@router.post("/error-reports/{report_id}/resolve")
async def resolve_error_report(report_id: int, body: ResolveIn, db: Session = Depends(get_db),
                               current_user: User = Depends(AuthService.get_current_active_user)):
    rep = db.query(ContentErrorReport).filter(ContentErrorReport.id == report_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Report not found")
    if rep.instructor_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your course")
    if body.status not in ("resolved", "dismissed"):
        raise HTTPException(status_code=422, detail="status must be resolved or dismissed")
    rep.status = body.status
    rep.resolution = (body.resolution or "").strip() or None
    rep.resolved_at = svc.utcnow()
    db.commit()
    try:
        create_notification(db, user_id=rep.reporter_id, type="content_error_resolved",
                            title=f"Your report was {body.status}", message=rep.resolution or "", link=f"/courses/{rep.course_id}",
                            related_id=rep.id)
    except Exception:
        pass
    return svc.report_dict(rep)


@router.get("/review-queue/counts")
async def review_queue_counts(db: Session = Depends(get_db),
                              current_user: User = Depends(AuthService.require_instructor)):
    """Cheap badge counts for the sidebar (R2): open escalations, open error
    reports, AI drafts. Item-statistics flags are excluded on purpose — they
    need a full scan and belong on the queue page itself."""
    admin = current_user.role in ADMIN_ROLES
    rq = db.query(ContentErrorReport).filter(ContentErrorReport.status == "open")
    eq = db.query(TutorEscalation).filter(TutorEscalation.status == "open")
    if not admin:
        rq = rq.filter(ContentErrorReport.instructor_id == current_user.id)
        eq = eq.filter(TutorEscalation.instructor_id == current_user.id)
    drafts = len(svc.ai_draft_queue(db, current_user.id))
    esc, rep = eq.count(), rq.count()
    return {"escalations": esc, "error_reports": rep, "ai_drafts": drafts, "total": esc + rep + drafts}


@router.get("/review-queue")
async def review_queue(db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.require_instructor)):
    admin = current_user.role in ADMIN_ROLES
    drafts = svc.ai_draft_queue(db, current_user.id)
    flagged = svc.flagged_items(db, current_user.id, admin=admin)
    rq = db.query(ContentErrorReport).filter(ContentErrorReport.status == "open")
    eq = db.query(TutorEscalation).filter(TutorEscalation.status == "open")
    if not admin:
        rq = rq.filter(ContentErrorReport.instructor_id == current_user.id)
        eq = eq.filter(TutorEscalation.instructor_id == current_user.id)
    return {"ai_drafts": drafts, "flagged_items": flagged,
            "error_reports": [svc.report_dict(r) for r in rq.order_by(ContentErrorReport.id.desc()).limit(100).all()],
            "escalations": [svc.escalation_dict(e) for e in eq.order_by(TutorEscalation.id.desc()).limit(100).all()],
            "counts": {"ai_drafts": len(drafts), "flagged_items": len(flagged), "error_reports": rq.count(), "escalations": eq.count()},
            "llm_configured": llm_configured()}


@router.get("/review-queue/integrity")
async def integrity_lane(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.require_instructor)):
    """R8: attempts with integrity flags across the instructor's courses (derived)."""
    from datetime import timedelta
    from app.models.quiz import Quiz, QuizAttempt
    from app.services.course_access import collaborated_course_ids
    admin = current_user.role in ADMIN_ROLES
    since = svc.utcnow() - timedelta(days=days)
    q = (db.query(QuizAttempt, Quiz, Course, User).join(Quiz, Quiz.id == QuizAttempt.quiz_id)
         .join(Course, Course.id == QuizAttempt.course_id).join(User, User.id == QuizAttempt.user_id)
         .filter(QuizAttempt.attempt_started_at >= since))
    if not admin:
        from sqlalchemy import or_
        q = q.filter(or_(Course.post_author == current_user.id, Course.id.in_(collaborated_course_ids(db, current_user.id))))
    out = []
    for a, quiz, course, u in q.order_by(QuizAttempt.attempt_id.desc()).limit(2000).all():
        integ = (a.attempt_info or {}).get("integrity") or {}
        tab, paste, fs = int(integ.get("tab_hidden") or 0), int(integ.get("paste") or 0), int(integ.get("fullscreen_exit") or 0)
        if tab >= 3 or paste >= 1 or fs >= 2:
            out.append({"attempt_id": a.attempt_id, "quiz_id": quiz.id, "quiz_title": quiz.post_title, "course_id": course.id,
                        "course_title": course.post_title, "user_id": u.id, "name": u.display_name, "tab_hidden": tab, "paste": paste,
                        "fullscreen_exit": fs, "earned": float(a.earned_marks or 0), "total": float(a.total_marks or 0),
                        "started_at": a.attempt_started_at.isoformat() if a.attempt_started_at else None})
    return {"days": days, "attempts": out}


def _owned_quiz_question(db: Session, question_id: int, user: User):
    from app.models.quiz import Quiz, QuizQuestion
    from app.services.course_access import can_edit
    row = (db.query(QuizQuestion, Quiz).join(Quiz, Quiz.id == QuizQuestion.quiz_id).filter(QuizQuestion.question_id == question_id).first())
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    qq, quiz = row
    course = db.query(Course).filter(Course.id == quiz.post_parent).first()
    if not can_edit(db, course, user):
        raise HTTPException(status_code=403, detail="Not your course")
    return qq


@router.post("/review-queue/items/{question_id}/retire")
async def retire_item(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(AuthService.require_instructor)):
    """R8: a flagged question stops appearing in NEW attempts; history is untouched."""
    qq = _owned_quiz_question(db, question_id, current_user)
    qq.is_retired = True
    db.commit()
    return {"question_id": question_id, "is_retired": True}


@router.post("/review-queue/items/{question_id}/unretire")
async def unretire_item(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(AuthService.require_instructor)):
    qq = _owned_quiz_question(db, question_id, current_user)
    qq.is_retired = False
    db.commit()
    return {"question_id": question_id, "is_retired": False}


def _owned_bank_question(db: Session, question_id: int, user: User) -> BankQuestion:
    row = (db.query(BankQuestion, QuestionBank).join(QuestionBank, QuestionBank.id == BankQuestion.bank_id)
           .filter(BankQuestion.id == question_id).first())
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    bq, bank = row
    if bank.instructor_id != user.id and user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not your bank")
    return bq


@router.post("/review-queue/questions/{question_id}/approve")
async def approve_draft(question_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.require_instructor)):
    bq = _owned_bank_question(db, question_id, current_user)
    tags = [t for t in (bq.tags or []) if t != "ai-draft"]
    if "reviewed" not in tags:
        tags.append("reviewed")
    bq.tags = tags
    db.commit()
    return {"question_id": bq.id, "tags": bq.tags, "status": "approved"}


@router.post("/review-queue/questions/{question_id}/reject")
async def reject_draft(question_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.require_instructor)):
    bq = _owned_bank_question(db, question_id, current_user)
    if "ai-draft" not in (bq.tags or []):
        raise HTTPException(status_code=409, detail="Only AI drafts can be rejected here")
    db.delete(bq)
    db.commit()
    return {"question_id": question_id, "status": "rejected"}
