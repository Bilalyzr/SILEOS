"""Bounded offline snapshots. Access and content versions are rechecked on sync."""
from html.parser import HTMLParser
from fastapi import HTTPException
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.services.lab_investigation_service import revision, learner_config


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag in ('p','div','li','br','h1','h2','h3'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)


def text_only(value):
    parser=Text();parser.feed(value or '');return ''.join(parser.parts).strip()


def enrolled(db, user, course_id):
    enrollment=db.query(Enrollment).filter(Enrollment.user_id==user.id,Enrollment.course_id==course_id,Enrollment.enrollment_status.in_(['enrolled','completed'])).first()
    course=db.query(Course).filter(Course.id==course_id,Course.post_status.in_(['publish','published'])).first()
    if not course or not enrollment:
        raise HTTPException(403, 'An active enrollment in a published course is required.')
    return course


def lesson_version(lesson):
    return revision({k:getattr(lesson,k,None) for k in ('id','post_title','post_content','post_status','lesson_content_type','virtual_lab_sim','three_d_model_id')})


def manifest(db,user,course_id):
    course=enrolled(db,user,course_id)
    lessons=db.query(Lesson).filter(Lesson.post_parent==course_id,Lesson.post_status.in_(['publish','published'])).order_by(Lesson.id).limit(101).all()
    if len(lessons)>100:raise HTTPException(422,'Offline packs support up to 100 lessons per course.')
    from app.routers.virtual_labs import get_lab, _public
    entries=[]
    for lesson in lessons:
        lab=get_lab(db,lesson.virtual_lab_sim) if lesson.virtual_lab_sim else None
        detail=_public(lab,True) if lab else None
        if detail and detail.get('provider') != 'native' and not (detail.get('embed_url') or '').startswith('/labs/cbse/'):
            detail=None
        entries.append({'id':lesson.id,'title':lesson.post_title,'text':text_only(lesson.post_content)[:200000], 'revision':lesson_version(lesson), 'lab':detail, 'model_id':lesson.three_d_model_id, 'online_media':bool(lesson.lesson_video_url or lesson.lesson_attachment_url)})
    return {'course_id':course_id,'title':course.post_title,'owner_id':user.id,'lessons':entries,'valid_days':7}
