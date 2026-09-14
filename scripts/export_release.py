"""Export the committed project tree with per-file hashes, without Git history.

Usage: python scripts/export_release.py --date 2026-09-07
Requires Git and Python 3.11+. No third-party Python packages required.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', required=True)
    parser.add_argument('--suffix', default='')
    parser.add_argument('--content', type=Path, help='Content-only recovery export under output/releases')
    args = parser.parse_args()
    if len(args.date) != 10 or any(c not in '0123456789-' for c in args.date):
        parser.error('date must use YYYY-MM-DD')
    if args.suffix and not re.fullmatch(r'[a-z0-9-]+', args.suffix):
        parser.error('suffix must contain only lowercase letters, digits and dashes')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    out = ROOT / 'output' / 'releases'
    out.mkdir(parents=True, exist_ok=True)
    name = f'SashaInfinity-SILeos-{args.date}'
    if args.suffix:
        name += '-' + args.suffix
    archive_root = 'SashaLMS'  # Keep Windows extraction paths short.
    archive = out / f'{name}.zip'
    # Git archive reads exactly HEAD, excluding ignored files and runtime uploads.
    payload = subprocess.check_output(['git', 'archive', '--format=zip', 'HEAD'], cwd=ROOT)
    manifest = {'release_date': args.date, 'commit': commit, 'root': archive_root, 'files': []}
    with zipfile.ZipFile(io.BytesIO(payload)) as source, zipfile.ZipFile(
        archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6
    ) as dest:
        for entry in source.infolist():
            if entry.is_dir():
                continue
            data = source.read(entry)
            manifest['files'].append({'path': entry.filename, 'bytes': len(data),
                                      'sha256': hashlib.sha256(data).hexdigest()})
            entry.filename = f'{archive_root}/{entry.filename}'
            dest.writestr(entry, data)
        if args.content:
            content = args.content.resolve()
            if not content.is_relative_to(out.resolve()) or not (content / 'content-manifest.json').is_file():
                raise ValueError('Use a verified content export under output/releases.')
            for file in sorted(content.rglob('*')):
                if not file.is_file():
                    continue
                if file.is_symlink():
                    raise ValueError('Content export cannot contain symlinks.')
                relative = file.relative_to(content).as_posix()
                if not (relative in ('content-manifest.json', 'README.md') or
                        relative.startswith('courses/') and file.suffix == '.zip' or
                        relative.startswith('model-recovery/') and file.suffix == '.glb'):
                    raise ValueError('Unexpected content export file: ' + relative)
                data = file.read_bytes()
                relative = 'recovered-content/' + relative
                manifest['files'].append({'path': relative, 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(), 'origin': 'private-content-handover'})
                dest.writestr(f'{archive_root}/{relative}', data)
        dest.writestr(f'{archive_root}/RELEASE_MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive) as check:
        bad = check.testzip()
        if bad:
            raise RuntimeError(f'Archive verification failed: {bad}')
        for item in manifest['files']:
            actual = hashlib.sha256(check.read(f"{archive_root}/{item['path']}")).hexdigest()
            if actual != item['sha256']:
                raise RuntimeError(f"Hash mismatch: {item['path']}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / f'{name}.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    (out / f'{name}-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'commit': commit,
                      'files': len(manifest['files']), 'bytes': archive.stat().st_size,
                      'sha256': digest, 'verified': True}, indent=2))


if __name__ == '__main__':
    main()
