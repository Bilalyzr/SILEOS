"""Course content uploads, automatic backup detection, preview and draft restoration."""
from datetime import timedelta, timezone
import hashlib
import html
from pathlib import Path
import logging
import shutil
import uuid
import zipfile
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from app.core.database import get_db
from app.models.course import Course
from app.models.operations import CourseTransfer
from app.services.auth_service import AuthService
from app.services.course_access import can_edit, ADMIN_ROLES, collaborated_course_ids
from app.services import course_package_service as svc
from sqlalchemy import or_

router = APIRouter()
logger = logging.getLogger(__name__)


class RestoreIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)


def transfer(db, ident, user):
    row = db.query(CourseTransfer).filter_by(id=ident, owner_id=user.id).first()
    if not row: raise HTTPException(404, "Upload preview not found.")
    expires = row.expires_at
    if expires.tzinfo is None: expires = expires.replace(tzinfo=timezone.utc)
    if row.status != 'restored' and expires < svc.utcnow():
        raise HTTPException(410, "This preview expired. Upload the file again.")
    return row


@router.get('/courses')
def courses(db: Session = Depends(get_db), user=Depends(AuthService.require_instructor)):
    query = db.query(Course)
    if user.role not in ADMIN_ROLES: query = query.filter(or_(Course.post_author == user.id, Course.id.in_(collaborated_course_ids(db, user.id))))
    return {'courses': [{'id': r.id, 'title': r.post_title, 'status': r.post_status} for r in query.order_by(Course.post_title).all()]}


@router.get('/courses/{course_id}/backup')
def backup(course_id: int, db: Session = Depends(get_db), user=Depends(AuthService.require_instructor)):
    course = db.get(Course, course_id)
    if not course: raise HTTPException(404, 'Course not found.')
    if not can_edit(db, course, user): raise HTTPException(403, 'Not your course.')
    svc.root().mkdir(parents=True, exist_ok=True)
    path = svc.root() / f'{uuid.uuid4()}.sasha-course.zip'
    try:
        svc.export_course(db, course, path)
    except (ValueError, OSError) as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else 'A course asset is unavailable.')
    return FileResponse(path, media_type='application/zip', filename=f'course-{course_id}.sasha-course.zip', headers={'Cache-Control':'private, no-store'}, background=BackgroundTask(path.unlink, missing_ok=True))


@router.post('/inspect', status_code=201)
def inspect(files: list[UploadFile] = File(...), db: Session = Depends(get_db), user=Depends(AuthService.require_instructor)):
    if not 1 <= len(files) <= 30: raise HTTPException(422, 'Upload one backup or up to thirty course files.')
    svc.cleanup_expired(db)
    active = db.query(CourseTransfer).filter(CourseTransfer.owner_id == user.id, CourseTransfer.expires_at > svc.utcnow(), CourseTransfer.status == 'preview').count()
    if active >= 5: raise HTTPException(429, 'Finish or discard an existing preview before uploading more files.')
    ident = str(uuid.uuid4()); folder = svc.safe_path(svc.root(), ident); folder.mkdir(parents=True)
    total = 0; digest = hashlib.sha256()
    try:
        stored = []
        for index, upload in enumerate(files):
            dest = folder / ('upload.bin' if index == 0 else f'upload-{index}.bin')
            with dest.open('wb') as target:
                while chunk := upload.file.read(1024*1024):
                    total += len(chunk)
                    if total > svc.MAX_UPLOAD: raise ValueError('Total upload limit is 200 MB.')
                    digest.update(chunk); target.write(chunk)
            stored.append((dest, (upload.filename or 'document')[:255]))
        first, filename = stored[0]
        is_backup = False
        if zipfile.is_zipfile(first):
            with zipfile.ZipFile(first) as z:
                is_backup = 'manifest.json' in z.namelist()
        if is_backup or (Path(filename).suffix.lower() == '.zip'):
            if len(stored) != 1: raise ValueError('Upload a backup by itself.')
            data, manifest = svc.inspect_archive(first); kind = 'backup'; warnings = manifest.get('warnings', [])
        else:
            from app.services.course_asset_service import inspect_files
            kind = 'documents'
            data, manifest, warnings = inspect_files(stored)
        svc.validate_data(data)
        row = CourseTransfer(id=ident, owner_id=user.id, kind=kind, filename=filename, sha256=digest.hexdigest(), manifest={'data':data, 'package':manifest}, warnings=warnings, expires_at=svc.utcnow()+timedelta(hours=24))
        db.add(row); db.commit()
        return svc.transfer_out(row)
    except Exception as exc:
        db.rollback()
        # folder is a freshly generated UUID under the private staging root.
        checked = svc.safe_path(svc.root(), ident)
        if checked.is_dir(): shutil.rmtree(checked)
        if isinstance(exc, HTTPException): raise
        raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else 'Could not read this upload. Use supported documents or a valid Sasha backup.')
    finally:
        for upload in files: upload.file.close()


@router.get('/previews')
def previews(db: Session = Depends(get_db), user=Depends(AuthService.require_instructor)):
    svc.cleanup_expired(db)
    rows = db.query(CourseTransfer).filter(CourseTransfer.owner_id == user.id, CourseTransfer.expires_at > svc.utcnow(), CourseTransfer.status != 'discarded').order_by(CourseTransfer.created_at.desc()).limit(20).all()
    return {'previews': [svc.transfer_out(r) for r in rows]}


@router.delete('/previews/{ident}')
def discard(ident: str, db: Session = Depends(get_db), user=Depends(AuthService.require_instructor)):
    row = transfer(db, ident, user)
    if row.status == 'restoring': raise HTTPException(409, 'This backup is being restored.')
    folder = svc.safe_path(svc.root(), row.id)
    if folder.is_dir(): shutil.rmtree(folder)
    row.status = 'discarded'; db.commit()
    return {'discarded': True}


@router.post('/previews/{ident}/restore')
def restore(ident: str, body: RestoreIn, db: Session = Depends(get_db), user=Depends(AuthService.require_instructor)):
    row = transfer(db, ident, user)
    if row.status == 'restored':
        if row.course_id is None: raise HTTPException(410, 'The restored course has been deleted.')
        course = db.get(Course, row.course_id)
        if not course: raise HTTPException(410, 'The restored course has been deleted.')
        return {'course_id': row.course_id, 'status': course.post_status, 'already_restored': True}
    changed = db.query(CourseTransfer).filter_by(id=ident, owner_id=user.id, status='preview').update({'status':'restoring'}, synchronize_session=False)
    if not changed: raise HTTPException(409, 'This preview was already consumed or is being restored.')
    db.expire(row)
    try: course = svc.restore(db, row, user, body.title)
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Course package restore failed (preview=%s owner=%s kind=%s)",
            ident,
            user.id,
            row.kind,
        )
        raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else 'Restore failed. No course was created; check the backup and try again.')
    return {'course_id': course.id, 'status':course.post_status, 'already_restored':False}
