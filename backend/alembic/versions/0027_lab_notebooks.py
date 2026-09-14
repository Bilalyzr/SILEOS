"""Private investigation notebooks for imported and authored labs."""
from alembic import op
import sqlalchemy as sa

revision = '0027'
down_revision = '0026'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('lab_notebooks'):
        return
    op.create_table('lab_notebooks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lab_slug', sa.String(50), nullable=False),
        sa.Column('prediction', sa.Text(), nullable=False),
        sa.Column('observation', sa.Text(), nullable=False),
        sa.Column('conclusion', sa.Text(), nullable=False),
        sa.Column('trials', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'lab_slug', name='uq_lab_notebook_user_slug'))
    op.create_index('ix_lab_notebooks_user_id', 'lab_notebooks', ['user_id'])


def downgrade():
    op.drop_table('lab_notebooks')
