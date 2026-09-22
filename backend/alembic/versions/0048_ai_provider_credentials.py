"""Encrypted multi-key AI provider vault.

Revision ID: 0048
Revises: 0047
"""
from alembic import op
import sqlalchemy as sa

from app.core.migration_operations import idempotent_create_operations


revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None
op = idempotent_create_operations(op)


def upgrade():
    op.create_table(
        "ai_provider_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("key_ciphertext", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.String(64), nullable=False),
        sa.Column("key_hint", sa.String(16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("health_status", sa.String(20), nullable=False, server_default="untested"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(300), nullable=False, server_default=""),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("provider IN ('glm','gemini')", name="ck_ai_provider_name"),
        sa.CheckConstraint("priority BETWEEN 1 AND 9999", name="ck_ai_provider_priority"),
        sa.CheckConstraint("health_status IN ('untested','healthy','degraded','failing')", name="ck_ai_provider_health"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "key_fingerprint", name="uq_ai_provider_key_fingerprint"),
    )
    for name, columns in (
        ("ix_ai_provider_credentials_provider", ["provider"]),
        ("ix_ai_provider_credentials_priority", ["priority"]),
        ("ix_ai_provider_credentials_is_active", ["is_active"]),
        ("ix_ai_provider_credentials_health_status", ["health_status"]),
        ("ix_ai_provider_credentials_created_by", ["created_by"]),
        ("ix_ai_provider_active_priority", ["is_active", "priority", "id"]),
    ):
        op.create_index(name, "ai_provider_credentials", columns)


def downgrade():
    op.drop_table("ai_provider_credentials")
