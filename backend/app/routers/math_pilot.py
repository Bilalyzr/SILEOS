"""Bounded pilot endpoints. No anonymous learning-record collection."""
from uuid import UUID
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.user import User
from app.models.math_pilot import MathPilotPolicy, MathPilotSession, MathPilotEvent
from app.services.auth_service import AuthService
from app.services import math_pilot as svc

router = APIRouter()


def educator(user: User = Depends(AuthService.get_current_active_user)):
    if user.role not in ('instructor', 'admin', 'superadmin'):
        raise HTTPException(403, 'Educator access required.')
    return user


def transaction(response: Response, db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        yield db
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Another request updated this activity. Reload and retry.')
    except Exception:
        db.rollback()
        raise


class StartIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    course_id: int = Field(gt=0)
    acknowledge: Literal[True]


class ApprovalIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: str = Field(min_length=64, max_length=64)
    note: str = Field(min_length=10, max_length=2000)
    content_reviewed: Literal[True]
    data_arrangements_reviewed: Literal[True]


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: UUID
    version: str = Field(min_length=64, max_length=64)
    sequence: int = Field(ge=0)
    stage: Literal['predict', 'diagnose', 'build', 'transfer', 'retention']
    answers: list[Annotated[StrictInt, Field(ge=0, le=1000)]] = Field(min_length=1, max_length=2)


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: UUID
    sequence: int = Field(ge=0)
    intervention: Literal['layers', 'multiplication', 'language']
    note: str = Field(min_length=10, max_length=2000)


@router.get('/me')
def me(db: Session = Depends(transaction), user: User = Depends(AuthService.get_current_active_user)):
    courses = svc.courses(db, user)
    rows = db.query(MathPilotSession).filter(MathPilotSession.user_id == user.id,
        MathPilotSession.course_id.in_([c['id'] for c in courses]), MathPilotSession.expires_at > svc.now()).all()
    return {'catalog': svc.catalog(), 'courses': courses, 'sessions': [svc.view(r) for r in rows]}


@router.post('/sessions')
def start(body: StartIn, db: Session = Depends(transaction), user: User = Depends(AuthService.get_current_active_user)):
    return svc.start(db, body.course_id, user)


@router.post('/sessions/{session_id}/answers')
def answers(session_id: int, body: AnswerIn, db: Session = Depends(transaction), user: User = Depends(AuthService.get_current_active_user)):
    return svc.submit(db, svc.own(db, session_id, user), body, user)


@router.get('/sessions/{session_id}/export')
def export(session_id: int, db: Session = Depends(transaction), user: User = Depends(AuthService.get_current_active_user)):
    row = svc.own(db, session_id, user)
    if svc.aware(row.expires_at) <= svc.now():
        raise HTTPException(410, 'Pilot data expired.')
    return {'activity': svc.view(row), 'events': [
        {'sequence': e.sequence, 'action': e.action, 'payload': e.payload, 'result': e.result, 'created_at': svc.aware(e.created_at)}
        for e in db.query(MathPilotEvent).filter_by(session_id=row.id).order_by(MathPilotEvent.sequence).all()]}


@router.delete('/sessions/{session_id}')
def delete(session_id: int, db: Session = Depends(transaction), user: User = Depends(AuthService.get_current_active_user)):
    svc.erase(db, svc.own(db, session_id, user))
    db.commit()
    return {'deleted': True}


@router.get('/courses/{course_id}/review')
def review_material(course_id: int, db: Session = Depends(transaction), user: User = Depends(educator)):
    svc.editor(db, course_id, user)
    policy = svc.active_policy(db, course_id)
    return {'version': svc.VERSION, 'material': svc.CATALOG, 'approved': bool(policy),
            'review_note': policy.review_note if policy else None}


@router.post('/courses/{course_id}/approve')
def approve(course_id: int, body: ApprovalIn, db: Session = Depends(transaction), user: User = Depends(educator)):
    svc.editor(db, course_id, user)
    if body.version != svc.VERSION or len(body.note.strip()) < 10:
        raise HTTPException(422, 'Review the current version and give a meaningful review note.')
    row = db.get(MathPilotPolicy, course_id)
    if not row:
        row = MathPilotPolicy(course_id=course_id)
        db.add(row)
    row.version, row.reviewed_by, row.review_note, row.reviewed_at = svc.VERSION, user.id, body.note.strip(), svc.now()
    # Reuse the platform concept graph, without replacing existing links.
    from app.models.mastery import ConceptPrerequisite
    for prerequisite in svc.CATALOG['prerequisites']:
        if not db.query(ConceptPrerequisite).filter_by(concept=svc.CATALOG['concept'], requires=prerequisite).first():
            db.add(ConceptPrerequisite(concept=svc.CATALOG['concept'], requires=prerequisite, created_by=user.id))
    db.commit()
    return {'approved': True}


@router.delete('/courses/{course_id}/approve')
def pause(course_id: int, db: Session = Depends(transaction), user: User = Depends(educator)):
    svc.editor(db, course_id, user)
    row = db.get(MathPilotPolicy, course_id)
    if row:
        row.version = 'paused'
        row.reviewed_by, row.reviewed_at = user.id, svc.now()
    db.commit()
    return {'approved': False}


@router.get('/courses/{course_id}/evidence')
def evidence(course_id: int, offset: int = Query(0, ge=0), db: Session = Depends(transaction), user: User = Depends(educator)):
    svc.editor(db, course_id, user)
    rows = db.query(MathPilotSession).filter_by(course_id=course_id).filter(
        MathPilotSession.expires_at > svc.now()).order_by(MathPilotSession.id).offset(offset).limit(100).all()
    return {'items': [{**svc.view(r), 'learner_id': r.user_id, 'events': [
        {'action': e.action, 'sequence': e.sequence, 'payload': e.payload, 'result': e.result}
        for e in db.query(MathPilotEvent).filter_by(session_id=r.id).order_by(MathPilotEvent.sequence).all()]}
        for r in rows if svc.enrolled(db, r.user_id, course_id)], 'offset': offset, 'limit': 100,
        'notice': 'Descriptive evidence only. Do not treat repeated events as independent learners or infer causal learning gains.'}


@router.post('/sessions/{session_id}/review')
def override(session_id: int, body: ReviewIn, db: Session = Depends(transaction), user: User = Depends(educator)):
    row = db.query(MathPilotSession).filter_by(id=session_id).with_for_update().first()
    if not row:
        raise HTTPException(404, 'Activity not found.')
    svc.editor(db, row.course_id, user)
    payload = body.model_dump(mode='json')
    old = db.query(MathPilotEvent).filter_by(session_id=row.id, key=str(body.key)).first()
    if old:
        if old.payload != payload or old.actor_id != user.id:
            raise HTTPException(409, 'Request key already used.')
        return svc.view(row)
    svc.available(db, row)
    if row.stage != 'build' or len(body.note.strip()) < 10:
        raise HTTPException(409, 'Interventions can only change before the independent transfer check. Explain your decision.')
    svc.reserve(db, row, body.sequence)
    row.intervention = body.intervention
    db.add(MathPilotEvent(session_id=row.id, sequence=row.sequence, key=str(body.key), actor_id=user.id,
        action='teacher_override', payload=payload, result={'intervention': body.intervention}, created_at=svc.now()))
    db.commit()
    return svc.view(row)
