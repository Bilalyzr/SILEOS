from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.models.content_library import VirtualLabCatalog
from app.models.lab_notebook import LabNotebook
from app.schemas.concept_lab import LabDraftIn, LabPack, NotebookIn
from app.services.auth_service import AuthService
from app.services import lab_studio_service as svc

router = APIRouter()
active = AuthService.get_current_active_user
from app.services.lab_investigation_service import InvestigationIn
from uuid import UUID


@router.get('/offline/courses/{course_id}')
def offline_manifest(course_id: int, db: Session = Depends(get_db), user=Depends(active)):
    from app.services.offline_learning_service import manifest
    return manifest(db,user,course_id)


class OfflineCompletion(BaseModel):
    event_id: UUID
    revision: str


@router.post('/offline/courses/{course_id}/lessons/{lesson_id}/complete')
async def offline_completion(course_id: int, lesson_id: int, payload: OfflineCompletion, db: Session = Depends(get_db), user=Depends(active)):
    from app.services.offline_learning_service import enrolled, lesson_version
    from app.models.course import Lesson
    from app.models.learning_release import OfflineSyncReceipt
    from app.routers.courses import mark_lesson_complete
    enrolled(db,user,course_id)
    lesson=db.query(Lesson).filter(Lesson.id==lesson_id,Lesson.post_parent==course_id,Lesson.post_status.in_(['publish','published'])).first()
    if not lesson:raise HTTPException(404,'Published lesson not found.')
    if payload.revision!=lesson_version(lesson):raise HTTPException(409,'Lesson changed. Download the latest version before marking it complete.')
    receipt=db.query(OfflineSyncReceipt).filter_by(user_id=user.id,event_id=str(payload.event_id)).first()
    if receipt:
        if receipt.lesson_id != lesson_id:raise HTTPException(409,'Event identifier belongs to a different lesson.')
        return {'synced':True,'replayed':True}
    db.add(OfflineSyncReceipt(user_id=user.id,event_id=str(payload.event_id),lesson_id=lesson_id))
    try:
        await mark_lesson_complete(course_id,lesson_id,db,user)
    except IntegrityError:
        db.rollback()
        receipt=db.query(OfflineSyncReceipt).filter_by(user_id=user.id,event_id=str(payload.event_id)).first()
        if not receipt or receipt.lesson_id!=lesson_id:raise HTTPException(409,'Completion sync conflict. Retry with a new event.')
    return {'synced':True}


@router.post('/labs/{slug}/attempts')
def submit_investigation(slug: str, payload: InvestigationIn, db: Session = Depends(get_db), user=Depends(active)):
    from app.services.lab_investigation_service import submit
    return submit(db, slug, payload, user)


@router.get('/labs/{slug}/attempts')
def review_investigations(slug: str, db: Session = Depends(get_db), user=Depends(active)):
    svc.owned(db, slug, user)
    from app.models.learning_release import LabInvestigationAttempt
    from app.services.lab_investigation_service import response
    rows = db.query(LabInvestigationAttempt).filter_by(lab_slug=slug).order_by(LabInvestigationAttempt.id.desc()).limit(100).all()
    return {'attempts':[dict(response(r), user_id=r.user_id, evidence=r.evidence) for r in rows]}


@router.post('/supplied-pack/inspect')
async def inspect_supplied(file: UploadFile = File(...), user=Depends(AuthService.require_admin)):
    from app.services.supplied_lab_pack import inspect, MAX_BYTES
    pack = inspect(await file.read(MAX_BYTES + 1))
    return pack.model_dump()


@router.post('/supplied-pack/import')
async def import_supplied(file: UploadFile = File(...), manifest: str | None = Form(None), db: Session = Depends(get_db), user=Depends(AuthService.require_admin)):
    from app.services.supplied_lab_pack import restore, MAX_BYTES
    return restore(db, await file.read(MAX_BYTES + 1), user, manifest)


@router.get('/supplied-pack/export')
def export_supplied(name: str = 'Sasha Virtual Labs', db: Session = Depends(get_db), user=Depends(active)):
    svc.author(user)
    if not 3 <= len(name.strip()) <= 120:
        raise HTTPException(422, 'Pack name must contain 3–120 characters.')
    from app.services.supplied_lab_pack import export
    return Response(export(db, name.strip()), media_type='application/zip', headers={'Content-Disposition': 'attachment; filename="sasha-virtual-labs.zip"', 'Cache-Control': 'no-store'})


