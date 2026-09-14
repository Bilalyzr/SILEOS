"""Portable course backup, preview, authorization and transactional restore."""
import hashlib
import io
import json
import zipfile
from datetime import timedelta
import pytest
from app.core.security import create_access_token
from app.models.course import Course, Lesson
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
from app.models.enrollment import Enrollment
from app.models.operations import CourseTransfer
from app.services import course_package_service as svc

@pytest.fixture
def teacher(db, make_user, tmp_path, monkeypatch):
    from app.models.user import InstructorProfile
    user = make_user(role="instructor", email="packages@example.com")
    db.add(InstructorProfile(user_id=user.id, is_approved=True)); db.commit()
    settings = svc.get_settings()
    monkeypatch.setattr(settings, 'UPLOAD_DIR', str(tmp_path / 'uploads'))
    (tmp_path / 'uploads').mkdir()
    return user

def auth(client, user):
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(user.id)})


def test_preview_expiry_respects_database_timezone_offsets():
    from datetime import timezone
    from types import SimpleNamespace
    from unittest.mock import Mock
    from fastapi import HTTPException
    from app.routers.course_packages import transfer
    db = Mock()
    row = SimpleNamespace(status='preview', expires_at=(svc.utcnow()-timedelta(hours=1)).astimezone(timezone(timedelta(hours=5, minutes=30))))
    db.query.return_value.filter_by.return_value.first.return_value = row
    with pytest.raises(HTTPException) as error:
        transfer(db, 'id', SimpleNamespace(id=1))
    assert error.value.status_code == 410

def upload(client, payload, filename='backup.unknown'):
    return client.post('/api/v1/course-packages/inspect', files=[('files', (filename, payload))])


def test_mixed_assets_categorized_and_originals_survive_restore(client, db, teacher, tmp_path, monkeypatch):
    from PIL import Image
    from reportlab.pdfgen import canvas
    from app.models.three_d import ThreeDModel
    import struct
    auth(client, teacher)
    image = io.BytesIO(); Image.new('RGB', (8, 8), 'orange').save(image, format='PNG')
    pdf = io.BytesIO(); c = canvas.Canvas(pdf); c.drawString(50, 700, 'Physics notes'); c.save()
    body = json.dumps({'asset': {'version':'2.0'}, 'scenes': [], 'nodes': []}).encode()
    body += b' ' * ((-len(body)) % 4)
    glb = b'glTF' + struct.pack('<II', 2, 20+len(body)) + struct.pack('<II', len(body), 0x4e4f534a) + body
    monkeypatch.setattr(svc, 'model_root', lambda: tmp_path / 'models')
    response = client.post('/api/v1/course-packages/inspect', files=[('files',('diagram.png',image.getvalue())),('files',('notes.pdf',pdf.getvalue())),('files',('model.glb',glb))])
    assert response.status_code == 201, response.text
    preview=response.json()
    assert preview['preview']['categories'] == {'Image':1,'Document':1,'3D model':1}
    result=client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={})
    assert result.status_code == 200, result.text
    lessons=db.query(Lesson).order_by(Lesson.menu_order).all()
    assert '<img' in lessons[0].post_content
    assert 'Physics notes' in lessons[1].post_content
    for lesson in lessons[:2]:
        path=tmp_path / 'uploads' / lesson.lesson_attachment_url.removeprefix('/uploads/')
        assert path.is_file()
    assert lessons[2].three_d_model_id == db.query(ThreeDModel).one().id


def test_invalid_image_and_model_rejected_before_preview(client,teacher):
    auth(client,teacher)
    assert upload(client,b'not an image','broken.png').status_code==422
    assert upload(client,b'glTFbroken','broken.glb').status_code==422

def package(data, extras=None, manifest_extra=None):
    stream = io.BytesIO(); payload = json.dumps(data).encode()
    with zipfile.ZipFile(stream, 'w') as z:
        z.writestr('course.json', payload)
        z.writestr('manifest.json', json.dumps({'format':svc.FORMAT,'version':1,'course_sha256':hashlib.sha256(payload).hexdigest(),'assets':[],**(manifest_extra or {})}))
        for name, value in (extras or {}).items(): z.writestr(name, value)
    return stream.getvalue()


