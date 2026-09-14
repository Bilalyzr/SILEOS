import json
from pathlib import Path
import pytest
from app.core.security import create_access_token
from app.models.content_library import VirtualLabCatalog
from app.services.lab_studio_service import CBSE_LABS, CHAPTERS


def test_every_legacy_chapter_has_a_valid_focused_activity():
    from app.services.lab_catalog_service import LEGACY_CHAPTERS
    from app.services.lab_studio_service import CONCEPT_EXTENSIONS, CONCEPT_LABS
    from app.schemas.concept_lab import LabDraftIn
    assert len(CONCEPT_EXTENSIONS) == 119
    for entry in CONCEPT_EXTENSIONS:
        LabDraftIn(**entry)
    slugs = {l['slug'] for l in CBSE_LABS + CONCEPT_LABS}
    assert all(c['lab_slug'] in slugs for c in LEGACY_CHAPTERS if c['lab_slug'])
    assert not any((c['lab_slug'] or '').startswith('concept-') for c in LEGACY_CHAPTERS)
    assert all(c['lab_slug'] in slugs for c in CHAPTERS if c['lab_slug'])


def auth(client, user):
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(user.id)})


def draft(engine='linear'):
    return {'title': 'Tamil and English concept lab', 'subject': 'mathematics', 'description': '', 'config': {
        'engine': engine, 'objective': 'Explain slope and intercept using evidence.',
        'prediction': 'What changes when the slope doubles?', 'investigation': ['Capture the first result.', 'Double the slope.'],
        'explanation': 'தமிழ் · y = mx + b', 'chapter_ids': [CHAPTERS[0]['id']], 'cards': []}}


def test_imported_catalog_has_all_files_and_chapters(client):
    response = client.get('/api/v1/lab-studio/curriculum')
    assert response.status_code == 200
    assert len(response.json()['labs']) == 59 and len(response.json()['chapters']) == 463
    assert len({l['slug'] for l in CBSE_LABS}) == 59
    base = Path(__file__).resolve().parents[2] / 'frontend/public/labs/cbse'
    for lab in CBSE_LABS:
        assert len(lab['slug']) <= 50
        assert 'spatial-bridge.js' in (base / lab['file']).read_text(encoding='utf-8')
    listed = client.get('/api/v1/virtual-labs').json()['labs']
    assert all(l['slug'] in {x['slug'] for x in listed} for l in CBSE_LABS)


def test_curriculum_editions_preserve_chapter_identity():
    from app.services.lab_catalog_service import CURRENT_CHAPTERS, LEGACY_CHAPTERS, CHAPTER_IDS
    assert len(CURRENT_CHAPTERS) == 230
    assert len(LEGACY_CHAPTERS) == 233
    assert len(CHAPTER_IDS) == 463
    assert {c['id'] for c in CURRENT_CHAPTERS}.isdisjoint(c['id'] for c in LEGACY_CHAPTERS)
    old = next(c for c in LEGACY_CHAPTERS if c['id'] == '6-mathematics-1')
    new = next(c for c in CURRENT_CHAPTERS if c['id'] == 'ncert-2024-6-mathematics-1')
    assert old['title'] != new['title']
    for chapter in CURRENT_CHAPTERS:
        if chapter.get('alignment_source') == 'matching-legacy-title':
            match = next(c for c in LEGACY_CHAPTERS if (c['grade'], c['subject'], c['title'].casefold().strip()) ==
                         (chapter['grade'], chapter['subject'], chapter['title'].casefold().strip()))
            assert chapter['lab_slug'] == match['lab_slug']


def test_student_cannot_author(client, make_user):
    auth(client, make_user(role='student'))
    assert client.post('/api/v1/lab-studio/drafts', json=draft()).status_code == 403
    assert client.get('/api/v1/lab-studio/drafts').status_code == 403


