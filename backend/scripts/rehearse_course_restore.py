"""Run only on an empty, isolated localhost database named *_rehearsal.
Requires the legacy schema or --bootstrap on an empty rehearsal database.
Seeds test content, exercises portable restore, then dumps and restores to a second DB.
"""
import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app.core.database import engine, SessionLocal
from app.core.config import get_settings
from app.models.user import User
from app.models.course import Course, Lesson
from app.models.operations import CourseTransfer
from app.services import course_package_service as packages, operations_service as operations

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pg-bin',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--restore-db', default='lms_restore_rehearsal')
    parser.add_argument('--bootstrap', action='store_true')
    args=parser.parse_args()
    url=make_url(get_settings().DATABASE_URL)
    if url.host not in ('127.0.0.1','localhost') or not url.database.endswith('_rehearsal'):raise RuntimeError('Use an isolated localhost rehearsal database.')
    if not args.restore_db.endswith('_rehearsal') or args.restore_db == url.database: raise RuntimeError('Choose a separate rehearsal restore database.')
    from alembic import command
    from alembic.config import Config
    config = Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    config.set_main_option('script_location', str(Path(__file__).resolve().parents[1]/'alembic'))
    if args.bootstrap:
        if inspect(engine).get_table_names(): raise RuntimeError('Bootstrap requires an empty database.')
        from app.core.database import Base
        # Legacy tables are created by init_db/create_all, not Alembic's no-op 0001.
        added = {'learning_goals','learning_interventions','learning_plan_tasks','studio_questions','recording_lessons','service_heartbeats','course_transfers'}
        Base.metadata.create_all(engine, tables=[t for t in Base.metadata.sorted_tables if t.name not in added])
        command.stamp(config, '0020')
    command.upgrade(config, 'head')
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    get_settings().UPLOAD_DIR=str(output/'content/uploads');Path(get_settings().UPLOAD_DIR).mkdir(parents=True,exist_ok=True)
    with SessionLocal() as db:
        if db.query(User).count():raise RuntimeError('Refusing to seed a nonempty rehearsal database.')
        user=User(user_login='rehearsal',user_email='rehearsal@example.invalid',user_pass='disabled-rehearsal-login',user_nicename='Rehearsal',display_name='Rehearsal',role='instructor')
        db.add(user);db.flush()
        source=Course(post_author=user.id,post_title='தமிழ் course backup',post_status='publish');db.add(source);db.flush()
        lesson=Lesson(post_author=user.id,post_parent=source.id,post_title='Fractions',post_content='<p>பின்னங்கள்: equal parts.</p>');db.add(lesson);db.commit()
        ident=str(uuid.uuid4());folder=packages.root()/ident;folder.mkdir(parents=True)
        archive=folder/'upload.bin';packages.export_course(db,source,archive);data,manifest=packages.inspect_archive(archive)
        transfer=CourseTransfer(id=ident,owner_id=user.id,kind='backup',filename='course.zip',sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),manifest={'data':data,'package':manifest},warnings=[],expires_at=packages.utcnow()+timedelta(hours=24))
        db.add(transfer);db.commit();restored=packages.restore(db,transfer,user,None)
        assert restored.id!=source.id and restored.post_status=='draft' and restored.post_title==source.post_title
        assert db.query(Lesson).filter_by(post_parent=restored.id).one().post_content==lesson.post_content
        operations.pulse(db,'recording_worker','ok')
        assert operations.health(db)['database']=='ok'
    source_counts={}
    with engine.connect() as conn:
        for table in inspect(engine).get_table_names():source_counts[table]=conn.execute(text('SELECT count(*) FROM "'+table+'"')).scalar()
    pg=Path(args.pg_bin);connection=['-h',url.host,'-p',str(url.port or 5432),'-U',url.username]
    backup=output/'database.dump'
    subprocess.run([str(pg/'pg_dump.exe'),*connection,'-Fc','-f',str(backup),url.database],check=True)
    destination=args.restore_db
    subprocess.run([str(pg/'createdb.exe'),*connection,destination],check=True)
    subprocess.run([str(pg/'pg_restore.exe'),*connection,'--exit-on-error','-d',destination,str(backup)],check=True)
    restored_engine=create_engine(url.set(database=destination))
    with restored_engine.connect() as conn:
        for table,count in source_counts.items():assert conn.execute(text('SELECT count(*) FROM "'+table+'"')).scalar()==count,table
        with engine.connect() as original:
            version = original.execute(text('SELECT version_num FROM alembic_version')).scalar()
            postgres_version = original.execute(text('SHOW server_version')).scalar()
        assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar()==version
        assert conn.execute(text("SELECT count(*) FROM courses WHERE post_title = :title"),{'title':'தமிழ் course backup'}).scalar()==2
    restored_engine.dispose()
    result={'postgres_version':postgres_version,'migration':version,'portable_restore':'passed','database_restore':'passed','tables_checked':len(source_counts),'backup_bytes':backup.stat().st_size,'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest()}
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
