"""3D match-and-verify tasks (v2.0 §6) — mounted at /api/v1/three-d-tasks
(no trailing slashes; prefix is in axios noSlashEndpoints).

Authoring: instructors create tasks on a 3D model they own OR a shared
library model; config validated per task type; publish makes it insertable
in quizzes (ScorableItem kind 'three_d_task' — see the three helpers at the
bottom that app/schemas/scorable.py and routers/scorable_items.py import).

Play: `GET /{id}/play` ships the config (answers included — advisory posture,
identical to /games/{id}/play); `POST /{id}/attempts` grades SERVER-SIDE from
the submitted state (§6.2), stores the evidence trail and the confidence
signal (§6.3), awards XP best-effort AFTER the commit.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.three_d import ThreeDModel
from app.models.three_d_task import ThreeDTask, ThreeDTaskAttempt
from app.models.user import User
from app.schemas.three_d_task_config import (
    TASK_TYPES, TaskConfigError, confidence_signal, derive_task_max_score,
    grade_task, validate_evidence, validate_task_config,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()

TIERS = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7"]
MAX_CONCEPTS = 20


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    model_id: int
    task_type: str
    config: dict
    concepts: List[str] = Field(default_factory=list)
    tier_floor: str = "T4"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    model_id: Optional[int] = None
    task_type: Optional[str] = None
    config: Optional[dict] = None
    concepts: Optional[List[str]] = None
    tier_floor: Optional[str] = None


class AttemptIn(BaseModel):
    answers: dict = Field(default_factory=dict)
    evidence: list = Field(default_factory=list)
    duration_s: int = Field(0, ge=0, le=6 * 3600)
    mode: str = "T1"


def _get_task(db: Session, task_id: int) -> ThreeDTask:
    t = db.query(ThreeDTask).filter(ThreeDTask.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="3D task not found")
    return t


def _require_owner(task: ThreeDTask, user: User) -> None:
    if task.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your 3D task")


def _check_model_access(db: Session, model_id: int, user: User) -> ThreeDModel:
    m = db.query(ThreeDModel).filter(ThreeDModel.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="3D model not found")
    if m.owner_id != user.id and user.role != "admin" and not bool(getattr(m, "is_library", False)):
        raise HTTPException(status_code=403, detail="You can only build tasks on your own or shared library models")
    return m


def _clean_concepts(concepts: Optional[List[str]]) -> List[str]:
    out, seen = [], set()
    for c in concepts or []:
        if not isinstance(c, str):
            raise HTTPException(status_code=422, detail="concepts must be strings")
        s = " ".join(c.strip().lower().split())[:80]
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    if len(out) > MAX_CONCEPTS:
        raise HTTPException(status_code=422, detail=f"at most {MAX_CONCEPTS} concepts")
    return out


def _task_dict(t: ThreeDTask, include_config: bool = True) -> dict:
    d = {
        "id": t.id, "owner_id": t.owner_id, "model_id": t.model_id, "title": t.title,
        "task_type": t.task_type, "concepts": t.concepts or [], "tier_floor": t.tier_floor,
        "status": t.status, "max_score": derive_task_max_score(t.task_type, t.config or {}),
        "created_at": t.created_at, "updated_at": t.updated_at,
    }
    if include_config:
        d["config"] = t.config
    return d


def _validated(task_type: str, config: dict) -> dict:
    try:
        return validate_task_config(task_type, config)
    except TaskConfigError as exc:
        raise HTTPException(status_code=400, detail=exc.detail)


@router.post("", status_code=201)
async def create_task(payload: TaskCreate, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.require_instructor)):
    if payload.task_type not in TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"task_type must be one of {sorted(TASK_TYPES)}")
    if payload.tier_floor not in TIERS:
        raise HTTPException(status_code=422, detail=f"tier_floor must be one of {TIERS}")
    _check_model_access(db, payload.model_id, current_user)
    cfg = _validated(payload.task_type, payload.config)
    t = ThreeDTask(owner_id=current_user.id, model_id=payload.model_id, title=payload.title.strip(),
                   task_type=payload.task_type, config=cfg, concepts=_clean_concepts(payload.concepts),
                   tier_floor=payload.tier_floor, status="draft")
    db.add(t)
    db.commit()
    db.refresh(t)
    try:
        from app.services.mastery_service import set_links
        set_links(db, "three_d_task", t.id, t.concepts or [], None, current_user.id)
    except Exception:
        db.rollback()
    return _task_dict(t)


@router.get("/for-model/{model_id}")
async def list_tasks_for_model(model_id: int, db: Session = Depends(get_db),
                               current_user: User = Depends(AuthService.get_current_active_user)):
    """Published tasks built on one model — the learner's 'check yourself'
    strip under a 3D lesson and the instructor's teaching kit. No configs
    (answers) leak here; /play still gates per task."""
    rows = (db.query(ThreeDTask).filter(ThreeDTask.model_id == model_id, ThreeDTask.status == "published")
            .order_by(ThreeDTask.id.asc()).all())
    return {"tasks": [_task_dict(t, include_config=False) for t in rows]}


@router.get("/mine")
async def list_my_tasks(db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.require_instructor)):
    rows = db.query(ThreeDTask).filter(ThreeDTask.owner_id == current_user.id).order_by(ThreeDTask.updated_at.desc()).all()
    return {"tasks": [_task_dict(t, include_config=False) for t in rows]}


@router.get("/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(AuthService.require_instructor)):
    t = _get_task(db, task_id)
    _require_owner(t, current_user)
    return _task_dict(t)


@router.put("/{task_id}")
async def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.require_instructor)):
    t = _get_task(db, task_id)
    _require_owner(t, current_user)
    task_type = payload.task_type or t.task_type
    if task_type not in TASK_TYPES:
        raise HTTPException(status_code=422, detail=f"task_type must be one of {sorted(TASK_TYPES)}")
    if payload.model_id is not None and payload.model_id != t.model_id:
        _check_model_access(db, payload.model_id, current_user)
        t.model_id = payload.model_id
    if payload.config is not None or payload.task_type is not None:
        t.config = _validated(task_type, payload.config if payload.config is not None else t.config)
        t.task_type = task_type
    if payload.title is not None:
        t.title = payload.title.strip()
    if payload.concepts is not None:
        t.concepts = _clean_concepts(payload.concepts)
    if payload.tier_floor is not None:
        if payload.tier_floor not in TIERS:
            raise HTTPException(status_code=422, detail=f"tier_floor must be one of {TIERS}")
        t.tier_floor = payload.tier_floor
    db.commit()
    db.refresh(t)
    try:
        from app.services.mastery_service import set_links
        set_links(db, "three_d_task", t.id, t.concepts or [], None, current_user.id)
    except Exception:
        db.rollback()
    return _task_dict(t)


@router.post("/{task_id}/publish")
async def publish_task(task_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(AuthService.require_instructor)):
    t = _get_task(db, task_id)
    _require_owner(t, current_user)
    _validated(t.task_type, t.config or {})   # re-validate at publish
    t.status = "published"
    db.commit()
    db.refresh(t)
    return _task_dict(t)


@router.post("/{task_id}/unpublish")
async def unpublish_task(task_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.require_instructor)):
    t = _get_task(db, task_id)
    _require_owner(t, current_user)
    t.status = "draft"
    db.commit()
    db.refresh(t)
    return _task_dict(t)


def _quizzes_using(db: Session, task_id: int) -> int:
    from app.models.quiz import Quiz
    n = 0
    for q in db.query(Quiz).filter(Quiz.interactive_modules.isnot(None)).all():
        for m in (q.interactive_modules or []):
            if m.get("kind") == "three_d_task" and str(m.get("id")) == str(task_id):
                n += 1
    return n


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(AuthService.require_instructor)):
    t = _get_task(db, task_id)
    _require_owner(t, current_user)
    n = _quizzes_using(db, task_id)
    if n:
        raise HTTPException(status_code=409, detail=f"Used by {n} quiz(zes) — remove it there first")
    db.query(ThreeDTaskAttempt).filter(ThreeDTaskAttempt.task_id == task_id).delete()
    db.delete(t)
    db.commit()
    return {"deleted": True, "id": task_id}


@router.get("/{task_id}/play")
async def play_task(task_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(AuthService.get_current_active_user)):
    t = _get_task(db, task_id)
    if t.status != "published" and t.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="This task is not published")
    best = (db.query(func.max(ThreeDTaskAttempt.score))
            .filter(ThreeDTaskAttempt.task_id == task_id, ThreeDTaskAttempt.user_id == current_user.id).scalar())
    d = _task_dict(t)
    d["best_score"] = int(best) if best is not None else None
    d["attempts"] = (db.query(ThreeDTaskAttempt)
                     .filter(ThreeDTaskAttempt.task_id == task_id, ThreeDTaskAttempt.user_id == current_user.id).count())
    return d


@router.post("/{task_id}/attempts", status_code=201)
async def submit_attempt(task_id: int, payload: AttemptIn, db: Session = Depends(get_db),
                         current_user: User = Depends(AuthService.get_current_active_user)):
    t = _get_task(db, task_id)
    if t.status != "published" and t.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="This task is not published")
    if payload.mode not in TIERS:
        raise HTTPException(status_code=422, detail=f"mode must be one of {TIERS}")
    try:
        evidence = validate_evidence(payload.evidence)
    except TaskConfigError as exc:
        raise HTTPException(status_code=422, detail=exc.detail)
    max_score = derive_task_max_score(t.task_type, t.config or {})
    score, detail = grade_task(t.task_type, t.config or {}, payload.answers, evidence)
    label, cdetail = confidence_signal(evidence, score, max_score)

    preview = t.owner_id == current_user.id or current_user.role == "admin"
    row = ThreeDTaskAttempt(task_id=task_id, user_id=current_user.id, score=score, max_score=max_score,
                            mode=payload.mode, answers=payload.answers, evidence=evidence,
                            confidence=label, confidence_detail=cdetail, duration_s=payload.duration_s)
    if not preview:
        db.add(row)
        db.commit()
        db.refresh(row)
        try:
            from app.services.gamification_service import award as _award_xp
            if score > 0:
                _award_xp(db, current_user.id, "three_d_task_completed", points=20,
                          event_key=f"three_d_task:{task_id}:completed:user:{current_user.id}",
                          meta={"task_id": task_id, "task_type": t.task_type, "confidence": label})
            if max_score and score == max_score:
                _award_xp(db, current_user.id, "three_d_task_perfect", points=10,
                          event_key=f"three_d_task:{task_id}:perfect:user:{current_user.id}",
                          meta={"task_id": task_id, "task_type": t.task_type})
            db.commit()
        except Exception as exc:
            logger.warning("Gamification award failed for 3D task attempt: %s", exc)
            try:
                db.rollback()
            except Exception:
                pass
    if not preview:
        from app.services.mastery_service import safe_record_evidence
        safe_record_evidence(db, user_id=current_user.id, kind="three_d_task", ref_id=task_id, score=float(score),
                             max_score=float(max_score), path_confidence=label)
    best = (db.query(func.max(ThreeDTaskAttempt.score))
            .filter(ThreeDTaskAttempt.task_id == task_id, ThreeDTaskAttempt.user_id == current_user.id).scalar())
    return {"id": None if preview else row.id, "score": score, "max_score": max_score, "grading": detail,
            "confidence": label, "confidence_detail": cdetail, "preview": preview,
            "best_score": int(best) if best is not None else score}


@router.get("/{task_id}/attempts")
async def list_attempts(task_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(AuthService.require_instructor)):
    t = _get_task(db, task_id)
    _require_owner(t, current_user)
    rows = (db.query(ThreeDTaskAttempt).filter(ThreeDTaskAttempt.task_id == task_id)
            .order_by(ThreeDTaskAttempt.created_at.desc()).limit(500).all())
    return {"attempts": [{
        "id": a.id, "user_id": a.user_id, "score": a.score, "max_score": a.max_score, "mode": a.mode,
        "confidence": a.confidence, "confidence_detail": a.confidence_detail, "duration_s": a.duration_s,
        "created_at": a.created_at,
    } for a in rows]}


# ---------------------------------------------------------------- hooks for the ScorableItem contract

def resolve_task_for_quiz(db: Session, ref: Any, current_user) -> Tuple[int, str, int, Optional[str]]:
    if not isinstance(ref, int) or isinstance(ref, bool):
        raise HTTPException(status_code=422, detail="three_d_task items need an integer id")
    t = db.query(ThreeDTask).filter(ThreeDTask.id == ref).first()
    if not t:
        raise HTTPException(status_code=404, detail=f"3D task {ref} not found")
    if t.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail=f"not your 3D task {ref}")
    if t.status != "published":
        raise HTTPException(status_code=422, detail=f"3D task {ref} is not published")
    return t.id, t.title, derive_task_max_score(t.task_type, t.config or {}), None


def best_task_score(db: Session, ref: Any, user_id: int) -> Optional[Tuple[float, float]]:
    res = (db.query(ThreeDTaskAttempt)
           .filter(ThreeDTaskAttempt.task_id == ref, ThreeDTaskAttempt.user_id == user_id)
           .order_by(ThreeDTaskAttempt.score.desc()).first())
    if res and res.max_score:
        return float(res.score), float(res.max_score)
    return None


def list_tasks_for_palette(db: Session, current_user) -> List[dict]:
    rows = (db.query(ThreeDTask)
            .filter(ThreeDTask.owner_id == current_user.id, ThreeDTask.status == "published")
            .order_by(ThreeDTask.title).all())
    return [{
        "kind": "three_d_task", "id": t.id, "title": t.title,
        "max_score": derive_task_max_score(t.task_type, t.config or {}),
        "tier_floor": t.tier_floor or "T4", "bucket": "three_d_tasks",
        "template": t.task_type, "source": "mine",
    } for t in rows]
