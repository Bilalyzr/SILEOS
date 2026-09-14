"""Export content-only course backups and every local GLB for a private handover.

Run with the backend Python environment. Reads a named SQLite database in read-only
mode; does not export accounts, passwords, enrollments, grades or payments.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        parser.error('Database does not exist.')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / 'backend'))
    # These only satisfy configuration for a read-only local content export.
    os.environ['DATABASE_URL'] = 'sqlite://'
    os.environ.setdefault('SECRET_KEY', 'offline-export-only-' + 'x' * 64)
    os.environ.setdefault('JWT_SECRET', 'offline-export-only-' + 'y' * 64)
    os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    import app.models
    from app.models.course import Course
    from app.core.config import get_settings
    from app.services.course_package_service import export_course, inspect_archive
    get_settings().UPLOAD_DIR = str(ROOT / 'backend/uploads')
    engine = create_engine(f'sqlite:///file:{database.as_posix()}?mode=ro&uri=true')
    report = {'format': 'sasha-content-handover', 'version': 1, 'courses': [], 'models': []}
    with Session(engine) as db:
        for course in db.query(Course).order_by(Course.id):
            target = output / 'courses' / f'course-{course.id}.zip'
            target.parent.mkdir(exist_ok=True)
            record = {'source_id': course.id, 'title': course.post_title, 'file': target.relative_to(output).as_posix()}
            try:
                manifest = export_course(db, course, target)
                data, _ = inspect_archive(target)
                record.update(verified=True, lessons=len(data['lessons']), warnings=manifest['warnings'],
                              sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            except Exception as exc:
                # Keep any incomplete backup only in recovery, explicitly labelled.
                record.update(verified=False, error=str(exc))
            report['courses'].append(record)
    engine.dispose()
    model_root = ROOT / 'backend/three_d'
    for source in sorted(model_root.rglob('*.glb')):
        if source.is_symlink():
            raise ValueError('Refusing a symlink in the model recovery tree.')
        relative = source.relative_to(model_root)
        target = output / 'model-recovery' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        target.write_bytes(raw)
        report['models'].append({'file': target.relative_to(output).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    (output / 'content-manifest.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'courses': len(report['courses']), 'verified_courses': sum(c['verified'] for c in report['courses']),
                      'model_files': len(report['models']), 'course_issues': [c for c in report['courses'] if not c['verified']]}, indent=2))


if __name__ == '__main__':
    main()
