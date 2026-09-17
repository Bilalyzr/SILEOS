"""School and college workspaces, scoped membership and academic administration."""
from alembic import op
import sqlalchemy as sa

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade():
    # Explicit migration schema; intentionally independent of evolving ORM models.
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    definitions = {
        "institution_members": [
            sa.Column(
                "institution_id",
                sa.Integer,
                sa.ForeignKey("institutions.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("department", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.UniqueConstraint(
                "institution_id", "user_id", name="uq_institution_member"
            ),
        ],
        "institution_invites": [
            sa.Column(
                "institution_id",
                sa.Integer,
                sa.ForeignKey("institutions.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("email", sa.String(254), nullable=False, index=True),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("department", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "institution_id", "email", name="uq_institution_invite"
            ),
        ],
        "institution_batches": [
            sa.Column(
                "institution_id",
                sa.Integer,
                sa.ForeignKey("institutions.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("department", sa.String(100), nullable=False),
            sa.Column("academic_year", sa.String(32), nullable=False),
            sa.UniqueConstraint(
                "institution_id", "name", "academic_year", name="uq_institution_batch"
            ),
        ],
        "institution_batch_members": [
            sa.Column(
                "batch_id",
                sa.Integer,
                sa.ForeignKey("institution_batches.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "member_id",
                sa.Integer,
                sa.ForeignKey("institution_members.id"),
                nullable=False,
                index=True,
            ),
            sa.UniqueConstraint(
                "batch_id", "member_id", name="uq_institution_batch_member"
            ),
        ],
        "institution_courses": [
            sa.Column(
                "institution_id",
                sa.Integer,
                sa.ForeignKey("institutions.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "course_id", sa.Integer, sa.ForeignKey("courses.id"), nullable=False
            ),
            sa.Column(
                "connected_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False
            ),
            sa.UniqueConstraint(
                "institution_id", "course_id", name="uq_institution_course"
            ),
        ],
        "institution_assignments": [
            sa.Column(
                "batch_id",
                sa.Integer,
                sa.ForeignKey("institution_batches.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "institution_course_id",
                sa.Integer,
                sa.ForeignKey("institution_courses.id"),
                nullable=False,
            ),
            sa.Column("due_date", sa.String(10)),
            sa.UniqueConstraint(
                "batch_id", "institution_course_id", name="uq_institution_assignment"
            ),
        ],
        "institution_audit": [
            sa.Column(
                "institution_id",
                sa.Integer,
                sa.ForeignKey("institutions.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "actor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("action", sa.String(60), nullable=False),
            sa.Column("detail", sa.String(250), nullable=False),
        ],
        "institution_plan_requests": [
            sa.Column(
                "institution_id",
                sa.Integer,
                sa.ForeignKey("institutions.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "requested_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("plan", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("note", sa.Text, nullable=False),
        ],
    }
    timed = {
        "institution_members",
        "institution_invites",
        "institution_batches",
        "institution_audit",
        "institution_plan_requests",
    }
    for name, columns in definitions.items():
        if name in timed:
            columns.append(
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.func.now(),
                )
            )
        op.create_table(name, sa.Column("id", sa.Integer, primary_key=True), *columns)


def downgrade():
    for name in (
        "institution_plan_requests",
        "institution_audit",
        "institution_assignments",
        "institution_courses",
        "institution_batch_members",
        "institution_batches",
        "institution_invites",
        "institution_members",
        "institutions",
    ):
        op.drop_table(name)
