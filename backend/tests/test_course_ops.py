"""R6 instructor growth tools: deep course clone (lessons, quizzes+answers,
assignments, sections_meta remap, studio settings), templates, CSV quiz
import (all-or-nothing with row errors), co-instructors editing through the
single can_edit rule and appearing in my-courses.
"""
import json

import pytest

from app.models.course import Course, Lesson
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="ops-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def other(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="ops-other@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def other_headers(client, other, auth_headers):
    return auth_headers(other.user_email)


@pytest.fixture
def course(db, instructor):
    c = Course(post_title="Source course", post_content="body", post_excerpt="p", post_status="publish", post_author=instructor.id,
               course_price=199, course_type="utporul", course_tags='["trig", "class10"]')
    db.add(c)
    db.commit()
    db.refresh(c)
    l1 = Lesson(post_author=instructor.id, post_parent=c.id, post_title="L1", post_status="publish", post_type="lesson", menu_order=1,
                lesson_content_type="video", lesson_video_url="https://cdn/x.mp4", lesson_preview=True)
    l2 = Lesson(post_author=instructor.id, post_parent=c.id, post_title="L2 3D", post_status="publish", post_type="lesson", menu_order=2,
                lesson_content_type="three_d", three_d_model_id=3)
    q = Quiz(post_author=instructor.id, post_parent=c.id, post_title="Q1", quiz_passing_grade=60, interactive_modules=[{"kind": "game", "id": 1}])
    db.add_all([l1, l2, q])
    db.commit()
    qq = QuizQuestion(quiz_id=q.id, question_title="2+2?", question_type="multiple_choice", question_mark=2, question_order=1)
    db.add(qq)
    db.commit()
    db.add_all([QuizQuestionAnswer(belongs_question_id=qq.question_id, answer_title="3", is_correct=False, answer_order=1),
                QuizQuestionAnswer(belongs_question_id=qq.question_id, answer_title="4", is_correct=True, answer_order=2)])
    c.course_sections_meta = json.dumps([{"id": "s1", "title": "Week 1", "lectureIds": [f"lesson-{l1.id}", f"lesson-{l2.id}", f"quiz-{q.id}"]}])
    db.commit()
    return c


