"""Public lesson preview + real lock (2026-09-05): the course payload strips
media/content from non-preview lessons for visitors and non-enrolled
learners (is_locked), keeps everything for enrolled / owner / admin; the
preview endpoint works logged-out for preview lessons only; published 3D
tasks are listable per model for the learner "check yourself" strip.
"""
import pytest

from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="prev-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


@pytest.fixture
def course(db, instructor):
    c = Course(post_title="Preview course", post_content="d", post_excerpt="p", post_status="publish",
               post_author=instructor.id, course_price=499, course_type="utporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    free = Lesson(post_author=instructor.id, post_parent=c.id, post_title="Free intro", post_content="Welcome text",
                  post_status="publish", post_type="lesson", menu_order=1, lesson_preview=True,
                  lesson_video_url="https://cdn.example.com/intro.mp4")
    paid = Lesson(post_author=instructor.id, post_parent=c.id, post_title="Paid deep dive", post_content="Secret text",
                  post_status="publish", post_type="lesson", menu_order=2, lesson_preview=False,
                  lesson_video_url="https://cdn.example.com/secret.mp4", lesson_content_type="video")
    db.add_all([free, paid])
    db.commit()
    return c


def _lessons(payload):
    return {l["title"]: l for l in payload["lessons"]}


def test_course_payload_strips_locked_lessons_for_visitors(client, db, course):
    r = client.get(f"/api/v1/courses/{course.id}")
    assert r.status_code == 200, r.text
    ls = _lessons(r.json())
    assert ls["Free intro"]["is_locked"] is False and ls["Free intro"]["video_url"].endswith("intro.mp4")
    assert ls["Free intro"]["is_preview"] is True and ls["Free intro"]["content"] == "Welcome text"
    locked = ls["Paid deep dive"]
    assert locked["is_locked"] is True and locked["video_url"] == "" and locked["lesson_video"] == "" and locked["content"] == ""
    assert locked["title"] == "Paid deep dive" and locked["lesson_content_type"] == "video"   # curriculum still renders


def test_enrolled_owner_and_admin_keep_full_access(client, db, course, student_user, student_headers, headers, make_user):
    # not enrolled yet -> locked
    assert _lessons(client.get(f"/api/v1/courses/{course.id}", headers=student_headers).json())["Paid deep dive"]["is_locked"] is True
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    db.commit()
    ls = _lessons(client.get(f"/api/v1/courses/{course.id}", headers=student_headers).json())
    assert ls["Paid deep dive"]["is_locked"] is False and ls["Paid deep dive"]["video_url"].endswith("secret.mp4")
    ls = _lessons(client.get(f"/api/v1/courses/{course.id}", headers=headers).json())
    assert ls["Paid deep dive"]["is_locked"] is False and ls["Paid deep dive"]["content"] == "Secret text"
    from app.core.security import create_access_token
    admin = make_user(role="admin", email="prev-admin@example.com")
    ah = {"Authorization": f"Bearer {create_access_token({'sub': str(admin.id)})}"}
    assert _lessons(client.get(f"/api/v1/courses/{course.id}", headers=ah).json())["Paid deep dive"]["is_locked"] is False


def test_public_preview_endpoint(client, db, course, student_user, student_headers, headers):
    free = db.query(Lesson).filter(Lesson.post_title == "Free intro").first()
    paid = db.query(Lesson).filter(Lesson.post_title == "Paid deep dive").first()
    # logged-out visitor
    r = client.get(f"/api/v1/courses/{course.id}/lessons/{free.id}/preview")
    assert r.status_code == 200, r.text
    assert r.json()["video_url"].endswith("intro.mp4") and r.json()["is_public_preview"] is True and r.json()["is_locked"] is False
    assert client.get(f"/api/v1/courses/{course.id}/lessons/{paid.id}/preview").status_code == 403
    assert client.get(f"/api/v1/courses/{course.id}/lessons/{paid.id}/preview", headers=student_headers).status_code == 403
    # enrolled learner and owner see the paid lesson through the same endpoint
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    db.commit()
    r = client.get(f"/api/v1/courses/{course.id}/lessons/{paid.id}/preview", headers=student_headers)
    assert r.status_code == 200 and r.json()["is_public_preview"] is False
    assert client.get(f"/api/v1/courses/{course.id}/lessons/{paid.id}/preview", headers=headers).status_code == 200
    # unpublished course: visitors get nothing, the owner still can
    course.post_status = "draft"
    db.commit()
    assert client.get(f"/api/v1/courses/{course.id}/lessons/{free.id}/preview").status_code == 403
    assert client.get(f"/api/v1/courses/{course.id}/lessons/{free.id}/preview", headers=headers).status_code == 200
    assert client.get(f"/api/v1/courses/{course.id}/lessons/999999/preview", headers=headers).status_code == 404


