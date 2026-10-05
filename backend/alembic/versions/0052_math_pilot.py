"""Versioned, course-scoped mathematics pilot (frozen schema)."""
from alembic import op
import sqlalchemy as sa

revision = '0052'
down_revision = '0051'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table('math_pilot_policies'):
        op.create_table('math_pilot_policies',
            sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), primary_key=True),
            sa.Column('version', sa.String(64), nullable=False),
            sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('review_note', sa.String(2000), nullable=False),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False))
    if not sa.inspect(bind).has_table('math_pilot_sessions'):
        op.create_table('math_pilot_sessions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=False),
            sa.Column('version', sa.String(64), nullable=False),
            sa.Column('stage', sa.String(24), nullable=False),
            sa.Column('sequence', sa.Integer(), nullable=False),
            sa.Column('hypothesis', sa.String(40)), sa.Column('intervention', sa.String(40)),
            sa.Column('transfer_score', sa.Integer()), sa.Column('retention_score', sa.Integer()),
            sa.Column('due_at', sa.DateTime(timezone=True)),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint('user_id', 'course_id', 'version', name='uq_math_pilot_learner'))
    if not sa.inspect(bind).has_table('math_pilot_events'):
        op.create_table('math_pilot_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('math_pilot_sessions.id'), nullable=False),
            sa.Column('sequence', sa.Integer(), nullable=False), sa.Column('key', sa.String(36), nullable=False),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('action', sa.String(24), nullable=False), sa.Column('payload', sa.JSON(), nullable=False),
            sa.Column('result', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint('session_id', 'sequence', name='uq_math_pilot_sequence'),
            sa.UniqueConstraint('session_id', 'key', name='uq_math_pilot_request'))
    for table, cols in [('math_pilot_sessions', ['user_id', 'course_id', 'expires_at']), ('math_pilot_events', ['session_id'])]:
        names = {i['name'] for i in sa.inspect(bind).get_indexes(table)}
        for col in cols:
            name = f'ix_{table}_{col}'
            if name not in names:
                op.create_index(name, table, [col])


def downgrade():
    for table in ('math_pilot_events', 'math_pilot_sessions', 'math_pilot_policies'):
        if sa.inspect(op.get_bind()).has_table(table):
            op.drop_table(table)
