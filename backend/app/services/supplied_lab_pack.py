"""Portable packs for the user's reviewed CBSE simulations.

Executable assets must match the supplied, reviewed archive. Metadata may be
edited freely; this importer never publishes arbitrary uploaded JavaScript on
the authenticated application origin.
"""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile, ZIP_DEFLATED
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from app.models.content_library import VirtualLabCatalog
from app.services.lab_catalog_service import CBSE_LABS

SOURCE = Path(__file__).resolve().parents[2] / 'seed_packs/cbse-supplied.zip'
MAX_BYTES = 8 * 1024 * 1024
MANIFEST = 'sasha-lab-pack.json'
CATALOG = {lab['slug']: lab for lab in CBSE_LABS}


class Entry(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    slug: str
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default='', max_length=2000)
    published: bool = True


class Pack(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    format: str = 'sasha-virtual-lab-pack'
    version: int = 1
    name: str = Field(default='Sasha Virtual Labs', min_length=3, max_length=120)
    labs: list[Entry] = Field(min_length=1, max_length=100)


def files(raw):
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, 'Lab ZIP must be under 8 MB.')
    try:
        with ZipFile(BytesIO(raw)) as archive:
            result = {}
            if len(archive.infolist()) > 200:
                raise ValueError('Too many files.')
            total = 0
            for item in archive.infolist():
                name = item.filename.replace('\\', '/')
                path = PurePosixPath(name)
                if name.startswith('/') or ':' in name or '..' in path.parts or name in result:
                    raise ValueError('Unsafe or duplicate archive path.')
                if item.is_dir():
                    continue
                total += item.file_size
                if total > 12 * 1024 * 1024 or item.file_size > 2 * 1024 * 1024:
                    raise ValueError('Uncompressed pack is too large.')
                result[name] = archive.read(item)
            return result
    except (BadZipFile, ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(422, 'Invalid lab ZIP: ' + str(exc)) from exc


def default_pack():
    return Pack(labs=[Entry(slug=l['slug'], title=l['title'], description=l.get('description') or '') for l in CBSE_LABS])


def inspect(raw):
    incoming = files(raw)
    expected = files(SOURCE.read_bytes())
    for name, data in expected.items():
        if incoming.get(name) != data:
            raise HTTPException(422, f'Unrecognized or missing lab asset: {name}. Use the supplied CBSE ZIP or an exported Sasha pack.')
    if set(incoming) - set(expected) - {MANIFEST}:
        raise HTTPException(422, 'The pack includes unreviewed files.')
    try:
        pack = Pack.model_validate_json(incoming[MANIFEST]) if MANIFEST in incoming else default_pack()
        if pack.format != 'sasha-virtual-lab-pack' or pack.version != 1:
            raise ValueError('Unsupported pack version.')
        if len({e.slug for e in pack.labs}) != len(pack.labs) or any(e.slug not in CATALOG for e in pack.labs):
            raise ValueError('Unknown or duplicate lab identifier.')
    except ValueError as exc:
        raise HTTPException(422, 'Invalid Sasha lab manifest.') from exc
    return pack


def restore(db, raw, user, manifest=None):
    pack = inspect(raw)  # Full validation before any database change.
    if manifest:
        try:
            if len(manifest) > 250000:
                raise ValueError('Manifest too large.')
            edited = Pack.model_validate_json(manifest)
            if edited.format != pack.format or edited.version != 1 or {e.slug for e in edited.labs} != {e.slug for e in pack.labs} or len(edited.labs) != len(pack.labs):
                raise ValueError('Manifest must preserve the inspected lab identifiers.')
            pack = edited
        except ValueError as exc:
            raise HTTPException(422, 'Invalid edited manifest.') from exc
    for entry in pack.labs:
        original = CATALOG[entry.slug]
        row = db.query(VirtualLabCatalog).filter_by(slug=entry.slug).first()
        if row is None:
            row = VirtualLabCatalog(slug=entry.slug, created_by=user.id)
            db.add(row)
        row.title, row.description = entry.title, entry.description
        row.subject, row.provider = original['subject'], 'embed'
        row.embed_url = original['embed_url']
        row.native_template = None
        row.attribution = 'User-authored CBSE Virtual Labs · locally hosted'
        row.config = {'pack_name': pack.name, 'pack_format': pack.format}
        row.is_published = entry.published
    db.commit()
    return {'name': pack.name, 'imported': len(pack.labs), 'source_sha256': sha256(SOURCE.read_bytes()).hexdigest()}


def export(db, name):
    entries = []
    for original in CBSE_LABS:
        row = db.query(VirtualLabCatalog).filter_by(slug=original['slug']).first()
        entries.append(Entry(slug=original['slug'], title=row.title if row else original['title'], description=(row.description if row else original.get('description')) or '', published=row.is_published if row else True))
    pack = Pack(name=name, labs=entries)
    out = BytesIO()
    with ZipFile(out, 'w', ZIP_DEFLATED) as archive:
        for path, data in files(SOURCE.read_bytes()).items():
            archive.writestr(path, data)
        archive.writestr(MANIFEST, json.dumps(pack.model_dump(), ensure_ascii=False, indent=2))
    return out.getvalue()
