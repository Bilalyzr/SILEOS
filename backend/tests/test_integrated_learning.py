import json
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from uuid import uuid4
from app.core.security import create_access_token
from app.models.content_library import VirtualLabCatalog
from app.models.learning_release import LabInvestigationAttempt,OfflineSyncReceipt
from app.models.course import Course,Lesson
from app.models.enrollment import Enrollment,LessonProgress
from app.services.supplied_lab_pack import SOURCE,files,MANIFEST


def auth(client,user):client.headers['Authorization']='Bearer '+create_access_token({'sub':str(user.id)})


def test_existing_course_lab_links_resolve_without_reviving_retired_catalog(client, db, make_user):
    from app.services.lab_catalog_service import LEGACY_LAB_REPLACEMENTS
    from app.routers.virtual_labs import get_lab
    for old, new in LEGACY_LAB_REPLACEMENTS.items():
        response = client.get('/api/v1/virtual-labs/' + old)
        assert response.status_code == 200, response.text
        assert response.json()['slug'] == new
        assert response.json()['provider'] == 'embed'
    listed = client.get('/api/v1/virtual-labs').json()['labs']
    assert len(listed) == 59
    assert not set(LEGACY_LAB_REPLACEMENTS).intersection(l['slug'] for l in listed)
    owner = make_user(role='admin')
    db.add(VirtualLabCatalog(slug='cbse-projectile-motion', title='Hidden', subject='physics', provider='embed', is_published=False, created_by=owner.id))
    db.commit()
    assert get_lab(db, 'projectile-motion') is None


def assessment(db,user):
    config={'engine':'supplied','source_slug':'cbse-fractions-explorer','objective':'Explore fractions and justify your reasoning.','prediction':'Which is larger?','investigation':['Compare two fractions.'],'cards':[],'chapter_ids':[], 'assessment_enabled':True,'guided_steps':[{'id':'q','kind':'question','title':'Choose half','instruction':'','options':['1/2','1/3'],'correct_index':0,'points':4},{'id':'note','kind':'observation','title':'Explain','instruction':'','options':[],'points':0}]}
    row=VirtualLabCatalog(slug='own-evidence',title='Fraction evidence',subject='mathematics',provider='native',native_template='concept_lab',config=config,is_published=True,created_by=user.id)
    db.add(row);db.commit();return row


def test_supplied_catalog_excludes_retired_and_respects_admin_visibility(client,db,make_user):
    listed=client.get('/api/v1/virtual-labs').json()['labs']
    assert len(listed)==59
    assert all(l['slug'].startswith('cbse-') and l['provider']=='embed' for l in listed)
    admin=make_user(role='admin');auth(client,admin)
    response=client.post('/api/v1/lab-studio/supplied-pack/inspect',files={'file':('labs.zip',SOURCE.read_bytes())})
    assert response.status_code==200,response.text
    pack=response.json();pack['name']='My Science Lab Collection';pack['labs'][0]['title']='My renamed lab';pack['labs'][0]['published']=False
    response=client.post('/api/v1/lab-studio/supplied-pack/import',files={'file':('labs.zip',SOURCE.read_bytes())},data={'manifest':json.dumps(pack)})
    assert response.status_code==200,response.text
    assert response.json()['imported']==59
    slug=pack['labs'][0]['slug']
    assert slug not in {l['slug'] for l in client.get('/api/v1/lab-studio/curriculum').json()['labs']}
    export=client.get('/api/v1/lab-studio/supplied-pack/export?name=My%20Collection')
    assert export.status_code==200
    manifest=json.loads(files(export.content)[MANIFEST]);entry=next(l for l in manifest['labs'] if l['slug']==slug)
    assert entry['title']=='My renamed lab' and entry['published'] is False


def test_pack_rejects_code_changes_paths_and_non_admin_import(client,db,make_user):
    auth(client,make_user(role='instructor'))
    assert client.post('/api/v1/lab-studio/supplied-pack/import',files={'file':('labs.zip',SOURCE.read_bytes())}).status_code==403
    auth(client,make_user(role='admin'))
    for bad in ('assets/labkit.js','../escape.js'):
        content=files(SOURCE.read_bytes());content[bad]=b'fetch("/api/v1/users")'
        out=BytesIO()
        with ZipFile(out,'w',ZIP_DEFLATED) as z:
            for name,data in content.items():z.writestr(name,data)
        response=client.post('/api/v1/lab-studio/supplied-pack/import',files={'file':('bad.zip',out.getvalue())})
        assert response.status_code==422,response.text
    assert db.query(VirtualLabCatalog).count()==0


