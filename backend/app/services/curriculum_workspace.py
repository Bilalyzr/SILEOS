"""One catalogue over real LMS resources, never fabricated lesson coverage."""
from hashlib import sha256
import json
from fastapi import HTTPException
from sqlalchemy import or_
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.curriculum_workspace import CurriculumChapter, CurriculumCourseLink
from app.services.course_access import can_edit, collaborated_course_ids, ADMIN_ROLES
from app.services.lab_catalog_service import CHAPTERS


def chapters(db):
    return [dict(c, source_url=None, alignment='Supplied map; current syllabus alignment unverified') for c in CHAPTERS] + [
        {'id': f'custom:{c.id}', 'grade': c.grade, 'subject': c.subject, 'title': c.title,
         'edition': c.edition, 'source_url': c.source_url, 'lab_slug': None,
         'alignment': 'Administrator-reviewed chapter reference'} for c in db.query(CurriculumChapter).order_by(CurriculumChapter.id).all()]


def snapshot(course, lessons):
    fields = tuple(c.name for c in Lesson.__table__.columns if c.name not in ('post_date', 'post_modified'))
    value = [course.post_title, course.post_content, course.course_sections_meta,
             [{key: getattr(l, key, None) for key in fields} for l in sorted(lessons, key=lambda x: x.id)]]
    return sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def visible_courses(db, user):
    q = db.query(Course)
    if user.role not in ADMIN_ROLES:
        owned = or_(Course.post_author == user.id, Course.id.in_(collaborated_course_ids(db, user.id)))
        if user.role == 'student':
            q = q.filter(db.query(Enrollment.id).filter(Enrollment.course_id == Course.id,
                Enrollment.user_id == user.id, Enrollment.enrollment_status.in_(['enrolled', 'completed'])).exists())
        else:
            q = q.filter(owned)
    return q.order_by(Course.post_title).all()


def overview(db, user):
    from app.routers.virtual_labs import catalog
    active_labs = catalog(db)
    definitions = chapters(db)
    accessible = {c.id: c for c in visible_courses(db, user)}
    links = db.query(CurriculumCourseLink).all()
    mapped_ids = {l.course_id for l in links}
    published = {c.id: c for c in db.query(Course).filter(Course.id.in_(mapped_ids), Course.post_status.in_(['publish', 'published'])).all()}
    courses = {**published, **{cid: c for cid, c in accessible.items() if cid in mapped_ids}}
    by_course = {}
    for lesson in db.query(Lesson).filter(Lesson.post_parent.in_(courses)).all():
        by_course.setdefault(lesson.post_parent, []).append(lesson)
    mappings = {}
    for link in links:
        course = courses.get(link.course_id)
        if not course:
            continue
        lessons = by_course.get(course.id, [])
        current = link.revision == snapshot(course, lessons)
        ready = current and course.id in published and any(l.post_status in ('publish', 'published') for l in lessons)
        editable = can_edit(db, course, user) and user.role in ('instructor', 'admin', 'superadmin')
        if not ready and not editable:
            continue
        mappings.setdefault(link.chapter_key, []).append({
            'link_id': link.id, 'id': course.id, 'title': course.post_title,
            'url': f'/courses/{course.post_name or course.id}', 'enrolled': course.id in accessible and user.role == 'student',
            'ready': ready, 'editable': editable, 'review_note': link.review_note if editable else None,
            'lesson_count': sum(l.post_status in ('publish', 'published') for l in lessons)})
    result = []
    for chapter in definitions:
        slug = chapter.get('lab_slug')
        labs = []
        if slug in active_labs:
            labs.append({'slug': slug, 'title': active_labs[slug]['title']})
        # Instructor-authored published labs may explicitly name this chapter.
        for lab_slug, lab in active_labs.items():
            if lab_slug != slug and chapter['id'] in ((lab.get('config') or {}).get('chapter_ids') or lab.get('chapter_ids') or []):
                labs.append({'slug': lab_slug, 'title': lab['title']})
        links = mappings.get(chapter['id'], [])
        result.append({**chapter, 'labs': labs, 'courses': links,
            'coverage': 'linked_course' if any(l['ready'] for l in links) else 'activity_only' if labs else 'content_needed'})
    return {'chapters': result, 'courses': [{'id': c.id, 'title': c.post_title,
                'editable': user.role in ('instructor', 'admin', 'superadmin') and can_edit(db, c, user)} for c in accessible.values()],
            'notice': 'A chapter reference or linked activity is not a complete curriculum. Existing maps require edition review.',
            'official_reference': 'https://cbseacademic.nic.in/curriculum_2027.html'}


def link_course(db, user, body):
    if user.role not in ('instructor', 'admin', 'superadmin'):
        raise HTTPException(403, 'Teaching access required.')
    if body.chapter_key not in {c['id'] for c in chapters(db)}:
        raise HTTPException(422, 'Unknown chapter reference.')
    course = db.get(Course, body.course_id)
    if not can_edit(db, course, user):
        raise HTTPException(403, 'Not your course.')
    lessons = db.query(Lesson).filter_by(post_parent=course.id).all()
    if course.post_status not in ('publish', 'published') or not any(l.post_status in ('publish', 'published') for l in lessons):
        raise HTTPException(422, 'Publish at least one lesson and the course before linking it.')
    row = db.query(CurriculumCourseLink).filter_by(chapter_key=body.chapter_key, course_id=course.id).first()
    if not row:
        row = CurriculumCourseLink(chapter_key=body.chapter_key, course_id=course.id)
        db.add(row)
    row.reviewed_by, row.review_note = user.id, body.note.strip()
    row.revision = snapshot(course, lessons)
    db.commit()
    return {'id': row.id}
