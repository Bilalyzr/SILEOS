"""Personal learning planner and interventions. Revision 0021, after 0020."""
from alembic import op
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Float, ForeignKey, JSON, UniqueConstraint, MetaData, Table, inspect
from sqlalchemy.sql import func
revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None

def schema():
    metadata = MetaData()
    for name in ('users', 'courses', 'lessons', 'adaptive_sessions'):
        Table(name, metadata, Column('id', Integer, primary_key=True))
    Table(
        'learning_goals', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False, index=True),
        Column('course_id', Integer, ForeignKey('courses.id'), nullable=False, index=True),
        Column('title', String(200), nullable=False),
        Column('target_date', Date, nullable=False),
        Column('daily_minutes', Integer, nullable=False, default=30),
        Column('timezone', String(64), nullable=False, default='Asia/Kolkata'),
        Column('status', String(20), nullable=False, default='active'),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
        UniqueConstraint('user_id', 'course_id', name='uq_learning_goal_user_course'),
    )
    Table(
        'learning_interventions', metadata,
        Column('id', Integer, primary_key=True),
        Column('goal_id', Integer, ForeignKey('learning_goals.id'), nullable=False, index=True),
        Column('concept', String(80), nullable=False),
        Column('status', String(24), nullable=False, default='suggested'),
        Column('reason', Text, nullable=False),
        Column('evidence', JSON, nullable=False, default=dict),
        Column('baseline_score', Float, nullable=True),
        Column('latest_score', Float, nullable=True),
        Column('followup_score', Float, nullable=True),
        Column('instructor_note', Text, nullable=True),
        Column('reviewed_by', Integer, ForeignKey('users.id'), nullable=True),
        Column('reviewed_at', DateTime(timezone=True), nullable=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column('updated_at', DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
        UniqueConstraint('goal_id', 'concept', name='uq_intervention_goal_concept'),
    )
    Table(
        'learning_plan_tasks', metadata,
        Column('id', Integer, primary_key=True),
        Column('goal_id', Integer, ForeignKey('learning_goals.id'), nullable=False, index=True),
        Column('task_key', String(120), nullable=False),
        Column('kind', String(20), nullable=False),
        Column('title', String(255), nullable=False),
        Column('reason', Text, nullable=False),
        Column('concept', String(80), nullable=True),
        Column('lesson_id', Integer, ForeignKey('lessons.id'), nullable=True),
        Column('intervention_id', Integer, ForeignKey('learning_interventions.id'), nullable=True, index=True),
        Column('session_id', Integer, ForeignKey('adaptive_sessions.id'), nullable=True, unique=True),
        Column('minutes', Integer, nullable=False),
        Column('due_date', Date, nullable=False, index=True),
        Column('not_before', Date, nullable=False),
        Column('status', String(20), nullable=False, default='pending'),
        Column('outcome', JSON, nullable=True),
        Column('completed_at', DateTime(timezone=True), nullable=True),
        Column('created_at', DateTime(timezone=True), nullable=False, server_default=func.now()),
        UniqueConstraint('goal_id', 'task_key', name='uq_plan_task_goal_key'),
    )
    return metadata

def upgrade():
    bind = op.get_bind()
    metadata = schema()
    for name in ('learning_goals', 'learning_interventions', 'learning_plan_tasks'):
        metadata.tables[name].create(bind, checkfirst=True)

def downgrade():
    bind = op.get_bind()
    for name in ('learning_plan_tasks', 'learning_interventions', 'learning_goals'):
        if inspect(bind).has_table(name):
            op.drop_table(name)
