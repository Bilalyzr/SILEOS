"""Reviewed bundled content, ownership and atomic data-only lab imports."""
from uuid import uuid4
from fastapi import HTTPException
from app.models.content_library import VirtualLabCatalog

from app.services.lab_catalog_service import (CBSE_LABS, CHAPTERS, CHAPTER_IDS, CONCEPT_EXTENSIONS, CONCEPT_LABS, EDITIONS)


def author(user):
    if user.role not in ('instructor', 'admin', 'superadmin'):
        raise HTTPException(403, 'Instructor access required.')
    return user


def owned(db, slug, user):
    author(user)
    row = db.query(VirtualLabCatalog).filter_by(slug=slug, native_template='concept_lab').first()
    if row is None or (row.created_by != user.id and user.role not in ('admin', 'superadmin')):
        raise HTTPException(404, 'Lab draft not found.')
    return row


def write_draft(db, payload, user, row=None):
    from app.services.lab_model_service import require_attachable
    require_attachable(db, payload.config.model_id, user)
    if row is None:
        row = VirtualLabCatalog(slug='own-' + uuid4().hex, created_by=user.id, provider='native', native_template='concept_lab', is_published=False)
        db.add(row)
    row.title = payload.title
    row.subject = payload.subject
    row.description = payload.description
    row.config = payload.config.model_dump()
    row.attribution = 'SashaInfinity · instructor-authored concept lab'
    return row


def draft_dict(row):
    return {k: getattr(row, k) for k in ('slug', 'title', 'subject', 'description', 'config', 'is_published', 'updated_at')}