def test_draft_ownership_publication_and_roundtrip(client, make_user):
    teacher = make_user(role='instructor'); other = make_user(role='instructor'); student = make_user(role='student')
    auth(client, teacher)
    created = client.post('/api/v1/lab-studio/drafts', json=draft()); assert created.status_code == 201, created.text
    row = created.json(); slug = row['slug']; assert not row['is_published']
    assert client.get(f'/api/v1/virtual-labs/{slug}').status_code == 200
    exported = client.get(f'/api/v1/lab-studio/drafts/{slug}/export'); assert exported.status_code == 200
    auth(client, other)
    assert client.put(f'/api/v1/lab-studio/drafts/{slug}', json=draft()).status_code == 404
    assert client.get(f'/api/v1/virtual-labs/{slug}').status_code == 404
    auth(client, teacher)
    assert client.post(f'/api/v1/lab-studio/drafts/{slug}/publication', json={'published': True}).status_code == 200
    restored = client.post('/api/v1/lab-studio/import', files={'file': ('backup.unknown', exported.content)})
    assert restored.status_code == 201, restored.text
    assert restored.json()['labs'][0]['slug'] != slug
    assert not restored.json()['labs'][0]['is_published']
    assert 'தமிழ்' in restored.json()['labs'][0]['config']['explanation']
    auth(client, student)
    assert client.get(f'/api/v1/virtual-labs/{slug}').status_code == 200
    assert client.post(f'/api/v1/virtual-labs/{slug}/results', json={'score': 0}).status_code == 400


@pytest.mark.parametrize('bad', [ {'engine':'eval'}, {'expression':'window.alert(1)'}, {'chapter_ids':['unknown']}, {'investigation':['']}, {'engine':'classification','cards':[]} ])
def test_invalid_config_is_rejected(client, make_user, bad):
    auth(client, make_user(role='instructor')); payload=draft(); payload['config'].update(bad)
    assert client.post('/api/v1/lab-studio/drafts',json=payload).status_code == 422


def test_pack_validation_is_atomic(client, db, make_user):
    auth(client, make_user(role='instructor'))
    invalid = draft(); invalid['config']['engine'] = 'javascript'
    before = db.query(VirtualLabCatalog).count()
    response = client.post('/api/v1/lab-studio/import', files={'file': ('pack.json',json.dumps({'format':'sasha-concept-labs','version':1,'labs':[draft(),invalid]}))})
    assert response.status_code == 422
    assert db.query(VirtualLabCatalog).count() == before


def test_notebooks_are_private_and_do_not_award_scores(client, make_user):
    a = make_user(role='student'); b = make_user(role='student'); slug=CBSE_LABS[0]['slug']
    auth(client,a)
    saved = client.put(f'/api/v1/lab-studio/notebooks/{slug}', json={'prediction':'தமிழ் prediction','observation':'Measured two trials','conclusion':'Compare','trials':[{'voltage':12,'current':1.2}]})
    assert saved.status_code == 200, saved.text
    auth(client,b)
    assert client.get(f'/api/v1/lab-studio/notebooks/{slug}').json()['prediction'] == ''
    auth(client,a)
    assert client.get(f'/api/v1/lab-studio/notebooks/{slug}').json()['trials'][0]['current'] == 1.2


def test_classification_requires_unique_labels_and_two_groups(client, make_user):
    auth(client, make_user(role='instructor')); data=draft('classification')
    data['config']['cards']=[{'label':'Copper','group':'Conductor'},{'label':'Iron','group':'Conductor'},{'label':'Rubber','group':'Insulator'}]
    assert client.post('/api/v1/lab-studio/drafts',json=data).status_code == 201
    data['config']['cards'][2]['label']='Copper'
    assert client.post('/api/v1/lab-studio/drafts',json=data).status_code == 422


def test_investigations_cannot_be_mistaken_for_gradeable_items(db, make_user):
    from fastapi import HTTPException
    from app.schemas.scorable import _resolve_reference
    from app.services.lab_studio_service import CONCEPT_LABS
    with pytest.raises(HTTPException) as error:
        _resolve_reference(db, 'lab', CONCEPT_LABS[0]['slug'], make_user(role='instructor'))
    assert error.value.status_code == 422