def test_clone_is_a_deep_draft_copy(client, db, course, headers, other_headers):
    assert client.post(f"/api/v1/course-ops/courses/{course.id}/clone", headers=other_headers, json={}).status_code == 403
    r = client.post(f"/api/v1/course-ops/courses/{course.id}/clone", headers=headers, json={"title": "Source course — batch 2"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft" and body["copied"] == {"lessons": 2, "quizzes": 1, "assignments": 0}
    new = db.query(Course).filter(Course.id == body["id"]).first()
    assert new.post_title == "Source course — batch 2" and new.course_tags == '["trig", "class10"]' and new.course_price == 199
    lessons = db.query(Lesson).filter(Lesson.post_parent == new.id).order_by(Lesson.menu_order).all()
    assert [l.post_title for l in lessons] == ["L1", "L2 3D"] and lessons[1].three_d_model_id == 3 and lessons[0].lesson_preview is True
    quiz = db.query(Quiz).filter(Quiz.post_parent == new.id).one()
    assert quiz.quiz_passing_grade == 60 and quiz.interactive_modules == [{"kind": "game", "id": 1}]
    answers = (db.query(QuizQuestionAnswer).join(QuizQuestion, QuizQuestion.question_id == QuizQuestionAnswer.belongs_question_id)
               .filter(QuizQuestion.quiz_id == quiz.id).all())
    assert sorted((a.answer_title, a.is_correct) for a in answers) == [("3", False), ("4", True)]
    meta = json.loads(new.course_sections_meta)
    assert meta[0]["lectureIds"] == [f"lesson-{lessons[0].id}", f"lesson-{lessons[1].id}", f"quiz-{quiz.id}"]
    # the original is untouched
    assert db.query(Lesson).filter(Lesson.post_parent == course.id).count() == 2


def test_templates_flow(client, db, course, headers, other_headers, other):
    assert client.get("/api/v1/course-ops/templates", headers=other_headers).json()["templates"] == []
    assert client.post(f"/api/v1/course-ops/courses/{course.id}/template", headers=other_headers, json={"is_template": True}).status_code == 403
    assert client.post(f"/api/v1/course-ops/courses/{course.id}/template", headers=headers, json={"is_template": True}).json()["is_template"] is True
    t = client.get("/api/v1/course-ops/templates", headers=other_headers).json()["templates"]
    assert len(t) == 1 and t[0]["lessons"] == 2
    r = client.post(f"/api/v1/course-ops/templates/{course.id}/use", headers=other_headers, json={"title": "My trig course"})
    assert r.status_code == 201 and r.json()["owner_id"] == other.id and r.json()["is_template"] is False
    mine = client.get("/api/v1/courses/my-courses", headers=other_headers).json()["courses"]
    assert any(c["post_title"] == "My trig course" for c in mine)


def test_csv_import_all_or_nothing(client, db, course, headers):
    good = ("question,type,option_a,option_b,option_c,option_d,correct,marks,explanation\n"
            "What is 2+2?,multiple_choice,3,4,5,6,B,1,Basic addition\n"
            "Water boils at 100 C at sea level,true_false,,,,,TRUE,1,\n"
            "The powerhouse of the cell is the ____,fill_in_blanks,,,,,mitochondria,2,\n")
    bad = good + "Broken row,multiple_choice,only one option,,,,A,1,\n"
    r = client.post(f"/api/v1/course-ops/courses/{course.id}/quizzes/import-csv", headers=headers,
                    files={"file": ("q.csv", bad.encode(), "text/csv")}, data={"title": "Unit test"})
    assert r.status_code == 422 and "row 5" in r.json()["detail"]["errors"][0]
    assert db.query(Quiz).filter(Quiz.post_title == "Unit test").count() == 0
    r = client.post(f"/api/v1/course-ops/courses/{course.id}/quizzes/import-csv", headers=headers,
                    files={"file": ("q.csv", good.encode(), "text/csv")}, data={"title": "Unit test", "passing_grade": "70"})
    assert r.status_code == 201, r.text
    assert r.json()["questions"] == 3
    quiz = db.query(Quiz).filter(Quiz.id == r.json()["quiz_id"]).one()
    assert quiz.quiz_passing_grade == 70
    qs = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.question_order).all()
    assert [q.question_type for q in qs] == ["multiple_choice", "true_false", "fill_in_blanks"] and qs[2].question_mark == 2
    tf = db.query(QuizQuestionAnswer).filter(QuizQuestionAnswer.belongs_question_id == qs[1].question_id).all()
    assert {(a.answer_title, a.is_correct) for a in tf} == {("True", True), ("False", False)}


def test_co_instructor_can_edit_and_sees_course(client, db, course, headers, other_headers, other, student_user):
    from app.core.security import create_access_token
    sh = {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}
    # before: the other instructor cannot touch the course
    assert client.post(f"/api/v1/courses/{course.id}/quizzes", headers=other_headers, json={"title": "Q2"}).status_code == 403
    assert client.get(f"/api/v1/studio/courses/{course.id}/settings", headers=other_headers).status_code == 403
    assert client.post(f"/api/v1/course-ops/courses/{course.id}/collaborators", headers=other_headers, json={"email": other.user_email}).status_code == 403
    assert client.post(f"/api/v1/course-ops/courses/{course.id}/collaborators", headers=headers, json={"email": student_user.user_email}).status_code == 422
    r = client.post(f"/api/v1/course-ops/courses/{course.id}/collaborators", headers=headers, json={"email": "nobody@example.com"})
    assert r.status_code == 422 and r.json()["detail"] == "No account with that email"   # not 404: the global handler would mask it
    r = client.post(f"/api/v1/course-ops/courses/{course.id}/collaborators", headers=headers, json={"email": other.user_email})
    assert r.status_code == 201 and r.json()["created"] is True and r.json()["collaborators"][0]["user_id"] == other.id
    # after: can edit through the shared rule, appears in my-courses, still cannot manage collaborators
    assert client.post(f"/api/v1/courses/{course.id}/quizzes", headers=other_headers, json={"title": "Q2"}).status_code in (200, 201)
    assert client.get(f"/api/v1/studio/courses/{course.id}/settings", headers=other_headers).status_code == 200
    assert client.get(f"/api/v1/mastery/courses/{course.id}/coverage", headers=other_headers).status_code == 200
    mine = client.get("/api/v1/courses/my-courses", headers=other_headers).json()["courses"]
    assert any(c["id"] == course.id for c in mine)
    assert client.get("/api/v1/course-ops/courses/%d/collaborators" % course.id, headers=sh).status_code == 403
    assert client.delete(f"/api/v1/course-ops/courses/{course.id}/collaborators/{other.id}", headers=other_headers).status_code == 403
    assert client.delete(f"/api/v1/course-ops/courses/{course.id}/collaborators/{other.id}", headers=headers).json()["removed"] == other.id
    assert client.get(f"/api/v1/studio/courses/{course.id}/settings", headers=other_headers).status_code == 403
