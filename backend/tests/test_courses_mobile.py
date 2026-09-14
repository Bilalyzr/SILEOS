from app.models.course import Course, Lesson


def _make_course_with_lesson(db, instructor, status="published", preview=True):
    course = Course(
        post_author=instructor.id,
        post_title="Mobile Course",
        post_content="Course content",
        post_excerpt="Course excerpt",
        post_status=status,
        post_name="mobile-course",
        course_thumbnail="",
        course_price=0,
        course_level="beginner",
        course_category="Meiporul",
        course_language="English",
        course_duration="10",
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    lesson = Lesson(
        post_author=instructor.id,
        post_parent=course.id,
        post_title="Mobile Lesson",
        post_content="Lesson content",
        post_status="publish",
        menu_order=1,
        lesson_video_url="https://example.com/video.mp4",
        lesson_youtube_url="",
        lesson_video_duration="120",
        lesson_preview=preview,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return course, lesson


def test_mobile_course_list_includes_published_status(client, db, make_user):
    instructor = make_user(role="instructor", email="instructor@example.com")
    _make_course_with_lesson(db, instructor, status="published")

    response = client.get("/api/v1/courses/")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert data["courses"][0]["title"] == "Mobile Course"


def test_mobile_course_detail_lesson_shape(client, db, make_user):
    instructor = make_user(role="instructor", email="instructor@example.com")
    course, lesson = _make_course_with_lesson(db, instructor)

    response = client.get(f"/api/v1/courses/{course.id}")

    assert response.status_code == 200, response.text
    lesson_data = response.json()["lessons"][0]
    assert lesson_data["id"] == lesson.id
    assert lesson_data["course_id"] == course.id
    assert lesson_data["content"] == "Lesson content"
    assert lesson_data["video_url"] == "https://example.com/video.mp4"
    assert lesson_data["video_duration"] == 120


def test_mobile_get_lesson_by_id(client, db, make_user):
    instructor = make_user(role="instructor", email="instructor@example.com")
    course, lesson = _make_course_with_lesson(db, instructor, preview=True)

    response = client.get(f"/api/v1/lessons/{lesson.id}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == lesson.id
    assert data["course_id"] == course.id
    assert data["content"] == "Lesson content"