def test_backup_restores_quiz_3d_tasks_and_moves_retired_labs_to_lessons(client, db, teacher, tmp_path, monkeypatch):
    from app.models.three_d import ThreeDModel
    from app.models.three_d_task import ThreeDTask
    from app.routers import three_d
    from pathlib import Path
    import struct
    auth(client, teacher)
    storage = tmp_path / 'models'
    (storage / 'old-owner').mkdir(parents=True)
    monkeypatch.setattr(three_d, 'BASE_DIR', str(storage))
    body = json.dumps({'asset': {'version': '2.0'}, 'scenes': [], 'nodes': []}).encode()
    body += b' ' * (-len(body) % 4)
    raw = b'glTF' + struct.pack('<IIII', 2, 20 + len(body), len(body), 0x4e4f534a) + body
    (storage / 'old-owner/model.glb').write_bytes(raw)
    model = ThreeDModel(owner_id=teacher.id, title='Legacy Windows model', file_path='old-owner\\model.glb', format='glb', file_size_bytes=len(raw))
    db.add(model); db.flush()
    task = ThreeDTask(owner_id=teacher.id, model_id=model.id, title='Find the top', task_type='identify',
        config={'anchors':[{'id':'top','label':'Top','position':[.5,1,.5]}, {'id':'base','label':'Base','position':[.5,0,.5]}], 'prompts':[{'condition':'Highest point','anchor_id':'top'}]}, concepts=[], tier_floor='T4', status='published')
    db.add(task); db.flush()
    course = Course(post_author=teacher.id, post_title='Portable investigations', course_type='meiporul', post_status='draft')
    db.add(course); db.flush()
    db.add(Quiz(post_parent=course.id, post_author=teacher.id, post_title='Interactive quiz', interactive_modules=[
        {'kind':'three_d_task','id':task.id,'title':task.title,'max_score':10},
        {'kind':'lab','id':'reaction-lab-basics','title':'Balance equations','max_score':100}]))
    db.commit()
    response = client.get(f'/api/v1/course-packages/courses/{course.id}/backup')
    assert response.status_code == 200, response.text
    inspected = upload(client, response.content)
    assert inspected.status_code == 201, inspected.text
    restored = client.post(f"/api/v1/course-packages/previews/{inspected.json()['id']}/restore", json={})
    assert restored.status_code == 200, restored.text
    fresh = db.get(Course, restored.json()['course_id'])
    quiz = db.query(Quiz).filter_by(post_parent=fresh.id).one()
    assert len(quiz.interactive_modules) == 1
    cloned = db.get(ThreeDTask, quiz.interactive_modules[0]['id'])
    assert cloned.id != task.id and cloned.model_id != model.id and cloned.status == 'draft'
    copied_model = db.get(ThreeDModel, cloned.model_id)
    assert (storage / copied_model.file_path).read_bytes() == raw
    lesson = db.query(Lesson).filter_by(post_parent=fresh.id).one()
    assert lesson.virtual_lab_sim == 'cbse-balance-equations' and lesson.post_status == 'draft'
    assert f'lesson-{lesson.id}' in fresh.course_sections_meta
    transfer = db.get(CourseTransfer, inspected.json()['id'])
    assert any('review quiz grading' in warning for warning in transfer.warnings)

def test_document_upload_preview_then_new_draft(client, db, teacher):
    auth(client, teacher)
    response = upload(client, 'தமிழ் lesson\nA fraction is part of a whole.'.encode(), 'Fractions.txt')
    assert response.status_code == 201, response.text
    preview = response.json(); assert preview['kind'] == 'documents'
    assert db.query(Course).count() == 0
    result = client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore", json={'title':'My new course'})
    assert result.status_code == 200, result.text
    course = db.get(Course, result.json()['course_id']); lesson = db.query(Lesson).one()
    assert course.post_title == 'My new course' and course.post_status == 'draft'
    assert lesson.post_parent == course.id and 'தமிழ்' in lesson.post_content
    repeat = client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore", json={})
    assert repeat.json()['already_restored'] and db.query(Course).count() == 1


def test_expired_cleanup_preserves_active_files_and_restored_course(client, db, teacher):
    auth(client, teacher)
    expired = upload(client, b'Old lesson', 'Old.txt').json()
    current = upload(client, b'Current lesson', 'Current.txt').json()
    restored = upload(client, b'Restored lesson', 'Restored.txt').json()
    result = client.post(f"/api/v1/course-packages/previews/{restored['id']}/restore", json={}).json()
    for ident in (expired['id'], restored['id']):
        db.get(CourseTransfer, ident).expires_at = svc.utcnow() - timedelta(hours=1)
    db.commit()
    assert svc.cleanup_expired(db) == 2
    db.expire_all()
    assert not (svc.root()/expired['id']).exists()
    assert (svc.root()/current['id']/'upload.bin').is_file()
    assert db.get(CourseTransfer, restored['id']).staging_cleaned_at is not None
    assert db.get(Course, result['course_id']) is not None
    assert svc.cleanup_expired(db) == 0
    again = client.post(f"/api/v1/course-packages/previews/{restored['id']}/restore", json={})
    assert again.status_code == 200 and again.json()['already_restored']


