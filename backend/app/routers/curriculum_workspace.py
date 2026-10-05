from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.course_access import can_edit
from app.services import curriculum_workspace as svc
from app.models.course import Course
from app.models.curriculum_workspace import CurriculumChapter, CurriculumCourseLink

router = APIRouter()


def transaction(response: Response, db: Session = Depends(get_db)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        yield db
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'This reference already exists or changed concurrently. Reload to continue.')


class LinkIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    chapter_key: str = Field(min_length=1, max_length=180)
    course_id: int = Field(gt=0)
    note: str = Field(min_length=10, max_length=2000)


class ChapterIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    grade: int = Field(ge=6, le=12)
    subject: str = Field(min_length=2, max_length=80, pattern=r'^[a-z][a-z0-9 -]+$')
    title: str = Field(min_length=3, max_length=200)
    edition: str = Field(min_length=4, max_length=40)
    source_url: str = Field(max_length=500)
    review_note: str = Field(min_length=10, max_length=2000)

    @field_validator('source_url')
    @classmethod
    def official_reference(cls, value):
        url = urlparse(value)
        if url.scheme != 'https' or url.hostname not in ('cbseacademic.nic.in', 'www.cbseacademic.nic.in', 'ncert.nic.in', 'www.ncert.nic.in') or url.username or url.password or url.port:
            raise ValueError('Use an HTTPS CBSE Academic or NCERT reference URL.')
        return value


@router.get('')
def overview(db: Session = Depends(transaction), user=Depends(AuthService.get_current_active_user)):
    return svc.overview(db, user)


@router.post('/links')
def link(body: LinkIn, db: Session = Depends(transaction), user=Depends(AuthService.get_current_active_user)):
    return svc.link_course(db, user, body)


@router.delete('/links/{link_id}')
def unlink(link_id: int, db: Session = Depends(transaction), user=Depends(AuthService.get_current_active_user)):
    row = db.get(CurriculumCourseLink, link_id)
    if not row or user.role not in ('instructor', 'admin', 'superadmin') or not can_edit(db, db.get(Course, row.course_id), user):
        raise HTTPException(404, 'Mapping not found.')
    db.delete(row); db.commit()
    return {'unlinked': True}


@router.post('/chapters')
def chapter(body: ChapterIn, db: Session = Depends(transaction), user=Depends(AuthService.get_current_active_user)):
    if user.role not in ('admin', 'superadmin'):
        raise HTTPException(403, 'Administrator review required for a shared chapter reference.')
    row = CurriculumChapter(**body.model_dump(), created_by=user.id)
    db.add(row); db.commit()
    return {'id': f'custom:{row.id}'}
