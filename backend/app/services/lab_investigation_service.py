"""Formative lab assessments: server-owned keys and revision-aware evidence."""
from hashlib import sha256
import json
import math
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models.learning_release import LabInvestigationAttempt


class InvestigationIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    submission_id: UUID
    revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    visited: list[str] = Field(default_factory=list, max_length=30)
    answers: dict[str, int] = Field(default_factory=dict)
    parameters: dict[str, float] = Field(default_factory=dict)
    observations: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def bounded(self):
        if any(len(v)>30 for v in (self.answers,self.parameters,self.observations)) or any(len(v)>3000 for v in self.observations.values()):
            raise ValueError('Evidence exceeds the allowed size.')
        if any(not math.isfinite(v) for v in self.parameters.values()):
            raise ValueError('Control values must be finite.')
        if len(json.dumps(self.model_dump(mode='json'))) > 100000:
            raise ValueError('Evidence too large.')
        return self


def revision(config):
    return sha256(json.dumps(config or {}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def learner_config(config):
    result = json.loads(json.dumps(config or {}))
    for step in result.get('guided_steps', []):
        step.pop('correct_index', None)
    return result


def response(row):
    return {k: getattr(row,k) for k in ('id','submission_id','revision','score','max_score','feedback','created_at')}


def submit(db, slug, payload, user):
    if user.role != 'student':
        raise HTTPException(403, 'Only student investigations are recorded. Staff can preview the activity.')
    from app.routers.virtual_labs import get_lab
    lab = get_lab(db, slug)
    if not lab or lab.get('native_template') != 'concept_lab':
        raise HTTPException(404, 'Published investigation not found.')
    config = lab.get('config') or {}
    if not config.get('guided_steps'):
        raise HTTPException(422, 'This lab does not have a guided investigation.')
    evidence = payload.model_dump(mode='json')
    def existing():
        row = db.query(LabInvestigationAttempt).filter_by(user_id=user.id,submission_id=str(payload.submission_id)).first()
        if row and (row.lab_slug != slug or row.evidence != evidence):
            raise HTTPException(409, 'Submission identifier already used for different evidence.')
        return row
    old = existing()
    if old:
        return response(old)
    if payload.revision != revision(config):
        raise HTTPException(409, 'The activity changed. Reload it before submitting a new attempt.')
    steps = config.get('guided_steps', [])
    ids = {s['id'] for s in steps}
    if set(payload.visited) - {h['id'] for h in config.get('hotspots', [])} or any(set(m)-ids for m in (payload.answers,payload.parameters,payload.observations)):
        raise HTTPException(422, 'Evidence references an unknown step or hotspot.')
    feedback=[]
    for step in steps:
        sid, kind = step['id'], step['kind']
        correct = False
        if kind == 'question':
            correct = payload.answers.get(sid) == step.get('correct_index')
        elif kind == 'visit':
            correct = step.get('hotspot_id') in payload.visited
        elif kind == 'parameter':
            value = payload.parameters.get(sid)
            correct = value is not None and step['target_min'] <= value <= step['target_max']
        available = step.get('points',0) if config.get('assessment_enabled') else 0
        points = available if correct else 0
        feedback.append({'step_id':sid,'earned':points,'available':available,'status':'recorded' if kind=='observation' else 'met' if correct else 'try_again'})
    score = sum(f['earned'] for f in feedback)
    maximum = sum(f['available'] for f in feedback)
    previous = db.query(LabInvestigationAttempt).filter_by(user_id=user.id,lab_slug=slug,revision=payload.revision).order_by(LabInvestigationAttempt.score.desc()).first()
    improved = previous is None or score > previous.score
    row = LabInvestigationAttempt(user_id=user.id,lab_slug=slug,submission_id=str(payload.submission_id),revision=payload.revision,evidence=evidence,feedback=feedback,score=score,max_score=maximum)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        old = existing()
        if old: return response(old)
        raise
    if improved and maximum > 0:
        from app.services.mastery_service import safe_record_evidence
        safe_record_evidence(db,user_id=user.id,kind='lab',ref_id=slug,score=float(score),max_score=float(maximum))
    return response(row)


def best_score(db, slug, user_id, config):
    row = db.query(LabInvestigationAttempt).filter_by(user_id=user_id,lab_slug=slug,revision=revision(config)).order_by(LabInvestigationAttempt.score.desc()).first()
    return (float(row.score),float(row.max_score)) if row and row.max_score else None