@router.get('/curriculum')
def curriculum(db: Session = Depends(get_db)):
    from app.routers.virtual_labs import catalog
    active_catalog = catalog(db)
    labs = [dict(l, **{k: active_catalog[l['slug']][k] for k in ('title', 'description', 'embed_url')}) for l in svc.CBSE_LABS if l['slug'] in active_catalog]
    chapters = [dict(c, lab_slug=c['lab_slug'] if c['lab_slug'] in active_catalog else None) for c in svc.CHAPTERS]
    return {'chapters': chapters, 'labs': labs, 'editions': svc.EDITIONS,
            'source': 'User-supplied curriculum maps. A linked activity explores part of a chapter; alignment has not been independently certified.'}


@router.get('/drafts')
def drafts(db: Session = Depends(get_db), user=Depends(active)):
    svc.author(user)
    rows = db.query(VirtualLabCatalog).filter_by(native_template='concept_lab', created_by=user.id).order_by(VirtualLabCatalog.updated_at.desc()).all()
    return {'labs': [svc.draft_dict(r) for r in rows]}


@router.post('/drafts', status_code=201)
def create(payload: LabDraftIn, db: Session = Depends(get_db), user=Depends(active)):
    svc.author(user)
    row = svc.write_draft(db, payload, user)
    db.commit()
    db.refresh(row)
    return svc.draft_dict(row)


@router.put('/drafts/{slug}')
def update(slug: str, payload: LabDraftIn, db: Session = Depends(get_db), user=Depends(active)):
    row = svc.owned(db, slug, user)
    svc.write_draft(db, payload, user, row)
    db.commit()
    db.refresh(row)
    return svc.draft_dict(row)


class PublishIn(BaseModel):
    published: bool


@router.post('/drafts/{slug}/publication')
def publish(slug: str, payload: PublishIn, db: Session = Depends(get_db), user=Depends(active)):
    row = svc.owned(db, slug, user)
    # Validate again even if an old draft predates the current contract.
    validated = LabDraftIn(title=row.title, subject=row.subject, description=row.description or '', config=row.config)
    from app.services.lab_model_service import require_attachable
    require_attachable(db, validated.config.model_id, user)
    row.is_published = payload.published
    db.commit()
    return svc.draft_dict(row)


@router.get('/drafts/{slug}/export')
def export(slug: str, db: Session = Depends(get_db), user=Depends(active)):
    row = svc.owned(db, slug, user)
    from app.services.lab_model_service import export_pack
    data, media, extension = export_pack(db, row, user)
    return Response(data, media_type=media, headers={'Content-Disposition': f'attachment; filename="{row.slug}.sasha-labs.{extension}"', 'Cache-Control': 'no-store'})


@router.post('/import', status_code=201)
async def import_pack(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(active)):
    svc.author(user)
    from app.services.lab_model_service import import_pack as restore, MAX_PACK
    raw = await file.read(MAX_PACK + 1)
    if len(raw) > MAX_PACK:
        raise HTTPException(413, 'Lab ZIP backups must be under 52 MB.')
    rows = restore(db, raw, user)
    return {'labs': [svc.draft_dict(row) for row in rows]}


def accessible(db, slug, user):
    from app.routers.virtual_labs import get_lab
    if get_lab(db, slug) is None:
        svc.owned(db, slug, user)


@router.get('/notebooks/{slug}')
def notebook(slug: str, db: Session = Depends(get_db), user=Depends(active)):
    accessible(db, slug, user)
    row = db.query(LabNotebook).filter_by(user_id=user.id, lab_slug=slug).first()
    return {k: getattr(row, k) if row else ([] if k == 'trials' else '') for k in ('prediction', 'observation', 'conclusion', 'trials')}


@router.put('/notebooks/{slug}')
def save_notebook(slug: str, payload: NotebookIn, db: Session = Depends(get_db), user=Depends(active)):
    accessible(db, slug, user)
    row = db.query(LabNotebook).filter_by(user_id=user.id, lab_slug=slug).first()
    if row is None:
        row = LabNotebook(user_id=user.id, lab_slug=slug)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Another save created this notebook. Reload and try again.')
    return {'saved': True, 'updated_at': row.updated_at}
