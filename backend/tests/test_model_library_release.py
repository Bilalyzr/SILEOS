import hashlib
import json
import struct

import pytest
from app.models.three_d import ThreeDModel
from app.services.model_library_service import install_library


def make_source(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    raw = json.dumps({'asset': {'version': '2.0'}, 'scenes': [], 'nodes': []}).encode()
    raw += b' ' * (-len(raw) % 4)
    raw = b'glTF' + struct.pack('<IIII', 2, len(raw) + 20, len(raw), 0x4e4f534a) + raw
    sha = hashlib.sha256(raw).hexdigest()
    (source / (sha + '.glb')).write_bytes(raw)
    item = {'original_model_id': 1234, 'title': 'Portable test model', 'file': sha + '.glb', 'sha256': sha, 'bytes': len(raw)}
    (source / 'catalog.json').write_text(json.dumps({'format': 'sasha-model-library', 'version': 1, 'models': [item]}))
    return source, item


def test_clean_install_remaps_ids_and_is_idempotent(db, make_user, tmp_path, monkeypatch):
    from app.routers import three_d
    monkeypatch.setattr(three_d, 'BASE_DIR', str(tmp_path / 'storage'))
    source, _ = make_source(tmp_path)
    owner = make_user(role='admin')
    result = install_library(db, owner, source)
    assert result[0]['model_id'] != 1234
    assert install_library(db, owner, source) == result
    row = db.get(ThreeDModel, result[0]['model_id'])
    assert row.is_library and row.owner_id == owner.id
    assert len(list((tmp_path / 'storage').rglob('*.glb'))) == 1


def test_invalid_model_never_creates_rows_or_files(db, make_user, tmp_path, monkeypatch):
    from app.routers import three_d
    monkeypatch.setattr(three_d, 'BASE_DIR', str(tmp_path / 'storage'))
    source, item = make_source(tmp_path)
    (source / item['file']).write_bytes(b'corrupt')
    count = db.query(ThreeDModel).count()
    with pytest.raises(ValueError, match='checksum'):
        install_library(db, make_user(role='admin'), source)
    assert db.query(ThreeDModel).count() == count
    assert not (tmp_path / 'storage').exists()


def test_only_admin_can_restore_the_real_bundled_library(client, db, make_user, tmp_path, monkeypatch):
    from app.routers import three_d
    from app.core.security import create_access_token
    monkeypatch.setattr(three_d, 'BASE_DIR', str(tmp_path / 'storage'))
    teacher = make_user(role='instructor')
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(teacher.id)})
    assert client.post('/api/v1/three-d/models/restore-library').status_code == 403
    admin = make_user(role='admin')
    client.headers['Authorization'] = 'Bearer ' + create_access_token({'sub': str(admin.id)})
    first = client.post('/api/v1/three-d/models/restore-library')
    assert first.status_code == 200, first.text
    assert len(first.json()['models']) == 4
    assert client.post('/api/v1/three-d/models/restore-library').json() == first.json()
    assert db.query(ThreeDModel).count() == 4
