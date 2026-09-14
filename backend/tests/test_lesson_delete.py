"""
B10 — courses.py declared two `DELETE /{course_id}/lessons/{lesson_id}`
handlers (~1493 live, ~1852 dead twin). FastAPI dispatches to the first
registered route, so the second was unreachable dead code — and it was
also strictly weaker (no FK-child cleanup for LessonProgress /
StudentCourseActivity / WatchSession before deleting the lesson row).

This test locks in the LIVE handler's actual behavior: a request still
routes and deletes the lesson plus its dependent progress/activity/
watch-session rows, returning 200 with a success message.
"""
from app.models.course import Lesson
from app.models.enrollment import LessonProgress, StudentCourseActivity, WatchSession


def _lesson(db, course, order=0):
    lesson = Lesson(
        post_author=course.post_author,
        post_title="Intro",
        post_parent=course.id,
        menu_order=order,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def test_delete_lesson_routes_to_live_handler_and_cleans_fk_children(
    db, client, course, student_user, auth_headers, make_user
):
    from app.models.user import User

    instructor = db.query(User).filter(User.id == course.post_author).first()
    lesson = _lesson(db, course)

    from app.models.enrollment import Enrollment
    enrollment = Enrollment(user_id=student_user.id, course_id=course.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    db.add(LessonProgress(
        user_id=student_user.id, course_id=course.id, lesson_id=lesson.id,
        enrollment_id=enrollment.id,
    ))
    db.add(StudentCourseActivity(
        user_id=student_user.id, course_id=course.id, lesson_id=lesson.id,
        activity_type="lesson_completed",
    ))
    db.add(WatchSession(
        user_id=student_user.id, course_id=course.id, lesson_id=lesson.id,
        event="started",
    ))
    db.commit()

    instructor.user_pass = instructor.user_pass  # no-op, keep session happy
    # Log in as the course's instructor via a fresh known password.
    from app.core.security import get_password_hash
    instructor.user_pass = get_password_hash("Test@123")
    db.commit()
    headers = auth_headers(instructor.user_email, "Test@123")

    resp = client.delete(f"/api/v1/courses/{course.id}/lessons/{lesson.id}", headers=headers)

    # The live handler (~1493) returns 200 with a message body — the dead
    # twin (~1852, now deleted) returned 204. This pins the LIVE contract.
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"message": "Lesson deleted successfully"}

    assert db.query(Lesson).filter(Lesson.id == lesson.id).first() is None
    assert db.query(LessonProgress).filter(LessonProgress.lesson_id == lesson.id).count() == 0
    assert db.query(StudentCourseActivity).filter(StudentCourseActivity.lesson_id == lesson.id).count() == 0
    assert db.query(WatchSession).filter(WatchSession.lesson_id == lesson.id).count() == 0


def test_delete_lesson_404_for_unknown_lesson(db, client, course, auth_headers):
    from app.models.user import User
    from app.core.security import get_password_hash

    instructor = db.query(User).filter(User.id == course.post_author).first()
    instructor.user_pass = get_password_hash("Test@123")
    db.commit()
    headers = auth_headers(instructor.user_email, "Test@123")

    resp = client.delete(f"/api/v1/courses/{course.id}/lessons/999999", headers=headers)
    assert resp.status_code == 404