def test_game_h5p_geogebra_and_tool_selections_roundtrip(client, db, teacher, tmp_path):
    from app.models.game import Game
    from app.models.h5p import H5PContent
    from app.models.geogebra import GeoGebraApplet
    auth(client, teacher)
    course = Course(post_author=teacher.id, post_title='Interactive source', course_price_type='free', enabled_tools=['virtual_labs'])
    game = Game(owner_id=teacher.id, title='Pairs', template='match_pairs', config={'items':[{'left':'one','right':'1'},{'left':'two','right':'2'},{'left':'three','right':'3'}]}, status='draft')
    h5p = H5PContent(owner_id=teacher.id, public_id='portable-source', title='Interactive content', status='ready', size_bytes=64)
    applet = GeoGebraApplet(owner_id=teacher.id, title='Geometry', app_type='geometry', material_id='example', config={})
    db.add_all([course, game, h5p, applet]); db.flush()
    folder = tmp_path/'uploads'/'h5p'/'portable-source'; folder.mkdir(parents=True)
    (folder/'h5p.json').write_text('{"mainLibrary":"H5P.InteractiveVideo 1.22"}', encoding='utf-8')
    (folder/'content').mkdir(); (folder/'content'/'content.json').write_text('{}', encoding='utf-8')
    for name, field, ident in [('Pairs','game_id',game.id),('H5P','h5p_content_id',h5p.id),('Geometry','geogebra_applet_id',applet.id)]:
        db.add(Lesson(post_parent=course.id, post_author=teacher.id, post_title=name, **{field:ident}))
    db.commit()
    response = client.get(f'/api/v1/course-packages/courses/{course.id}/backup')
    assert response.status_code == 200, response.text
    inspected = upload(client, response.content)
    assert inspected.status_code == 201, inspected.text
    preview = inspected.json()
    restored = client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={})
    assert restored.status_code == 200, restored.text
    fresh = db.get(Course,restored.json()['course_id'])
    assert fresh.enabled_tools == ['virtual_labs']
    lessons = {lesson.post_title:lesson for lesson in fresh.lessons}
    assert lessons['Pairs'].game_id != game.id
    assert db.get(Game,lessons['Pairs'].game_id).config['items'][0]['left'] == 'one'
    assert lessons['Geometry'].geogebra_applet_id != applet.id
    cloned_h5p = db.get(H5PContent,lessons['H5P'].h5p_content_id)
    assert cloned_h5p.public_id != h5p.public_id
    assert (tmp_path/'uploads'/'h5p'/cloned_h5p.public_id/'content'/'content.json').is_file()


def test_duplicate_question_ids_across_quizzes_are_rejected(client, teacher):
    auth(client, teacher)
    data = {'course':{'post_title':'Ambiguous questions'},'quizzes':[
        {'id':i,'data':{'post_title':f'Quiz {i}'},'questions':[{'id':5,'data':{'question_title':'One?'}}]} for i in (1,2)]}
    response = upload(client, package(data))
    assert response.status_code == 422

