"""Move WhatsApp consent to accounts and add platform campaigns.

Revision ID: 0034
Revises: 0033
"""

from alembic import op
import sqlalchemy as sa
from app.core.migration_operations import idempotent_create_operations

op = idempotent_create_operations(op)


revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def _legacy_tables():
    members = sa.table(
        "institution_members",
        sa.column("id", sa.Integer()),
        sa.column("user_id", sa.Integer()),
    )
    legacy = sa.table(
        "campus_whatsapp_contacts",
        sa.column("member_id", sa.Integer()),
        sa.column("phone", sa.String()),
        sa.column("status", sa.String()),
        sa.column("challenge", sa.String()),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("consent_at", sa.DateTime(timezone=True)),
    )
    return members, legacy


def _global_contacts_table():
    return sa.table(
        "whatsapp_contacts",
        sa.column("user_id", sa.Integer()),
        sa.column("phone", sa.String()),
        sa.column("status", sa.String()),
        sa.column("challenge", sa.String()),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("consent_at", sa.DateTime(timezone=True)),
    )


def _stamp(value):
    if value is None:
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _copy_legacy_contacts():
    """Consolidate legacy member rows conservatively into one user row.

    A revocation wins over every other state. This avoids silently restoring
    permission when one account had conflicting campus records. Otherwise the
    most recent confirmed consent or pending expiry wins deterministically.
    The legacy table remains through this revision so rollback never depends
    on reconstructing information that was necessarily collapsed.
    """

    bind = op.get_bind()
    members, legacy = _legacy_tables()
    rows = bind.execute(
        sa.select(
            members.c.user_id,
            legacy.c.member_id,
            legacy.c.phone,
            legacy.c.status,
            legacy.c.challenge,
            legacy.c.expires_at,
            legacy.c.consent_at,
        ).select_from(legacy.join(members, members.c.id == legacy.c.member_id))
    ).mappings()
    priority = {"pending": 1, "confirmed": 2, "revoked": 3}
    winners = {}
    for row in rows:
        rank = (
            priority.get(row["status"], 0),
            _stamp(row["consent_at"]),
            _stamp(row["expires_at"]),
            row["member_id"],
        )
        current = winners.get(row["user_id"])
        if current is None or rank > current[0]:
            winners[row["user_id"]] = (rank, row)
    contacts = _global_contacts_table()
    values = []
    for user_id, (_, row) in winners.items():
        pending = row["status"] == "pending"
        values.append(
            {
                "user_id": user_id,
                "phone": row["phone"],
                "status": row["status"],
                "challenge": row["challenge"] if pending else None,
                "expires_at": row["expires_at"] if pending else None,
                "consent_at": row["consent_at"],
            }
        )
    if values:
        bind.execute(contacts.insert(), values)


def _sync_global_contacts_to_legacy():
    """Preserve post-upgrade changes for accounts representable by a campus."""

    bind = op.get_bind()
    members, legacy = _legacy_tables()
    contacts = _global_contacts_table()
    contacts_by_user = {
        row["user_id"]: row for row in bind.execute(sa.select(contacts)).mappings()
    }
    member_ids_by_user = {}
    for row in bind.execute(
        sa.select(members.c.id, members.c.user_id).order_by(members.c.id)
    ).mappings():
        member_ids_by_user.setdefault(row["user_id"], []).append(row["id"])

    existing_by_user = {}
    for row in bind.execute(
        sa.select(legacy.c.member_id, members.c.user_id).select_from(
            legacy.join(members, members.c.id == legacy.c.member_id)
        )
    ).mappings():
        existing_by_user.setdefault(row["user_id"], []).append(row["member_id"])

    for user_id, contact in contacts_by_user.items():
        target_ids = existing_by_user.get(user_id)
        if not target_ids:
            candidates = member_ids_by_user.get(user_id, [])
            target_ids = candidates[:1]
        for index, member_id in enumerate(target_ids):
            pending = contact["status"] == "pending"
            values = {
                "phone": contact["phone"],
                "status": contact["status"],
                "challenge": contact["challenge"] if pending and index == 0 else None,
                "expires_at": contact["expires_at"] if pending and index == 0 else None,
                "consent_at": contact["consent_at"],
            }
            updated = bind.execute(
                legacy.update().where(legacy.c.member_id == member_id).values(**values)
            )
            if not updated.rowcount:
                bind.execute(legacy.insert().values(member_id=member_id, **values))


def upgrade():
    op.create_table(
        "whatsapp_contacts",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("challenge", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("challenge"),
    )
    op.create_index("ix_whatsapp_contacts_phone", "whatsapp_contacts", ["phone"])
    op.create_table(
        "whatsapp_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("template", sa.String(120), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.Column("header_image_url", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_key"),
    )
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider_id", sa.String(250), nullable=True),
        sa.Column("error", sa.String(200), nullable=False),
        sa.Column("callback_key", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("last_event_at", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["whatsapp_campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id"),
        sa.UniqueConstraint("callback_key"),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_whatsapp_message"),
    )
    op.create_index(
        "ix_whatsapp_messages_campaign_id", "whatsapp_messages", ["campaign_id"]
    )
    op.create_index(
        "ix_whatsapp_messages_delivery_due",
        "whatsapp_messages",
        ["status", "next_attempt_at", "id"],
    )
    op.create_table(
        "whatsapp_status_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(250), nullable=False),
        sa.Column("provider_id", sa.String(250), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("event_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index(
        "ix_whatsapp_status_receipts_provider_id",
        "whatsapp_status_receipts",
        ["provider_id"],
    )
    op.create_index(
        "ix_whatsapp_status_receipts_due",
        "whatsapp_status_receipts",
        ["next_attempt_at", "expires_at", "id"],
    )
    op.create_index(
        "ix_campus_whatsapp_messages_delivery_due",
        "campus_whatsapp_messages",
        ["status", "next_attempt_at", "id"],
    )
    _copy_legacy_contacts()


def downgrade():
    _sync_global_contacts_to_legacy()
    op.drop_index(
        "ix_campus_whatsapp_messages_delivery_due",
        table_name="campus_whatsapp_messages",
    )
    op.drop_index(
        "ix_whatsapp_status_receipts_due",
        table_name="whatsapp_status_receipts",
    )
    op.drop_index(
        "ix_whatsapp_status_receipts_provider_id",
        table_name="whatsapp_status_receipts",
    )
    op.drop_table("whatsapp_status_receipts")
    op.drop_index("ix_whatsapp_messages_delivery_due", table_name="whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_campaign_id", table_name="whatsapp_messages")
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_campaigns")
    op.drop_index("ix_whatsapp_contacts_phone", table_name="whatsapp_contacts")
    op.drop_table("whatsapp_contacts")
