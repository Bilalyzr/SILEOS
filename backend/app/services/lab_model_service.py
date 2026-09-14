"""GLB attachment authorization and portable, bounded lab archives."""
import hashlib
import io
import json
import os
import struct
import uuid
import zipfile
from fastapi import HTTPException
from app.models.three_d import ThreeDModel
from app.models.content_library import VirtualLabCatalog
from app.schemas.concept_lab import LabPack

MAX_MODEL = 50 * 1024 * 1024
MAX_PACK = 52 * 1024 * 1024


def require_attachable(db, model_id, user):
    if model_id is None:
        return None
    model = db.get(ThreeDModel, model_id)
    if model is None or not (model.owner_id == user.id or model.is_library or user.role in ('admin', 'superadmin')):
        raise HTTPException(403, 'Choose a model from your uploads or the shared library.')
    return model


def referencing_labs(db, model_id):
    # JSON extraction keeps this compatible with SQLite preview and PostgreSQL.
    return db.query(VirtualLabCatalog).filter(
        VirtualLabCatalog.native_template == 'concept_lab',
        VirtualLabCatalog.config['model_id'].as_integer() == model_id)


def validate_glb(raw):
    from app.services.glb_budget import parse_glb_json, check_or_raise
    if len(raw) > MAX_MODEL:
        raise HTTPException(413, 'GLB exceeds the 50 MB limit.')
    if len(raw) < 20 or raw[:4] != b'glTF' or struct.unpack_from('<II', raw, 4) != (2, len(raw)):
        raise HTTPException(422, 'Invalid glTF 2.0 GLB header or length.')
    try:
        offset = 12
        while offset < len(raw):
            if offset + 8 > len(raw):
                raise ValueError()
            length = struct.unpack_from('<I', raw, offset)[0]
            if length % 4 or offset + 8 + length > len(raw):
                raise ValueError()
            offset += 8 + length
        data = parse_glb_json(raw)
        if not isinstance(data, dict) or data.get('asset', {}).get('version') != '2.0':
            raise ValueError()
        for entry in data.get('buffers', []) + data.get('images', []):
            if entry.get('uri') and not str(entry['uri']).startswith('data:'):
                raise ValueError()
        return check_or_raise(raw, 'model.glb')
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, struct.error):
        raise HTTPException(422, 'Use a self-contained GLB with embedded textures and buffers.')


def export_pack(db, row, user):
    from app.routers.three_d import _resolve
    pack = LabPack(format='sasha-concept-labs', version=1, labs=[{k: getattr(row, k) for k in ('title','subject','description','config')}])
    model = require_attachable(db, pack.labs[0].config.model_id, user)
    if model is None:
        return pack.model_dump_json(indent=2), 'application/json', 'json'
    with open(_resolve(model.file_path), 'rb') as handle:
        raw = handle.read(MAX_MODEL + 1)
    validate_glb(raw)
    manifest = {'format':'sasha-lab-model-pack', 'version':1, 'model_id':model.id, 'sha256':hashlib.sha256(raw).hexdigest()}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(manifest))
        archive.writestr('lab.json', pack.model_dump_json())
        archive.writestr('model.glb', raw)
    return output.getvalue(), 'application/zip', 'zip'


def import_pack(db, raw, user):
    from app.routers.three_d import _model_dir
    from app.services.lab_studio_service import write_draft
    created = None
    try:
        if raw.startswith(b'PK'):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                entries = archive.infolist()
                if len(entries) != 3 or {x.filename for x in entries} != {'manifest.json','lab.json','model.glb'}:
                    raise ValueError('Unexpected archive contents.')
                for entry in entries:
                    if entry.file_size > (MAX_MODEL if entry.filename == 'model.glb' else 1024 * 1024):
                        raise ValueError('Archive entry exceeds its limit.')
                manifest = json.loads(archive.read('manifest.json'))
                pack = LabPack.model_validate_json(archive.read('lab.json'))
                model_raw = archive.read('model.glb')
            if (manifest.get('format') != 'sasha-lab-model-pack' or manifest.get('version') != 1
                    or len(pack.labs) != 1 or pack.labs[0].config.model_id != manifest.get('model_id')
                    or hashlib.sha256(model_raw).hexdigest() != manifest.get('sha256')):
                raise ValueError('Invalid manifest or model checksum.')
            validate_glb(model_raw)
            name = uuid.uuid4().hex + '.glb'
            created = os.path.join(_model_dir(user.id), name)
            with open(created, 'xb') as handle:
                handle.write(model_raw)
            model = ThreeDModel(owner_id=user.id, title=pack.labs[0].title, format='glb',
                                file_path=os.path.join(str(user.id), name), file_size_bytes=len(model_raw))
            db.add(model)
            db.flush()
            pack.labs[0].config.model_id = model.id
        else:
            if len(raw) > 1024 * 1024:
                raise HTTPException(413, 'JSON lab packs must be under 1 MB.')
            pack = LabPack.model_validate_json(raw)
        rows = [write_draft(db, entry, user) for entry in pack.labs]
        db.commit()
        return rows
    except Exception as exc:
        db.rollback()
        if created and os.path.isfile(created):
            os.remove(created)
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, (ValueError, TypeError, AttributeError, KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError)):
            raise HTTPException(422, 'Invalid lab backup. Import a JSON or GLB ZIP exported by Lab Studio.') from exc
        raise
