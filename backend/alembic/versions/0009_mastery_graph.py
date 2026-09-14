"""learner mastery graph — concept_links, concept_prerequisites, mastery_evidence,
learner_mastery, course_outcomes (v2.0 §9.5/§8.3, WP3)

Guarded like 0007/0008: every operation checks has_table first.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    def has(t):
        return sa.inspect(bind).has_table(t)

    if not has("concept_links"):
        op.create_table(
            "concept_links",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("kind", sa.String(24), nullable=False),
            sa.Column("ref_id", sa.String(64), nullable=False),
            sa.Column("concept", sa.String(80), nullable=False),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("kind", "ref_id", "concept", name="uq_concept_link"),
        )
        op.create_index("ix_concept_links_kind", "concept_links", ["kind"])
        op.create_index("ix_concept_links_ref_id", "concept_links", ["ref_id"])
        op.create_index("ix_concept_links_concept", "concept_links", ["concept"])
        op.create_index("ix_concept_links_course_id", "concept_links", ["course_id"])
    if not has("concept_prerequisites"):
        op.create_table(
            "concept_prerequisites",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("concept", sa.String(80), nullable=False),
            sa.Column("requires", sa.String(80), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("concept", "requires", name="uq_concept_prereq"),
        )
        op.create_index("ix_concept_prerequisites_concept", "concept_prerequisites", ["concept"])
        op.create_index("ix_concept_prerequisites_requires", "concept_prerequisites", ["requires"])
    if not has("mastery_evidence"):
        op.create_table(
            "mastery_evidence",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("concept", sa.String(80), nullable=False),
            sa.Column("source_kind", sa.String(24), nullable=False),
            sa.Column("source_ref", sa.String(64), nullable=False),
            sa.Column("score_pct", sa.Float(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_mastery_evidence_user_id", "mastery_evidence", ["user_id"])
        op.create_index("ix_mastery_evidence_concept", "mastery_evidence", ["concept"])
    if not has("learner_mastery"):
        op.create_table(
            "learner_mastery",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("concept", sa.String(80), nullable=False),
            sa.Column("estimate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "concept", name="uq_learner_concept"),
        )
        op.create_index("ix_learner_mastery_user_id", "learner_mastery", ["user_id"])
        op.create_index("ix_learner_mastery_concept", "learner_mastery", ["concept"])
    if not has("course_outcomes"):
        op.create_table(
            "course_outcomes",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False, unique=True),
            sa.Column("outcome_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("target_concepts", sa.JSON(), nullable=False),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    for t in ("course_outcomes", "learner_mastery", "mastery_evidence", "concept_prerequisites", "concept_links"):
        if sa.inspect(bind).has_table(t):
            op.drop_table(t)
