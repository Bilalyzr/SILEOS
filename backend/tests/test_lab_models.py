import io
import json
import struct
import zipfile
import pytest
from app.core.security import create_access_token
from app.models.three_d import ThreeDModel
from app.models.content_library import VirtualLabCatalog
from app.services import lab_model_service as svc


def auth(client, user):
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(user.id)})


def glb():
    raw = json.dumps({'asset': {'version':'2.0'}, 'scenes': [], 'nodes': []}).encode()
    raw += b' ' * (-len(raw) % 4)
    return b'glTF' + struct.pack('<IIII', 2, 20+len(raw), len(raw), 0x4e4f534a) + raw


def draft(model_id):
    return {'title':'Model investigation', 'subject':'physics', 'config': {
        'model_id':model_id, 'engine':'linear', 'objective':'Explore a model and compare evidence.',
        'prediction':'What changes when the input doubles?', 'investigation':['Inspect the model.']}}


def test_windows_path_and_missing_optional_tier_remain_portable(client, db, model):
    teacher, model_id = model
    row = db.get(ThreeDModel, model_id)
    assert '\\' not in row.file_path
    row.file_path = row.file_path.replace('/', '\\')
    row.tier_files = {'T2': '1/missing.t2.glb'}
    db.commit()
    response = client.get(f'/api/v1/three-d/models/{model_id}/file?tier=T2')
    assert response.status_code == 200
    assert response.content == glb()
    assert response.headers['x-tier'] == 'T1'


@pytest.mark.parametrize('relative', ['../escape.glb', '..\\escape.glb', 'C:\\escape.glb', '/escape.glb'])
def test_model_paths_cannot_escape_storage(tmp_path, monkeypatch, relative):
    from fastapi import HTTPException
    from app.routers import three_d
    monkeypatch.setattr(three_d, 'BASE_DIR', str(tmp_path))
    with pytest.raises(HTTPException) as exc:
        three_d._resolve(relative)
    assert exc.value.status_code == 404


@pytest.fixture
def model(client, db, make_user, tmp_path, monkeypatch):
    from app.routers import three_d
    monkeypatch.setattr(three_d, 'BASE_DIR', str(tmp_path))
    teacher = make_user(role='instructor')
    auth(client, teacher)
    response = client.post('/api/v1/three-d/models', files={'file':('shape.glb',glb())})
    assert response.status_code == 201, response.text
    return teacher, response.json()['id']


def test_glb_attachment_publication_and_portable_backup(client, db, make_user, model):
    teacher, model_id = model
    created = client.post('/api/v1/lab-studio/drafts', json=draft(model_id))
    assert created.status_code == 201, created.text
    slug = created.json()['slug']
    backup = client.get(f'/api/v1/lab-studio/drafts/{slug}/export')
    assert backup.status_code == 200 and backup.content.startswith(b'PK')
    other = make_user(role='instructor')
    auth(client, other)
    assert client.post('/api/v1/lab-studio/drafts', json=draft(model_id)).status_code == 403
    assert client.get(f'/api/v1/three-d/models/{model_id}/file').status_code == 403
    restored = client.post('/api/v1/lab-studio/import', files={'file':('backup.anything', backup.content)})
    assert restored.status_code == 201, restored.text
    lab = restored.json()['labs'][0]
    assert not lab['is_published'] and lab['slug'] != slug
    assert lab['config']['model_id'] != model_id
    assert client.get(f"/api/v1/three-d/models/{lab['config']['model_id']}/file").content == glb()
    auth(client, teacher)
    assert client.delete(f'/api/v1/three-d/models/{model_id}').status_code == 409
    client.headers.pop('Authorization')
    assert client.get(f'/api/v1/three-d/models/{model_id}/file').status_code == 401
    auth(client, teacher)
    assert client.post(f'/api/v1/lab-studio/drafts/{slug}/publication',json={'published':True}).status_code == 200
    client.headers.pop('Authorization')
    assert client.get(f'/api/v1/three-d/models/{model_id}/file').content == glb()
    assert client.get(f'/api/v1/virtual-labs/{slug}').status_code == 200
    auth(client, teacher)
    client.post(f'/api/v1/lab-studio/drafts/{slug}/publication',json={'published':False})
    client.headers.pop('Authorization')
    assert client.get(f'/api/v1/three-d/models/{model_id}/file').status_code == 401


@pytest.mark.parametrize('mutation', ['checksum','path','duplicate','version'])
def test_invalid_zip_is_atomic(client, db, model, mutation):
    teacher, model_id = model
    row = client.post('/api/v1/lab-studio/drafts',json=draft(model_id)).json()
    original = client.get(f"/api/v1/lab-studio/drafts/{row['slug']}/export").content
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        entries = {name:archive.read(name) for name in archive.namelist()}
    if mutation == 'checksum': entries['model.glb'] += b'bad'
    if mutation == 'path': entries['../model.glb'] = entries.pop('model.glb')
    if mutation == 'version':
        manifest=json.loads(entries['manifest.json']); manifest['version']=9; entries['manifest.json']=json.dumps(manifest).encode()
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        for name, raw in entries.items(): archive.writestr(name,raw)
        if mutation == 'duplicate': archive.writestr('model.glb',glb())
    before=(db.query(ThreeDModel).count(),db.query(VirtualLabCatalog).count())
    response=client.post('/api/v1/lab-studio/import',files={'file':('lab.zip',output.getvalue())})
    assert response.status_code == 422, response.text
    assert before == (db.query(ThreeDModel).count(),db.query(VirtualLabCatalog).count())


def test_upload_rejects_malformed_or_external_glb(client, make_user):
    auth(client,make_user(role='instructor'))
    for raw in (b'glTFbroken', glb()[:-2]):
        assert client.post('/api/v1/three-d/models',files={'file':('shape.glb',raw)}).status_code == 422


def test_json_reference_cannot_steal_private_model(client, db, make_user, model):
    _, model_id=model
    auth(client,make_user(role='instructor'))
    pack=json.dumps({'format':'sasha-concept-labs','version':1,'labs':[draft(None),draft(model_id)]})
    before=db.query(VirtualLabCatalog).count()
    assert client.post('/api/v1/lab-studio/import',files={'file':('lab.json',pack)}).status_code == 403
    assert db.query(VirtualLabCatalog).count() == before
