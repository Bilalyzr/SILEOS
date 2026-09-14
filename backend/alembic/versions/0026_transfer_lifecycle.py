"""Course transfer history must not prevent course/user deletion."""
from alembic import op
import sqlalchemy as sa

revision = '0026'
down_revision = '0025'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table('course_transfers'): return
    # SQLite's migration-only harness intentionally has no legacy parent tables.
    # It contains no user/course records; create_all supplies the complete schema.
    if not inspector.has_table('users') or not inspector.has_table('courses'): return
    wanted = {'owner_id': ('users', 'CASCADE'), 'course_id': ('courses', 'SET NULL')}
    changes = []
    for foreign in inspector.get_foreign_keys('course_transfers'):
        columns = foreign['constrained_columns']
        if len(columns) != 1 or columns[0] not in wanted: continue
        column = columns[0]
        table, action = wanted[column]
        if foreign.get('options', {}).get('ondelete', '').upper() != action:
            name = foreign['name'] or f'fk_course_transfers_{column}_{table}'
            changes.append((name, column, table, action))
    if changes:
        convention = {'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s'}
        with op.batch_alter_table('course_transfers', naming_convention=convention) as batch:
            for name, column, table, action in changes:
                batch.drop_constraint(name, type_='foreignkey')
                batch.create_foreign_key(f'fk_course_transfers_{column}_{table}', table, [column], ['id'], ondelete=action)


def downgrade():
    # Retain safe history cleanup semantics; reverting them would block deletion again.
    pass