def test_export_restore_remaps_answers_sections_assets_without_learners(client, db, teacher, student_user):
    auth(client, teacher)
    asset = svc.get_settings().UPLOAD_DIR + '/notes.txt'
    from pathlib import Path
    Path(asset).write_text('local resource', encoding='utf-8')
    course = Course(post_author=teacher.id, post_title='Source', post_status='publish')
    db.add(course); db.flush()
    lesson = Lesson(post_parent=course.id, post_author=teacher.id, post_title='Lesson', post_content='<p>Safe<script>alert(1)</script></p>', lesson_attachment_url='/uploads/notes.txt')
    quiz = Quiz(post_parent=course.id, post_author=teacher.id, post_title='Quiz')
    db.add_all([lesson, quiz]); db.flush()
    question = QuizQuestion(quiz_id=quiz.id, question_title='HTML paragraph tag?', question_type='short_answer')
    db.add(question); db.flush()
    db.add(QuizQuestionAnswer(belongs_question_id=question.question_id, answer_title='<p>', is_correct=True))
    course.course_sections_meta = json.dumps([{'id':'section-1','title':'Unit','lectureIds':[f'lesson-{lesson.id}',f'quiz-{quiz.id}']}])
    db.add(Enrollment(user_id=student_user.id, course_id=course.id)); db.commit()
    exported = client.get(f'/api/v1/course-packages/courses/{course.id}/backup')
    assert exported.status_code == 200, exported.text
    preview = upload(client, exported.content)
    assert preview.status_code == 201, preview.text
    assert preview.json()['kind'] == 'backup'
    result = client.post(f"/api/v1/course-packages/previews/{preview.json()['id']}/restore", json={})
    assert result.status_code == 200, result.text
    restored = db.get(Course, result.json()['course_id'])
    newlesson = db.query(Lesson).filter_by(post_parent=restored.id).one()
    newquiz = db.query(Quiz).filter_by(post_parent=restored.id).one()
    assert restored.id != course.id and restored.post_status == 'draft'
    assert '<script>' not in newlesson.post_content and newlesson.post_status == 'draft'
    assert newlesson.lesson_attachment_url.startswith('/uploads/course-restores/')
    assert Path(svc.get_settings().UPLOAD_DIR, newlesson.lesson_attachment_url.removeprefix('/uploads/')).read_text() == 'local resource'
    assert json.loads(restored.course_sections_meta)[0]['lectureIds'] == [f'lesson-{newlesson.id}', f'quiz-{newquiz.id}']
    assert newquiz.questions[0].answers[0].answer_title == '<p>'
    assert db.query(Enrollment).filter_by(course_id=restored.id).count() == 0

@pytest.mark.parametrize('name', ['../escape.txt','C:/escape.txt','assets/../../bad.txt','assets\\bad.txt'])
def test_unsafe_archives_rejected(client, teacher, name):
    auth(client, teacher)
    payload = package({'course':{'post_title':'Bad'}}, {name.replace(chr(92), '/'):b'bad'})
    if chr(92) in name: payload = payload.replace(name.replace(chr(92), '/').encode(), name.encode())
    response = upload(client, payload)
    assert response.status_code == 422

def test_changed_staged_backup_rejected(client, db, teacher):
    auth(client, teacher)
    preview = upload(client, package({'course':{'post_title':'Original'}})).json()
    (svc.root()/preview['id']/'upload.bin').write_bytes(package({'course':{'post_title':'Tampered'}}))
    result = client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore", json={})
    assert result.status_code == 422 and db.query(Course).count() == 0

def test_student_foreign_teacher_and_discard(client, db, teacher, student_user, make_user):
    auth(client, student_user)
    assert upload(client,b'Hello','Lesson.txt').status_code == 403
    auth(client, teacher)
    preview = upload(client,b'Hello','Lesson.txt').json()
    other = make_user(role='instructor',email='otherpackage@example.com')
    from app.models.user import InstructorProfile
    db.add(InstructorProfile(user_id=other.id,is_approved=True)); db.commit()
    auth(client, other)
    assert client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={}).status_code == 404
    auth(client, teacher)
    assert client.delete(f"/api/v1/course-packages/previews/{preview['id']}").status_code == 200
    assert client.get('/api/v1/course-packages/previews').json()['previews'] == []
    assert client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={}).status_code == 409

def test_failed_dependency_rolls_back_course_and_assets(client, db, teacher):
    auth(client,teacher)
    data={'course':{'post_title':'Missing game'},'lessons':[{'id':1,'data':{'post_title':'Game','game_id':998}}]}
    preview=upload(client,package(data)).json()
    result=client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={})
    assert result.status_code == 422 and db.query(Course).count()==0
    db.expire_all(); assert db.get(CourseTransfer,preview['id']).status == 'preview'

def test_expired_preview(client,db,teacher):
    auth(client,teacher); preview=upload(client,b'Hello','Lesson.txt').json()
    row=db.get(CourseTransfer,preview['id']); row.expires_at=svc.utcnow()-timedelta(seconds=1); db.commit()
    assert client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={}).status_code==410


def test_video_upload_and_tampered_media(client, db, teacher):
    auth(client, teacher)
    assert upload(client,b'plain text','bad.mp4').status_code == 422
    payload = bytes.fromhex('000000186674797069736f6d00000200')
    preview = upload(client,payload,'Lecture.mp4').json()
    result=client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={})
    assert result.status_code==200, result.text
    lesson=db.query(Lesson).one()
    assert lesson.lesson_video_source=='html5' and lesson.lesson_video_url.endswith('.mp4')
    preview=upload(client,payload,'Lecture.mp4').json()
    (svc.root()/preview['id']/'upload.bin').write_bytes(b'changed')
    assert client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore",json={}).status_code==422
    assert db.query(Course).count()==1


