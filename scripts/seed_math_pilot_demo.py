"""Synthetic pilot examples; invoked only by the isolated SaaS demo seeder."""
from datetime import timedelta
from uuid import uuid4


def seed_math_pilot(db, teacher, users):
    if db.bind.dialect.name != 'sqlite' or 'saas-demo' not in str(db.bind.url):
        raise RuntimeError('Math demo seeding is restricted to the local SaaS demo database.')
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.math_pilot import MathPilotPolicy, MathPilotSession
    from app.routers.math_pilot import AnswerIn
    from app.services import math_pilot as svc
    course = db.query(Course).filter_by(post_name='demo-volume-pilot').first()
    if not course:
        course = Course(post_author=teacher.id, post_title='DEMO: Volume discovery pilot',
                        post_name='demo-volume-pilot', post_status='publish', course_price=0,
                        course_type='meiporul', post_content='Synthetic pilot examples; not classroom efficacy evidence.')
        db.add(course); db.flush()
    if not db.get(MathPilotPolicy, course.id):
        db.add(MathPilotPolicy(course_id=course.id, version=svc.VERSION, reviewed_by=teacher.id,
            review_note='SYNTHETIC LOCAL DEMO approval only. Not an educator or school privacy sign-off.', reviewed_at=svc.now()))
    for index in range(3):
        student = users.get(f'campus-student-{index}@example.org')
        if not student:
            continue
        if not db.query(Enrollment).filter_by(user_id=student.id, course_id=course.id).first():
            db.add(Enrollment(user_id=student.id, course_id=course.id, enrollment_status='enrolled'))
        db.commit()
        # Preserve a user's demo progress on subsequent seed runs.
        if db.query(MathPilotSession).filter_by(user_id=student.id, course_id=course.id, version=svc.VERSION).first():
            continue
        state = svc.start(db, course.id, student)
        if index == 0:
            continue
        for values in ([[0], [6, 6]] if index == 1 else [[1], [6, 24], [4, 24], [24, 15]]):
            row = svc.own(db, state['id'], student)
            body = AnswerIn(key=uuid4(), version=svc.VERSION, sequence=row.sequence, stage=state['stage'], answers=values)
            state = svc.submit(db, row, body, student)
        if index == 2:
            # Explicit synthetic time travel, never used in real learner flows.
            row = svc.own(db, state['id'], student)
            row.due_at = svc.now()-timedelta(seconds=1); db.commit()
    return course.id
