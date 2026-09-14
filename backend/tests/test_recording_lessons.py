"""Access, job recovery, publication and source-grounded recording drafts."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import pytest
from app.core.security import create_access_token
from app.models.course import Course, Lesson
from app.models.live_class import LiveClass
from app.models.live_class_report import ClassReport
from app.models.recording_lesson import RecordingLesson
from app.models.mastery import CourseOutcome, ConceptLink
from app.models.enrollment import Enrollment
from app.models.assessment_studio import StudioQuestion
from app.services import recording_lesson_service as svc, transcription_provider as provider


@pytest.fixture
def world(db, make_user, student_user):
    from app.models.user import InstructorProfile
    teacher = make_user(role="instructor", email="recording@example.com")
    db.add(InstructorProfile(user_id=teacher.id, is_approved=True))
    course = Course(post_author=teacher.id, post_title="Recording course", post_status="publish")
    db.add(course); db.flush()
    now = datetime.now(timezone.utc)
    lc = LiveClass(course_id=course.id, instructor_id=teacher.id, title="Fractions class", room_name="si-recordingtest",
                   scheduled_start=now, scheduled_end=now + timedelta(hours=1), ended_at=now)
    db.add(lc); db.flush()
    db.add(ClassReport(class_id=lc.id, course_id=course.id, instructor_id=teacher.id, title=lc.title))
    db.add(CourseOutcome(course_id=course.id, target_concepts=["fractions"]))
    db.add(Enrollment(user_id=student_user.id, course_id=course.id, enrollment_status="enrolled"))
    db.commit()
    return teacher, course, lc


def auth(client, user):
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": str(user.id)})


def transcript():
    return {"language": "en", "segments": [{"start": 0, "end": 8, "text": "Fractions describe equal parts of a whole."},
                                           {"start": 190, "end": 198, "text": "Equivalent fractions name the same amount."}]}


def ready(db, world):
    row = RecordingLesson(class_id=world[2].id, title=world[2].title, source_path="private/path.mp4")
    db.add(row); db.flush(); svc.apply_transcript(db, row, transcript()); db.commit()
    return row


def test_drafts_private_until_curriculum_publication(client, db, world, student_user):
    row = ready(db, world); url = f"/api/v1/recording-lessons/{row.class_id}"
    auth(client, student_user)
    assert client.get(url).status_code == 403
    assert client.get(url + '/reader').status_code == 403
    auth(client, world[0])
    detail = client.get(url).json()['work']
    assert 'source_path' not in detail and 'private/path' not in str(detail)
    response = client.post(url + '/create-lesson', json={'version': row.version})
    assert response.status_code == 200, response.text
    lesson_id = response.json()['lesson_id']; lesson = db.get(Lesson, lesson_id)
    assert lesson.post_status == 'draft'
    assert 'class_report:' in lesson.post_excerpt and '/recordings/' in lesson.post_content
    assert db.query(ConceptLink).filter_by(kind='lesson', ref_id=str(lesson_id), concept='fractions').count() == 1
    assert db.query(ClassReport).one().transcript is None  # no private draft leaked through old report API
    auth(client, student_user)
    assert client.get(url + '/reader').status_code == 403
    lesson.post_status = 'publish'; db.commit()
    response = client.get(url + '/reader')
    assert response.status_code == 200 and 'suggestions' not in response.json()
    assert 'source_path' not in response.json()
    world[1].post_status = 'draft'; db.commit()
    assert client.get(url + '/reader').status_code == 403


def test_other_instructors_and_unenrolled_cannot_read(client, db, world, make_user):
    row = ready(db, world)
    from app.models.user import InstructorProfile
    other = make_user(role='instructor', email='foreignrecording@example.com')
    db.add(InstructorProfile(user_id=other.id, is_approved=True)); db.commit()
    auth(client, other)
    assert client.get('/api/v1/recording-lessons').json()['classes'] == []
    assert client.get(f'/api/v1/recording-lessons/{row.class_id}').status_code == 403
    assert client.post(f'/api/v1/recording-lessons/{row.class_id}/create-lesson', json={'version': 1}).status_code == 403


def test_questions_are_exact_excerpt_drafts_and_idempotent(client, db, world):
    row = ready(db, world); auth(client, world[0]); url = f'/api/v1/recording-lessons/{row.class_id}/assessment-drafts'
    r = client.post(url, json={'version': row.version}); assert r.status_code == 200, r.text
    assert len(r.json()['question_ids']) == 1
    question = db.query(StudioQuestion).one()
    assert question.status == 'draft' and question.published_snapshot is None
    again = client.post(url, json={'version': r.json()['version']})
    assert again.status_code == 200 and db.query(StudioQuestion).count() == 1
    assert client.post(url, json={'version': 1}).status_code == 409


def test_edit_corrects_transcript_and_rejects_timestamp_tampering(client, db, world):
    row = ready(db, world); auth(client, world[0]); url = f'/api/v1/recording-lessons/{row.class_id}'
    body = {'version': row.version, 'title': '<script>title</script>', 'notes': '<script>bad</script> These are reviewed notes.',
            'chapters': [{'start': 0, 'title': '<img onerror=bad>'}], 'concepts': ['fractions'], 'segments': transcript()['segments']}
    body['segments'][0]['text'] = 'Fractions represent equal parts of a whole.'
    r = client.put(url, json=body); assert r.status_code == 200, r.text
    assert 'represent' in r.json()['segments'][0]['text']
    body['version'] = r.json()['version']; body['segments'][0]['start'] = 2
    assert client.put(url, json=body).status_code == 422
    r = client.post(url + '/create-lesson', json={'version': body['version']}); assert r.status_code == 200, r.text
    lesson = db.get(Lesson, r.json()['lesson_id'])
    assert '<script>' not in lesson.post_content and '&lt;script&gt;' in lesson.post_content
    assert client.put(url, json={**body, 'version': r.json()['version']}).status_code == 409


def test_duplicate_lesson_creation_returns_existing(client, db, world):
    row = ready(db, world); auth(client, world[0]); url = f'/api/v1/recording-lessons/{row.class_id}/create-lesson'
    first = client.post(url, json={'version': row.version}).json()
    second = client.post(url, json={'version': first['version']}).json()
    assert first['lesson_id'] == second['lesson_id'] and db.query(Lesson).count() == 1


def test_worker_success_and_no_duplicate_claim(db, world, TestingSessionLocal, monkeypatch, tmp_path):
    row = RecordingLesson(class_id=world[2].id, title='Class', source_path='source.mp4'); db.add(row); db.commit()
    monkeypatch.setattr(provider, 'configuration', lambda: {'configured': True})
    monkeypatch.setattr(svc, 'source_for', lambda *a: tmp_path / 'source.mp4')
    calls = []
    monkeypatch.setattr(provider, 'transcribe', lambda *a: calls.append(a) or transcript())
    assert svc.run_one(TestingSessionLocal)
    assert not svc.run_one(TestingSessionLocal)
    db.expire_all(); assert row.status == 'draft' and row.attempts == 1 and len(calls) == 1
    assert len(row.chapters) == 2 and row.concepts == ['fractions']


def test_worker_failure_recovery_and_no_automatic_infinite_retry(db, world, TestingSessionLocal, monkeypatch):
    row = RecordingLesson(class_id=world[2].id, title='Class', source_path='source.mp4'); db.add(row); db.commit()
    monkeypatch.setattr(provider, 'configuration', lambda: {'configured': True})
    monkeypatch.setattr(svc, 'source_for', lambda *a: Path('source.mp4'))
    def fail(*args):
        raise RuntimeError('private internal path or secret')
    monkeypatch.setattr(provider, 'transcribe', fail)
    assert svc.run_one(TestingSessionLocal)
    db.expire_all(); assert row.status == 'failed' and 'private internal' not in row.error
    assert not svc.run_one(TestingSessionLocal)
    row.status = 'processing'; row.started_at = svc.utcnow() - timedelta(hours=2); db.commit()
    assert not svc.run_one(TestingSessionLocal)
    db.expire_all(); assert row.status == 'failed' and 'interrupted' in row.error


def test_missing_local_configuration_is_503_and_no_job(client, db, world, monkeypatch):
    monkeypatch.setattr(provider, 'configuration', lambda: {'configured': False, 'note': 'Install the local runtime.'})
    auth(client, world[0])
    assert client.post(f'/api/v1/recording-lessons/{world[2].id}/transcribe', json={'language': 'ta'}).status_code == 503
    assert db.query(RecordingLesson).count() == 0


def test_source_rejects_other_rooms_traversal_and_deleted(db, world, tmp_path, monkeypatch):
    from app.services import live_recording_service
    monkeypatch.setattr(live_recording_service.settings, 'JITSI_RECORDINGS_DIR', str(tmp_path))
    lc = world[2]
    other = tmp_path / 'si-another' / 'recording.mp4'; other.parent.mkdir(); other.write_bytes(b'test')
    for path in (str(other), str(tmp_path / '..' / 'outside.mp4')):
        with pytest.raises(ValueError): svc.source_for(lc, path)
    correct = tmp_path / lc.room_name / 'recording.mp4'; correct.parent.mkdir(); correct.write_bytes(b'test')
    assert svc.source_for(lc, str(correct)) == correct
    lc.recording_deleted_at = svc.utcnow()
    with pytest.raises(ValueError): svc.source_for(lc, str(correct))


@pytest.mark.parametrize('segments', [[], [{'start': -1, 'end': 4, 'text': 'text'}], [{'start': 5, 'end': 4, 'text': 'text'}], [{'start': 0, 'end': float('inf'), 'text': 'text'}]])
def test_invalid_asr_outputs_never_become_drafts(db, world, segments):
    row = RecordingLesson(class_id=world[2].id)
    with pytest.raises(ValueError): svc.apply_transcript(db, row, {'segments': segments})


def test_migration_matches_model():
    path = Path(__file__).parents[1] / 'alembic/versions/0023_recording_lessons.py'
    spec = importlib.util.spec_from_file_location('recording_migration', path); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    frozen = module.schema().tables['recording_lessons']
    assert list(frozen.columns.keys()) == list(RecordingLesson.__table__.columns.keys())
    assert module.down_revision == '0022'


def test_published_recording_enters_planner_but_draft_does_not(db, world, student_user):
    from app.models.learning_planner import LearningGoal, LearningPlanTask
    from app.services.learning_planner_service import refresh_goal
    row = ready(db, world)
    lesson = svc.create_lesson(db, row, world[2], world[0]); db.commit()
    goal = LearningGoal(user_id=student_user.id, course_id=world[1].id, title="Review the recording",
                        target_date=(svc.utcnow() + timedelta(days=30)).date(), daily_minutes=30, timezone="UTC")
    db.add(goal); db.commit()
    refresh_goal(db, goal)
    assert db.query(LearningPlanTask).filter_by(goal_id=goal.id, lesson_id=lesson.id).count() == 0
    lesson.post_status = 'publish'; db.commit(); refresh_goal(db, goal)
    tasks = db.query(LearningPlanTask).filter_by(goal_id=goal.id, lesson_id=lesson.id).all()
    assert len(tasks) == 1 and tasks[0].kind == 'lesson' and tasks[0].status == 'pending'
    from app.models.mastery import MasteryEvidence
    assert db.query(MasteryEvidence).count() == 0


def test_reader_rechecks_enrollment_and_lesson_course(client, db, world, student_user):
    row = ready(db, world)
    lesson = svc.create_lesson(db, row, world[2], world[0]); lesson.post_status = 'publish'; db.commit()
    auth(client, student_user); url=f'/api/v1/recording-lessons/{row.class_id}/reader'
    assert client.get(url).status_code == 200
    enrollment = db.query(Enrollment).filter_by(user_id=student_user.id,course_id=world[1].id).one()
    enrollment.enrollment_status = 'cancelled'; db.commit()
    assert client.get(url).status_code == 403
    enrollment.enrollment_status = 'enrolled'
    other = Course(post_author=world[0].id,post_title='Other course'); db.add(other); db.flush()
    lesson.post_parent = other.id; db.commit()
    assert client.get(url).status_code == 403
