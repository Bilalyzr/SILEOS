"""Campus examinations: exams, papers, marks and hall tickets.

Revision ID: 0038
Revises: 0037
"""

from alembic import op
import sqlalchemy as sa


revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("campus_exams"):
        op.create_table(
            "campus_exams",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("term_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False, server_default="other"),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["term_id"], ["campus_terms.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("institution_id", "term_id", "name", name="uq_campus_exam"),
        )
        op.create_index("ix_campus_exams_institution_id", "campus_exams", ["institution_id"])
        op.create_index("ix_campus_exams_term_id", "campus_exams", ["term_id"])

    if not inspector.has_table("campus_exam_papers"):
        op.create_table(
            "campus_exam_papers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("exam_id", sa.Integer(), nullable=False),
            sa.Column("batch_id", sa.Integer(), nullable=False),
            sa.Column("subject", sa.String(120), nullable=False),
            sa.Column("max_marks", sa.Float(), nullable=False),
            sa.Column("pass_marks", sa.Float(), nullable=False, server_default="0"),
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_minutes", sa.Integer(), nullable=False),
            sa.Column("room", sa.String(80), nullable=False, server_default=""),
            sa.Column("event_id", sa.Integer(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["exam_id"], ["campus_exams.id"]),
            sa.ForeignKeyConstraint(["batch_id"], ["institution_batches.id"]),
            sa.ForeignKeyConstraint(["event_id"], ["campus_events.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("exam_id", "batch_id", "subject", name="uq_campus_exam_paper"),
        )
        op.create_index("ix_campus_exam_papers_exam_id", "campus_exam_papers", ["exam_id"])
        op.create_index("ix_campus_exam_papers_batch_id", "campus_exam_papers", ["batch_id"])

    if not inspector.has_table("campus_exam_marks"):
        op.create_table(
            "campus_exam_marks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("paper_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("marks", sa.Float(), nullable=True),
            sa.Column("absent", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("remarks", sa.String(500), nullable=False, server_default=""),
            sa.Column("graded_by", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["paper_id"], ["campus_exam_papers.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["graded_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("paper_id", "member_id", name="uq_campus_exam_mark"),
        )
        op.create_index("ix_campus_exam_marks_paper_id", "campus_exam_marks", ["paper_id"])
        op.create_index("ix_campus_exam_marks_member_id", "campus_exam_marks", ["member_id"])

    if not inspector.has_table("campus_hall_tickets"):
        op.create_table(
            "campus_hall_tickets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("exam_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("roll_number", sa.String(40), nullable=False),
            sa.Column("token", sa.String(32), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("issued_by", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["exam_id"], ["campus_exams.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["institution_members.id"]),
            sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("exam_id", "member_id", name="uq_campus_hall_ticket"),
            sa.UniqueConstraint("token", name="uq_campus_hall_ticket_token"),
        )
        op.create_index("ix_campus_hall_tickets_exam_id", "campus_hall_tickets", ["exam_id"])
        op.create_index("ix_campus_hall_tickets_member_id", "campus_hall_tickets", ["member_id"])


def downgrade():
    op.drop_table("campus_hall_tickets")
    op.drop_table("campus_exam_marks")
    op.drop_table("campus_exam_papers")
    op.drop_table("campus_exams")
