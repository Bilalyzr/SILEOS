"""Shared tenant, entitlement, domain, audit, and outbox kernel.

Revision ID: 0044
Revises: 0043
"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


VERTICALS = (
    ("meiporul", "immersive_catalog", {"private_assets": 0, "device_rooms": 0}),
    ("seyappaduporul", "campus_operations", {"campuses": 1}),
    ("utporul", "course_authoring", {"published_courses": 20}),
)


def _tables():
    metadata = sa.MetaData()
    tenants = sa.Table(
        "platform_tenants",
        metadata,
        sa.Column("id", sa.Integer),
        sa.Column("slug", sa.String),
        sa.Column("name", sa.String),
        sa.Column("kind", sa.String),
        sa.Column("status", sa.String),
        sa.Column("timezone", sa.String),
        sa.Column("data_region", sa.String),
        sa.Column("created_by", sa.Integer),
    )
    memberships = sa.Table(
        "platform_tenant_memberships",
        metadata,
        sa.Column("tenant_id", sa.Integer),
        sa.Column("user_id", sa.Integer),
        sa.Column("role", sa.String),
        sa.Column("status", sa.String),
        sa.Column("permissions", sa.JSON),
    )
    domains = sa.Table(
        "platform_tenant_domains",
        metadata,
        sa.Column("tenant_id", sa.Integer),
        sa.Column("hostname", sa.String),
        sa.Column("vertical", sa.String),
        sa.Column("status", sa.String),
        sa.Column("is_primary", sa.Boolean),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )
    entitlements = sa.Table(
        "platform_tenant_entitlements",
        metadata,
        sa.Column("tenant_id", sa.Integer),
        sa.Column("vertical", sa.String),
        sa.Column("feature_key", sa.String),
        sa.Column("enabled", sa.Boolean),
        sa.Column("quota", sa.JSON),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("updated_by", sa.Integer),
    )
    return tenants, memberships, domains, entitlements


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("platform_tenants"):
        op.create_table(
            "platform_tenants",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("slug", sa.String(100), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("kind", sa.String(24), nullable=False, server_default="institution"),
            sa.Column("status", sa.String(20), nullable=False, server_default="trial"),
            sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
            sa.Column("data_region", sa.String(32), nullable=False, server_default="in"),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "kind IN ('platform','institution','franchise','company','creator')",
                name="ck_platform_tenant_kind",
            ),
            sa.CheckConstraint(
                "status IN ('trial','active','suspended','archived')",
                name="ck_platform_tenant_status",
            ),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index("ix_platform_tenants_slug", "platform_tenants", ["slug"], unique=True)
        op.create_index("ix_platform_tenants_kind", "platform_tenants", ["kind"])
        op.create_index("ix_platform_tenants_status", "platform_tenants", ["status"])

    inspector = sa.inspect(bind)
    if not inspector.has_table("platform_tenant_memberships"):
        op.create_table(
            "platform_tenant_memberships",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(24), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("permissions", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "role IN ('owner','admin','teacher','instructor','student','learner','finance','operations','support','analyst')",
                name="ck_platform_tenant_member_role",
            ),
            sa.CheckConstraint(
                "status IN ('invited','active','suspended','removed')",
                name="ck_platform_tenant_member_status",
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "user_id", name="uq_platform_tenant_member"),
        )
        op.create_index("ix_platform_tenant_memberships_tenant_id", "platform_tenant_memberships", ["tenant_id"])
        op.create_index("ix_platform_tenant_memberships_user_id", "platform_tenant_memberships", ["user_id"])
        op.create_index("ix_platform_tenant_member_scope", "platform_tenant_memberships", ["tenant_id", "status", "role"])

    if not inspector.has_table("platform_tenant_domains"):
        op.create_table(
            "platform_tenant_domains",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("hostname", sa.String(253), nullable=False),
            sa.Column("vertical", sa.String(30), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "vertical IS NULL OR vertical IN ('meiporul','seyappaduporul','utporul')",
                name="ck_platform_tenant_domain_vertical",
            ),
            sa.CheckConstraint(
                "status IN ('pending','verified','disabled')",
                name="ck_platform_tenant_domain_status",
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("hostname"),
        )
        op.create_index("ix_platform_tenant_domains_tenant_id", "platform_tenant_domains", ["tenant_id"])
        op.create_index("ix_platform_tenant_domain_scope", "platform_tenant_domains", ["tenant_id", "vertical", "status"])

    if not inspector.has_table("platform_tenant_entitlements"):
        op.create_table(
            "platform_tenant_entitlements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("vertical", sa.String(30), nullable=False),
            sa.Column("feature_key", sa.String(80), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("quota", sa.JSON(), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("effective_through", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "vertical IN ('meiporul','seyappaduporul','utporul')",
                name="ck_platform_tenant_entitlement_vertical",
            ),
            sa.CheckConstraint(
                "effective_through IS NULL OR effective_from IS NULL OR effective_through > effective_from",
                name="ck_platform_tenant_entitlement_window",
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tenant_id", "vertical", "feature_key", name="uq_platform_tenant_entitlement"),
        )
        op.create_index("ix_platform_tenant_entitlements_tenant_id", "platform_tenant_entitlements", ["tenant_id"])
        op.create_index("ix_platform_tenant_entitlement_lookup", "platform_tenant_entitlements", ["tenant_id", "vertical", "enabled"])

    if not inspector.has_table("platform_audit_events"):
        op.create_table(
            "platform_audit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("target_type", sa.String(80), nullable=False),
            sa.Column("target_id", sa.String(100), nullable=False, server_default=""),
            sa.Column("reason", sa.String(500), nullable=False, server_default=""),
            sa.Column("before_json", sa.JSON(), nullable=True),
            sa.Column("after_json", sa.JSON(), nullable=True),
            sa.Column("request_id", sa.String(80), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_platform_audit_events_tenant_id", "platform_audit_events", ["tenant_id"])
        op.create_index("ix_platform_audit_events_actor_id", "platform_audit_events", ["actor_id"])
        op.create_index("ix_platform_audit_events_action", "platform_audit_events", ["action"])
        op.create_index("ix_platform_audit_events_request_id", "platform_audit_events", ["request_id"])
        op.create_index("ix_platform_audit_tenant_created", "platform_audit_events", ["tenant_id", "created_at", "id"])

    if not inspector.has_table("platform_outbox_events"):
        op.create_table(
            "platform_outbox_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("topic", sa.String(120), nullable=False),
            sa.Column("aggregate_type", sa.String(80), nullable=False),
            sa.Column("aggregate_id", sa.String(100), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("idempotency_key", sa.String(160), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "status IN ('pending','published','failed')",
                name="ck_platform_outbox_status",
            ),
            sa.CheckConstraint("attempts >= 0", name="ck_platform_outbox_attempts"),
            sa.ForeignKeyConstraint(["tenant_id"], ["platform_tenants.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key"),
        )
        op.create_index("ix_platform_outbox_events_tenant_id", "platform_outbox_events", ["tenant_id"])
        op.create_index("ix_platform_outbox_events_topic", "platform_outbox_events", ["topic"])
        op.create_index("ix_platform_outbox_events_status", "platform_outbox_events", ["status"])
        op.create_index("ix_platform_outbox_delivery", "platform_outbox_events", ["status", "available_at", "id"])

    inspector = sa.inspect(bind)
    if inspector.has_table("institutions"):
        columns = {column["name"] for column in inspector.get_columns("institutions")}
        if "tenant_id" not in columns:
            with op.batch_alter_table("institutions") as batch:
                batch.add_column(sa.Column("tenant_id", sa.Integer(), nullable=True))
                batch.create_foreign_key(
                    "fk_institution_platform_tenant",
                    "platform_tenants",
                    ["tenant_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
                batch.create_index("ix_institutions_tenant_id", ["tenant_id"])

    _seed_and_backfill(bind)


def _seed_and_backfill(bind):
    tenants, memberships, domains, entitlements = _tables()
    now = datetime.now(timezone.utc)

    hq_id = bind.execute(
        sa.select(tenants.c.id).where(tenants.c.slug == "sasha-hq")
    ).scalar_one_or_none()
    if hq_id is None:
        bind.execute(
            tenants.insert().values(
                slug="sasha-hq",
                name="Sasha Infinity",
                kind="platform",
                status="active",
                timezone="Asia/Kolkata",
                data_region="in",
                created_by=None,
            )
        )
        hq_id = bind.execute(
            sa.select(tenants.c.id).where(tenants.c.slug == "sasha-hq")
        ).scalar_one()

    canonical_domains = (
        ("sashainfinity.com", None, True),
        ("admin.sashainfinity.com", None, False),
        ("meiporul.sashainfinity.com", "meiporul", True),
        ("seyappaduporul.sashainfinity.com", "seyappaduporul", True),
        ("utporul.sashainfinity.com", "utporul", True),
    )
    existing_hosts = set(bind.execute(sa.select(domains.c.hostname)).scalars())
    for hostname, vertical, is_primary in canonical_domains:
        if hostname not in existing_hosts:
            bind.execute(
                domains.insert().values(
                    tenant_id=hq_id,
                    hostname=hostname,
                    vertical=vertical,
                    status="verified",
                    is_primary=is_primary,
                    verified_at=now,
                )
            )

    existing_entitlements = set(
        bind.execute(
            sa.select(
                entitlements.c.tenant_id,
                entitlements.c.vertical,
                entitlements.c.feature_key,
            )
        ).all()
    )
    for vertical, feature_key, quota in VERTICALS:
        key = (hq_id, vertical, feature_key)
        if key not in existing_entitlements:
            bind.execute(
                entitlements.insert().values(
                    tenant_id=hq_id,
                    vertical=vertical,
                    feature_key=feature_key,
                    enabled=True,
                    quota=quota,
                    effective_from=now,
                    updated_by=None,
                )
            )

    inspector = sa.inspect(bind)
    if not inspector.has_table("institutions"):
        return
    institution_columns = {column["name"] for column in inspector.get_columns("institutions")}
    if "tenant_id" not in institution_columns:
        return

    institutions = bind.execute(
        sa.text(
            "SELECT id, slug, name, timezone, tenant_id FROM institutions ORDER BY id"
        )
    ).mappings()
    for institution in institutions:
        tenant_id = institution["tenant_id"]
        if tenant_id is None:
            tenant_slug = f"inst-{institution['id']}-{institution['slug']}"[:100]
            tenant_id = bind.execute(
                sa.select(tenants.c.id).where(tenants.c.slug == tenant_slug)
            ).scalar_one_or_none()
            if tenant_id is None:
                bind.execute(
                    tenants.insert().values(
                        slug=tenant_slug,
                        name=institution["name"],
                        kind="institution",
                        status="active",
                        timezone=institution["timezone"] or "Asia/Kolkata",
                        data_region="in",
                        created_by=None,
                    )
                )
                tenant_id = bind.execute(
                    sa.select(tenants.c.id).where(tenants.c.slug == tenant_slug)
                ).scalar_one()
            bind.execute(
                sa.text("UPDATE institutions SET tenant_id = :tenant_id WHERE id = :institution_id"),
                {"tenant_id": tenant_id, "institution_id": institution["id"]},
            )

        existing_entitlements = set(
            bind.execute(
                sa.select(entitlements.c.vertical, entitlements.c.feature_key).where(
                    entitlements.c.tenant_id == tenant_id
                )
            ).all()
        )
        for vertical, feature_key, quota in VERTICALS:
            if (vertical, feature_key) not in existing_entitlements:
                bind.execute(
                    entitlements.insert().values(
                        tenant_id=tenant_id,
                        vertical=vertical,
                        feature_key=feature_key,
                        enabled=True,
                        quota=quota,
                        effective_from=now,
                        updated_by=None,
                    )
                )

        if inspector.has_table("institution_members"):
            campus_members = bind.execute(
                sa.text(
                    "SELECT user_id, role, status FROM institution_members "
                    "WHERE institution_id = :institution_id"
                ),
                {"institution_id": institution["id"]},
            ).mappings()
            existing_users = set(
                bind.execute(
                    sa.select(memberships.c.user_id).where(
                        memberships.c.tenant_id == tenant_id
                    )
                ).scalars()
            )
            for member in campus_members:
                if member["user_id"] not in existing_users:
                    bind.execute(
                        memberships.insert().values(
                            tenant_id=tenant_id,
                            user_id=member["user_id"],
                            role=member["role"],
                            status=(
                                "active"
                                if member["status"] == "active"
                                else "suspended"
                            ),
                            permissions=[],
                        )
                    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("institutions"):
        columns = {column["name"] for column in inspector.get_columns("institutions")}
        # SQLite batch reflection follows every FK target. A bare Alembic
        # database intentionally lacks the legacy users table; institutions
        # will be dropped by 0030 a few steps later, so no rebuild is needed.
        if "tenant_id" in columns and inspector.has_table("users"):
            indexes = {row["name"] for row in inspector.get_indexes("institutions")}
            foreign_keys = {
                row.get("name") for row in inspector.get_foreign_keys("institutions")
            }
            with op.batch_alter_table("institutions") as batch:
                if "ix_institutions_tenant_id" in indexes:
                    batch.drop_index("ix_institutions_tenant_id")
                if "fk_institution_platform_tenant" in foreign_keys:
                    batch.drop_constraint(
                        "fk_institution_platform_tenant", type_="foreignkey"
                    )
                batch.drop_column("tenant_id")
    for table_name in (
        "platform_outbox_events",
        "platform_audit_events",
        "platform_tenant_entitlements",
        "platform_tenant_domains",
        "platform_tenant_memberships",
        "platform_tenants",
    ):
        if sa.inspect(bind).has_table(table_name):
            op.drop_table(table_name)
