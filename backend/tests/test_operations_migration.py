import importlib.util
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_course_tools_migration_reentrant_on_legacy_sqlite(tmp_path):
    path = Path(__file__).parents[1] / 'alembic/versions/0025_course_tools.py'
    spec = importlib.util.spec_from_file_location('migration0025', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(f'sqlite:///{tmp_path / "migration.db"}')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE courses (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE course_transfers (id VARCHAR(36) PRIMARY KEY)'))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            connection.execute(text("INSERT INTO courses (id, enabled_tools) VALUES (1, '[\"virtual_labs\"]')"))
            migration.upgrade()
        assert 'staging_cleaned_at' in {c['name'] for c in inspect(connection).get_columns('course_transfers')}
        assert connection.execute(text('SELECT enabled_tools FROM courses WHERE id=1')).scalar() == '["virtual_labs"]'
    engine.dispose()


def test_transfer_history_survives_course_deletion_and_cascades_account_deletion(tmp_path):
    path = Path(__file__).parents[1] / 'alembic/versions/0026_transfer_lifecycle.py'
    spec = importlib.util.spec_from_file_location('migration0026', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine(f'sqlite:///{tmp_path / "lifecycle.db"}')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE courses (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE course_transfers (id VARCHAR(36) PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id), course_id INTEGER REFERENCES courses(id))'))
        connection.execute(text('INSERT INTO users VALUES (1)'))
        connection.execute(text('INSERT INTO courses VALUES (1)'))
        connection.execute(text("INSERT INTO course_transfers VALUES ('transfer',1,1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            migration.upgrade()
    with engine.connect() as connection:
        connection.execute(text('PRAGMA foreign_keys=ON'))
        connection.execute(text('DELETE FROM courses WHERE id=1'))
        assert connection.execute(text('SELECT course_id FROM course_transfers')).one()[0] is None
        connection.execute(text('DELETE FROM users WHERE id=1'))
        assert connection.execute(text('SELECT count(*) FROM course_transfers')).scalar() == 0
        connection.commit()
    engine.dispose()
