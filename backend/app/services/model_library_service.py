"""Install the bundled, checksummed project models into an existing account.

No user accounts, passwords or original owner IDs are transferred.
"""
import hashlib
import json
from pathlib import Path

from app.models.three_d import ThreeDModel
from app.services.lab_model_service import validate_glb

SOURCE = Path(__file__).resolve().parents[2] / 'seed_packs/models'


def install_library(db, owner, source=None):
    from app.routers.three_d import BASE_DIR
    if owner.role not in ('admin', 'superadmin', 'instructor'):
        raise ValueError('Choose an existing instructor or administrator as owner.')
    source = Path(source or SOURCE).resolve()
    catalog = json.loads((source / 'catalog.json').read_text(encoding='utf-8'))
    if catalog.get('format') != 'sasha-model-library' or catalog.get('version') != 1:
        raise ValueError('Unsupported model library.')
    prepared = []
    for item in catalog['models']:
        sha = item['sha256']
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha) or item['file'] != sha + '.glb':
            raise ValueError('Invalid model path or digest.')
        file = (source / item['file']).resolve()
        if source not in file.parents:
            raise ValueError('Model escaped library directory.')
        raw = file.read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError('Model checksum mismatch: ' + item['title'])
        validate_glb(raw)
        prepared.append((item, raw))
    created = []
    result = []
    try:
        for item, raw in prepared:
            relative = f"{owner.id}/library-{item['sha256']}.glb"
            destination = Path(BASE_DIR).resolve() / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.resolve().parent != Path(BASE_DIR).resolve() / str(owner.id):
                raise ValueError('Model destination escaped storage.')
            if not destination.exists():
                destination.write_bytes(raw)
                created.append(destination)
            elif hashlib.sha256(destination.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Existing library file has changed; repair it before importing.')
            row = db.query(ThreeDModel).filter_by(owner_id=owner.id, file_path=relative).first()
            if row is None:
                row = ThreeDModel(owner_id=owner.id, file_path=relative, title=item['title'],
                                  format='glb', file_size_bytes=len(raw), is_library=True)
                db.add(row)
                db.flush()
            result.append({'source_id': item['original_model_id'], 'model_id': row.id,
                           'title': row.title, 'sha256': item['sha256']})
        db.commit()
    except Exception:
        db.rollback()
        for file in created:
            file.unlink(missing_ok=True)
        raise
    return result
