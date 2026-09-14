"""Fee collection: cash verification columns, demand invoices, online orders.

Revision ID: 0043
Revises: 0042
"""

from alembic import op
import sqlalchemy as sa


revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    payment_columns = (
        {c["name"] for c in inspector.get_columns("tuition_payments")}
        if inspector.has_table("tuition_payments")
        else set()
    )
    # A bare Alembic test database intentionally has no pre-existing users
    # table. Avoid a SQLite batch reflection through missing FK targets; the
    # normal create_all-first and production schemas both have users.
    if (
        inspector.has_table("tuition_payments")
        and inspector.has_table("users")
        and "verification_status" not in payment_columns
    ):
        with op.batch_alter_table("tuition_payments") as batch:
            batch.add_column(sa.Column("received_by", sa.Integer(), nullable=True))
            batch.add_column(
                sa.Column(
                    "verification_status",
                    sa.String(20),
                    nullable=False,
                    server_default="not_required",
                )
            )
            batch.add_column(sa.Column("verified_by", sa.Integer(), nullable=True))
            batch.add_column(
                sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)
            )
            batch.add_column(
                sa.Column(
                    "verification_note",
                    sa.String(300),
                    nullable=False,
                    server_default="",
                )
            )
            batch.create_foreign_key(
                "fk_tuition_payment_received_by", "users", ["received_by"], ["id"]
            )
            batch.create_foreign_key(
                "fk_tuition_payment_verified_by", "users", ["verified_by"], ["id"]
            )
            batch.create_check_constraint(
                "ck_tuition_payment_verification",
                "verification_status IN ('not_required','pending','verified')",
            )
        # History is treated as already counted: nobody can verify old cash.
        op.execute(
            "UPDATE tuition_payments SET received_by = recorded_by "
            "WHERE received_by IS NULL AND method IN ('cash','cheque')"
        )
        op.execute(
            "UPDATE tuition_payments SET verification_status = 'verified' "
            "WHERE method IN ('cash','cheque')"
        )
        op.create_index(
            "ix_tuition_payment_verification",
            "tuition_payments",
            ["institution_id", "verification_status", "paid_at"],
        )

    if not inspector.has_table("tuition_invoices"):
        op.create_table(
            "tuition_invoices",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("assignment_id", sa.Integer(), nullable=False),
            sa.Column("installment_id", sa.Integer(), nullable=True),
            sa.Column("invoice_number", sa.String(50), nullable=False),
            sa.Column("amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("due_on", sa.Date(), nullable=False),
            sa.Column("lines_json", sa.JSON(), nullable=False),
            sa.Column("issued_by", sa.Integer(), nullable=False),
            sa.Column(
                "issued_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["assignment_id"], ["tuition_fee_assignments.id"]),
            sa.ForeignKeyConstraint(["installment_id"], ["tuition_installments.id"]),
            sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("invoice_number", name="uq_tuition_invoice_number"),
            sa.CheckConstraint("amount > 0", name="ck_tuition_invoice_amount_positive"),
        )
        op.create_index("ix_tuition_invoices_institution_id", "tuition_invoices", ["institution_id"])
        op.create_index("ix_tuition_invoices_assignment_id", "tuition_invoices", ["assignment_id"])
        op.create_index(
            "ix_tuition_invoice_institution_issued",
            "tuition_invoices",
            ["institution_id", "issued_at", "id"],
        )

    if not inspector.has_table("tuition_online_orders"):
        op.create_table(
            "tuition_online_orders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("institution_id", sa.Integer(), nullable=False),
            sa.Column("assignment_id", sa.Integer(), nullable=False),
            sa.Column("installment_id", sa.Integer(), nullable=True),
            sa.Column("payer_user_id", sa.Integer(), nullable=False),
            sa.Column("gateway_order_id", sa.String(64), nullable=False),
            sa.Column("gateway_payment_id", sa.String(64), nullable=True),
            sa.Column("payment_id", sa.Integer(), nullable=True),
            sa.Column("amount", sa.Numeric(13, 2), nullable=False),
            sa.Column("amount_paise", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
            sa.Column("status", sa.String(20), nullable=False, server_default="created"),
            sa.Column("excess_amount", sa.Numeric(13, 2), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
            sa.ForeignKeyConstraint(["assignment_id"], ["tuition_fee_assignments.id"]),
            sa.ForeignKeyConstraint(["installment_id"], ["tuition_installments.id"]),
            sa.ForeignKeyConstraint(["payer_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["payment_id"], ["tuition_payments.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("gateway_order_id", name="uq_tuition_online_order_gateway"),
            sa.UniqueConstraint("gateway_payment_id", name="uq_tuition_online_order_payment"),
            sa.CheckConstraint("amount > 0", name="ck_tuition_online_order_amount_positive"),
            sa.CheckConstraint(
                "status IN ('created','paid','paid_excess','failed')",
                name="ck_tuition_online_order_status",
            ),
        )
        op.create_index("ix_tuition_online_orders_institution_id", "tuition_online_orders", ["institution_id"])
        op.create_index("ix_tuition_online_orders_assignment_id", "tuition_online_orders", ["assignment_id"])
        op.create_index("ix_tuition_online_order_status", "tuition_online_orders", ["institution_id", "status"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("tuition_online_orders"):
        op.drop_table("tuition_online_orders")
    if inspector.has_table("tuition_invoices"):
        op.drop_table("tuition_invoices")
    inspector = sa.inspect(bind)
    if not inspector.has_table("tuition_payments"):
        return
    columns = {c["name"] for c in inspector.get_columns("tuition_payments")}
    if "verification_status" not in columns:
        return
    indexes = {row["name"] for row in inspector.get_indexes("tuition_payments")}
    if "ix_tuition_payment_verification" in indexes:
        op.drop_index("ix_tuition_payment_verification", table_name="tuition_payments")
    checks = {row.get("name") for row in inspector.get_check_constraints("tuition_payments")}
    with op.batch_alter_table("tuition_payments") as batch:
        if "ck_tuition_payment_verification" in checks:
            batch.drop_constraint("ck_tuition_payment_verification", type_="check")
        for column in (
            "verification_note",
            "verified_at",
            "verified_by",
            "verification_status",
            "received_by",
        ):
            if column in columns:
                batch.drop_column(column)