def test_answer_keys_private_server_scoring_idempotence_and_version(client,db,make_user):
    teacher=make_user(role='instructor');student=make_user(role='student');row=assessment(db,teacher)
    auth(client,student)
    detail=client.get('/api/v1/virtual-labs/own-evidence').json()
    assert 'correct_index' not in json.dumps(detail)
    payload={'submission_id':str(uuid4()),'revision':detail['revision'],'answers':{'q':0},'observations':{'note':'Two fourths make one half.'}}
    path='/api/v1/lab-studio/labs/own-evidence/attempts'
    result=client.post(path,json=payload);assert result.status_code==200,result.text
    assert result.json()['score']==4
    assert client.get('/api/v1/virtual-labs/own-evidence').json()['best_score']==4
    assert client.post(path,json=payload).json()['id']==result.json()['id']
    assert db.query(LabInvestigationAttempt).count()==1
    assert client.post(path,json={**payload,'answers':{'q':1}}).status_code==409
    assert client.post(path,json={**payload,'score':100}).status_code==422
    row.config={**row.config,'objective':'A revised investigation objective.'};db.commit()
    assert client.post(path,json={**payload,'submission_id':str(uuid4())}).status_code==409
    from app.schemas.scorable import best_item_score
    assert best_item_score(db,{'kind':'lab','id':row.slug},student.id) is None
    auth(client,teacher)
    assert client.get(path).json()['attempts'][0]['evidence']['observations']['note']=='Two fourths make one half.'


def test_ungraded_observations_are_saved_without_marks(client,db,make_user):
    teacher=make_user(role='instructor');student=make_user(role='student');row=assessment(db,teacher)
    row.config={**row.config,'assessment_enabled':False};db.commit()
    auth(client,student)
    detail=client.get('/api/v1/virtual-labs/own-evidence').json()
    response=client.post('/api/v1/lab-studio/labs/own-evidence/attempts',json={'submission_id':str(uuid4()),'revision':detail['revision'],'answers':{'q':0},'observations':{'note':'My ungraded observation'}})
    assert response.status_code==200,response.text
    assert response.json()['score']==response.json()['max_score']==0
    assert db.query(LabInvestigationAttempt).one().evidence['observations']['note']=='My ungraded observation'


def course_fixture(db,teacher,student):
    course=Course(post_author=teacher.id,post_title='Offline science',post_name='offline-science',post_status='published')
    db.add(course);db.flush()
    lesson=Lesson(post_parent=course.id,post_author=teacher.id,post_title='Read this lesson',post_status='publish',post_content='<p>Useful science.</p><script>private()</script>')
    enrollment=Enrollment(user_id=student.id,course_id=course.id,enrollment_status='enrolled')
    db.add_all([lesson,enrollment]);db.commit();return course,lesson,enrollment


def test_offline_access_revision_completion_replay_and_revocation(client,db,make_user):
    teacher=make_user(role='instructor');student=make_user(role='student');course,lesson,enrollment=course_fixture(db,teacher,student)
    auth(client,student)
    path=f'/api/v1/lab-studio/offline/courses/{course.id}'
    response=client.get(path);assert response.status_code==200,response.text
    entry=response.json()['lessons'][0];assert entry['text']=='Useful science.'
    payload={'event_id':str(uuid4()),'revision':entry['revision']}
    complete=path+f'/lessons/{lesson.id}/complete'
    response=client.post(complete,json=payload);assert response.status_code==200,response.text
    assert client.post(complete,json=payload).json()['replayed']
    assert db.query(OfflineSyncReceipt).count()==1
    assert db.query(LessonProgress).filter_by(lesson_id=lesson.id).one().progress_status=='completed'
    lesson.post_content='Changed content';db.commit()
    assert client.post(complete,json={**payload,'event_id':str(uuid4())}).status_code==409
    enrollment.enrollment_status='cancelled';db.commit()
    assert client.get(path).status_code==403


def test_readiness_is_admin_only_and_does_not_expose_secrets(client,make_user,monkeypatch):
    auth(client,make_user(role='student'))
    assert client.get('/api/v1/admin/operations/readiness').status_code==403
    auth(client,make_user(role='admin'))
    monkeypatch.setenv('GLM_API_KEY','private-key-not-for-response')
    result=client.get('/api/v1/admin/operations/readiness');assert result.status_code==200,result.text
    assert 'private-key-not-for-response' not in result.text
    monkeypatch.setattr('app.services.llm_provider.call_glm',lambda *a,**k:'ready')
    assert client.post('/api/v1/admin/operations/readiness/probe/ai').json()['status']=='verified'