def test_glb_course_asset_roundtrip(client, db, teacher, tmp_path, monkeypatch):
    import struct
    from app.models.three_d import ThreeDModel
    auth(client, teacher)
    base = tmp_path/'three_d'; base.mkdir()
    monkeypatch.setattr(svc, 'model_root', lambda: base)
    document = json.dumps({'asset': {'version': '2.0'}, 'scenes': [{}], 'scene': 0}).encode()
    document += b' ' * ((-len(document)) % 4)
    blob = struct.pack('<4sII', b'glTF', 2, 20 + len(document)) + struct.pack('<I4s', len(document), b'JSON') + document
    (base/'source.glb').write_bytes(blob)
    model = ThreeDModel(owner_id=teacher.id, title='Portable model', file_path='source.glb', file_size_bytes=len(blob))
    course = Course(post_author=teacher.id, post_title='3D course', course_type='meiporul')
    db.add_all([model, course]); db.flush()
    db.add(Lesson(post_author=teacher.id, post_parent=course.id, post_title='Model', three_d_model_id=model.id)); db.commit()
    payload = client.get(f'/api/v1/course-packages/courses/{course.id}/backup')
    assert payload.status_code == 200, payload.text
    preview = upload(client, payload.content).json()
    result = client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore", json={})
    assert result.status_code == 200, result.text
    lesson = db.query(Lesson).filter_by(post_parent=result.json()['course_id']).one()
    restored = db.get(ThreeDModel, lesson.three_d_model_id)
    assert restored.id != model.id and restored.owner_id == teacher.id
    assert (base/restored.file_path).read_bytes() == blob


def test_cleanup_reclaims_old_orphan_upload_but_keeps_new_upload(client, db, teacher):
    import os
    auth(client, teacher)
    old = upload(client, b'Old orphan', 'Old.txt').json()
    new = upload(client, b'New orphan', 'New.txt').json()
    for ident in (old['id'], new['id']): db.delete(db.get(CourseTransfer, ident))
    db.commit()
    old_folder = svc.root()/old['id']
    expired = (svc.utcnow()-timedelta(hours=25)).timestamp()
    for file in old_folder.iterdir(): os.utime(file, (expired, expired))
    os.utime(old_folder, (expired, expired))
    assert svc.cleanup_expired(db) == 1
    assert not old_folder.exists()
    assert (svc.root()/new['id']/'upload.bin').is_file()


def test_authored_lab_is_portable_with_course(client, db, teacher, tmp_path, monkeypatch):
    from app.models.content_library import VirtualLabCatalog
    from app.models.three_d import ThreeDModel
    from tests.test_lab_models import glb
    from tests.test_lab_studio import draft
    model_dir = tmp_path / 'lab-models'; model_dir.mkdir()
    (model_dir / 'original.glb').write_bytes(glb())
    monkeypatch.setattr(svc, 'model_root', lambda: model_dir)
    model = ThreeDModel(owner_id=teacher.id, title='Lab geometry', file_path='original.glb', file_size_bytes=len(glb()), format='glb')
    db.add(model); db.commit()
    auth(client, teacher)
    payload = draft(); payload['config']['model_id'] = model.id
    created = client.post('/api/v1/lab-studio/drafts', json=payload).json()
    course = Course(post_author=teacher.id, post_title='Course with custom investigation')
    db.add(course); db.flush()
    db.add(Lesson(post_author=teacher.id, post_parent=course.id, post_title='Investigate', lesson_content_type='virtual_lab', virtual_lab_sim=created['slug']))
    db.commit()
    response = client.get(f'/api/v1/course-packages/courses/{course.id}/backup')
    assert response.status_code == 200, response.text
    preview = upload(client, response.content).json()
    result = client.post(f"/api/v1/course-packages/previews/{preview['id']}/restore", json={})
    assert result.status_code == 200, result.text
    lesson = db.query(Lesson).filter_by(post_parent=result.json()['course_id']).one()
    assert lesson.virtual_lab_sim != created['slug']
    lab = db.query(VirtualLabCatalog).filter_by(slug=lesson.virtual_lab_sim).one()
    assert not lab.is_published and lab.created_by == teacher.id
    assert lab.config['explanation'] == created['config']['explanation']
    assert lab.config['model_id'] != model.id
    restored_model = db.get(ThreeDModel, lab.config['model_id'])
    assert restored_model.owner_id == teacher.id
    assert (model_dir / restored_model.file_path).read_bytes() == glb()
    assert client.get(f'/api/v1/virtual-labs/{lab.slug}').status_code == 200