@pytest.mark.usefixtures("authored_native_labs")
def test_anonymous_assets_open_only_for_public_preview_lessons(client, db, course, instructor, tmp_path, monkeypatch):
    """The 3D file / lab detail / game payload are reachable logged-out ONLY
    when a public-preview lesson in a published course embeds them."""
    from app.models.three_d import ThreeDModel
    from app.routers import three_d as three_d_router
    glb = tmp_path / "m.glb"
    glb.write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 60)
    monkeypatch.setattr(three_d_router, "_resolve", lambda rel: str(glb))
    model = ThreeDModel(owner_id=instructor.id, title="Cube", file_path="x/m.glb", file_size_bytes=68, format="glb")
    db.add(model)
    db.commit()
    lesson3d = Lesson(post_author=instructor.id, post_parent=course.id, post_title="3D locked", post_status="publish", post_type="lesson",
                      menu_order=3, lesson_preview=False, lesson_content_type="three_d", three_d_model_id=model.id)
    db.add(lesson3d)
    db.commit()
    assert client.get(f"/api/v1/three-d/models/{model.id}/file").status_code == 401
    assert client.get("/api/v1/virtual-labs/fixture-reaction-lab").status_code == 401
    lesson3d.lesson_preview = True
    db.add(Lesson(post_author=instructor.id, post_parent=course.id, post_title="Lab open", post_status="publish", post_type="lesson",
                  menu_order=4, lesson_preview=True, lesson_content_type="virtual_lab", virtual_lab_sim="fixture-reaction-lab"))
    db.commit()
    assert client.get(f"/api/v1/three-d/models/{model.id}/file").status_code == 200
    r = client.get("/api/v1/virtual-labs/fixture-reaction-lab")
    assert r.status_code == 200 and r.json()["slug"] == "fixture-reaction-lab"
    # course goes back to draft -> visitors lose it again
    course.post_status = "draft"
    db.commit()
    assert client.get(f"/api/v1/three-d/models/{model.id}/file").status_code == 401


def test_tasks_for_model_lists_only_published(client, db, instructor, headers, student_headers):
    from app.models.three_d import ThreeDModel
    from app.models.three_d_task import ThreeDTask
    model = ThreeDModel(owner_id=instructor.id, title="Heart", file_path="x/h.glb", file_size_bytes=10, format="glb")
    db.add(model)
    db.commit()
    db.add_all([
        ThreeDTask(owner_id=instructor.id, model_id=model.id, title="Published", task_type="identify",
                   config={"anchors": [], "prompts": []}, concepts=[], status="published"),
        ThreeDTask(owner_id=instructor.id, model_id=model.id, title="Draft", task_type="identify",
                   config={"anchors": [], "prompts": []}, concepts=[], status="draft"),
    ])
    db.commit()
    r = client.get(f"/api/v1/three-d-tasks/for-model/{model.id}", headers=student_headers)
    assert r.status_code == 200, r.text
    assert [t["title"] for t in r.json()["tasks"]] == ["Published"] and "config" not in r.json()["tasks"][0]
    assert client.get("/api/v1/three-d-tasks/for-model/999", headers=headers).json()["tasks"] == []
