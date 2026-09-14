"""Rehearse every content backup in an isolated SQLite database and storage tree."""
import argparse
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'backend'))
    sandbox = ROOT / '.toolchains' / ('restore-' + uuid.uuid4().hex)
    sandbox.mkdir(parents=True)
    os.environ['DATABASE_URL'] = 'sqlite:///' + (sandbox / 'restore.db').as_posix()
    os.environ['SECRET_KEY'] = 'isolated-restore-' + 'x' * 64
    os.environ['JWT_SECRET'] = 'isolated-restore-' + 'y' * 64
    os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
    os.environ['UPLOAD_DIR'] = str(sandbox / 'uploads')
    os.environ['THREE_D_ROOT'] = str(sandbox / 'three_d')
    import app.models
    from app.core.database import Base, engine, SessionLocal
    from app.models.user import User
    from app.models.course import Lesson
    from app.models.operations import CourseTransfer
    from app.services import course_package_service as svc
    from app.services.model_library_service import install_library
    Base.metadata.create_all(engine)
    results = []
    with SessionLocal() as db:
        owner = User(user_login='isolated-restore', user_email='restore@example.invalid',
                     user_pass='not-a-login-credential', user_nicename='restore', display_name='Restore check', role='admin')
        db.add(owner)
        db.commit()
        library = install_library(db, owner)
        assert install_library(db, owner) == library
        for archive in sorted((args.content / 'courses').glob('*.zip')):
            ident = str(uuid.uuid4())
            folder = svc.root() / ident
            folder.mkdir(parents=True)
            raw = archive.read_bytes()
            target = folder / 'upload.bin'
            target.write_bytes(raw)
            data, manifest = svc.inspect_archive(target)
            row = CourseTransfer(id=ident, owner_id=owner.id, kind='backup', filename=archive.name,
                                 sha256=hashlib.sha256(raw).hexdigest(), manifest={'data': data, 'package': manifest},
                                 warnings=manifest.get('warnings', []), expires_at=svc.utcnow() + timedelta(days=1))
            db.add(row)
            db.commit()
            course = svc.restore(db, row, owner, None)
            count = db.query(Lesson).filter_by(post_parent=course.id).count()
            investigations = sum(w.startswith('Quiz lab ') for w in (row.warnings or []))
            assert count == len(data['lessons']) + investigations
            assert course.post_status == 'draft' and course.post_author == owner.id
            results.append({'archive': archive.name, 'restored': True, 'lessons': count, 'draft': True,
                            'investigations_moved_from_quizzes': investigations, 'warnings': row.warnings})
            print('Restored ' + archive.name, flush=True)
    engine.dispose()
    report = {'courses': results, 'library_models': len(library), 'library_idempotent': True,
              'isolated': True, 'note': 'Checks structural restoration. The malformed New Lesson source remains marked for re-export.'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
