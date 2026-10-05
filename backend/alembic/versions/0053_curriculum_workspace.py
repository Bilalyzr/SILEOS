"""Explicit curriculum references and reviewed course mappings."""
from alembic import op
import sqlalchemy as sa
revision = '0053'
down_revision = '0052'
branch_labels = depends_on = None


def upgrade():
    if not sa.inspect(op.get_bind()).has_table('curriculum_workspace_chapters'):
        op.create_table('curriculum_workspace_chapters',
            sa.Column('id', sa.Integer(), primary_key=True), sa.Column('grade', sa.Integer(), nullable=False),
            sa.Column('subject', sa.String(80), nullable=False), sa.Column('title', sa.String(200), nullable=False),
            sa.Column('edition', sa.String(40), nullable=False), sa.Column('source_url', sa.String(500), nullable=False),
            sa.Column('review_note', sa.Text(), nullable=False),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('grade', 'subject', 'title', 'edition', name='uq_curriculum_workspace_chapter'))
    if not sa.inspect(op.get_bind()).has_table('curriculum_workspace_links'):
        op.create_table('curriculum_workspace_links', sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('chapter_key', sa.String(180), nullable=False),
            sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=False),
            sa.Column('reviewed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('review_note', sa.Text(), nullable=False), sa.Column('revision', sa.String(64), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('chapter_key', 'course_id', name='uq_curriculum_workspace_link'))
    names = {i['name'] for i in sa.inspect(op.get_bind()).get_indexes('curriculum_workspace_links')}
    for col in ('chapter_key', 'course_id'):
        name = f'ix_curriculum_workspace_links_{col}'
        if name not in names:
            op.create_index(name, 'curriculum_workspace_links', [col])


def downgrade():
    for table in ('curriculum_workspace_links', 'curriculum_workspace_chapters'):
        if sa.inspect(op.get_bind()).has_table(table):
            op.drop_table(table)
