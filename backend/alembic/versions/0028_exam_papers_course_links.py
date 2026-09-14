"""Admin-priced exam papers and race-safe public course links."""
from alembic import op
import sqlalchemy as sa

revision = '0028'
down_revision = '0027'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if sa.inspect(bind).has_table('courses'):
        # Preserve all existing links. Resolve duplicates explicitly before migration.
        duplicates = bind.execute(sa.text("SELECT lower(post_name) FROM courses WHERE post_name <> '' GROUP BY lower(post_name) HAVING count(*) > 1")).first()
        if duplicates:
            raise RuntimeError('Duplicate course links exist. Resolve them before applying migration 0028.')
        bind.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_courses_public_slug ON courses (lower(post_name)) WHERE post_name <> ''"))
    if not sa.inspect(bind).has_table('exam_price_slabs'):
        op.create_table('exam_price_slabs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('exam', sa.String(10), nullable=False, index=True),
            sa.Column('title', sa.String(100), nullable=False),
            sa.Column('min_questions', sa.Integer(), nullable=False),
            sa.Column('max_questions', sa.Integer(), nullable=False),
            sa.Column('price_paise', sa.Integer(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False),
            sa.Column('deleted', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    if not sa.inspect(bind).has_table('exam_papers'):
        op.create_table('exam_papers',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
            sa.Column('slab_id', sa.Integer(), sa.ForeignKey('exam_price_slabs.id')),
            sa.Column('exam', sa.String(10), nullable=False),
            sa.Column('title', sa.String(200), nullable=False),
            sa.Column('question_count', sa.Integer(), nullable=False),
            sa.Column('input_json', sa.JSON(), nullable=False),
            sa.Column('amount_paise', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(24), nullable=False, index=True),
            sa.Column('gateway_order_id', sa.String(100), unique=True),
            sa.Column('gateway_payment_id', sa.String(100), unique=True),
            sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id')),
            sa.Column('bank_id', sa.Integer(), sa.ForeignKey('question_banks.id')),
            sa.Column('questions', sa.JSON()), sa.Column('error', sa.Text()),
            sa.Column('generation_id', sa.String(36)),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('started_at', sa.DateTime(timezone=True)),
            sa.Column('finished_at', sa.DateTime(timezone=True)))



def downgrade():
    bind = op.get_bind()
    for table in ('exam_papers', 'exam_price_slabs'):
        if sa.inspect(bind).has_table(table):
            op.drop_table(table)
    # SQLAlchemy does not reflect SQLite expression indexes; use portable SQL.
    bind.execute(sa.text('DROP INDEX IF EXISTS uq_courses_public_slug'))
