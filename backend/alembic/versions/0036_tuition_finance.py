"""Institution tuition plans, installments, ledger and receipts.

Revision ID: 0036
Revises: 0035

Tuition finance is intentionally independent from SashaInfinity orders and
campus SaaS subscriptions.  Financial source rows are retained with RESTRICT
foreign keys; only unpublished plan children cascade with their plan.
"""

from alembic import op
import sqlalchemy as sa


revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


MONEY = sa.Numeric(13, 2)


def upgrade():
    op.create_table(
        "tuition_fee_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("academic_year", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("description", sa.String(1000), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_amount", MONEY, nullable=False, server_default="0"),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "institution_id", "name", "academic_year", name="uq_tuition_plan_name_year"
        ),
        sa.CheckConstraint(
            "status IN ('draft','published','archived')", name="ck_tuition_plan_status"
        ),
        sa.CheckConstraint(
            "total_amount >= 0", name="ck_tuition_plan_total_nonnegative"
        ),
        sa.CheckConstraint("length(currency) = 3", name="ck_tuition_plan_currency"),
    )
    op.create_index(
        "ix_tuition_fee_plans_institution_id", "tuition_fee_plans", ["institution_id"]
    )

    op.create_table(
        "tuition_fee_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("plan_id", "code", name="uq_tuition_component_code"),
        sa.UniqueConstraint(
            "plan_id", "position", name="uq_tuition_component_position"
        ),
        sa.CheckConstraint("amount > 0", name="ck_tuition_component_amount_positive"),
        sa.CheckConstraint(
            "position > 0", name="ck_tuition_component_position_positive"
        ),
    )
    op.create_index(
        "ix_tuition_fee_components_plan_id", "tuition_fee_components", ["plan_id"]
    )

    op.create_table(
        "tuition_installment_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.UniqueConstraint("plan_id", "sequence", name="uq_tuition_template_sequence"),
        sa.CheckConstraint("amount > 0", name="ck_tuition_template_amount_positive"),
        sa.CheckConstraint(
            "sequence > 0", name="ck_tuition_template_sequence_positive"
        ),
    )
    op.create_index(
        "ix_tuition_installment_templates_plan_id",
        "tuition_installment_templates",
        ["plan_id"],
    )
    op.create_index(
        "ix_tuition_template_due",
        "tuition_installment_templates",
        ["plan_id", "due_on", "sequence"],
    )

    op.create_table(
        "tuition_fee_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "student_member_id",
            sa.Integer(),
            sa.ForeignKey("institution_members.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("gross_amount", MONEY, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("assigned_on", sa.Date(), nullable=False),
        sa.Column(
            "assigned_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "student_member_id", "plan_id", name="uq_tuition_student_plan"
        ),
        sa.CheckConstraint(
            "status IN ('active','settled','cancelled')",
            name="ck_tuition_assignment_status",
        ),
        sa.CheckConstraint(
            "gross_amount > 0", name="ck_tuition_assignment_gross_positive"
        ),
    )
    op.create_index(
        "ix_tuition_fee_assignments_institution_id",
        "tuition_fee_assignments",
        ["institution_id"],
    )
    op.create_index(
        "ix_tuition_fee_assignments_student_member_id",
        "tuition_fee_assignments",
        ["student_member_id"],
    )
    op.create_index(
        "ix_tuition_fee_assignments_plan_id", "tuition_fee_assignments", ["plan_id"]
    )
    op.create_index(
        "ix_tuition_assignment_institution_status",
        "tuition_fee_assignments",
        ["institution_id", "status", "id"],
    )

    op.create_table(
        "tuition_installments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("tuition_installment_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("amount_due", MONEY, nullable=False),
        sa.UniqueConstraint(
            "assignment_id", "sequence", name="uq_tuition_installment_sequence"
        ),
        sa.CheckConstraint(
            "amount_due > 0", name="ck_tuition_installment_amount_positive"
        ),
    )
    op.create_index(
        "ix_tuition_installments_assignment_id",
        "tuition_installments",
        ["assignment_id"],
    )
    op.create_index(
        "ix_tuition_installments_due_on", "tuition_installments", ["due_on"]
    )
    op.create_index(
        "ix_tuition_installment_assignment_due",
        "tuition_installments",
        ["assignment_id", "due_on", "sequence"],
    )

    op.create_table(
        "tuition_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(120), nullable=False, server_default=""),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
        sa.Column(
            "recorded_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "institution_id", "idempotency_key", name="uq_tuition_payment_idempotency"
        ),
        sa.CheckConstraint("amount > 0", name="ck_tuition_payment_amount_positive"),
        sa.CheckConstraint(
            "status IN ('posted','reversed')", name="ck_tuition_payment_status"
        ),
    )
    op.create_index(
        "ix_tuition_payments_institution_id", "tuition_payments", ["institution_id"]
    )
    op.create_index(
        "ix_tuition_payments_assignment_id", "tuition_payments", ["assignment_id"]
    )
    op.create_index(
        "ix_tuition_payment_assignment_paid",
        "tuition_payments",
        ["assignment_id", "paid_at", "id"],
    )

    op.create_table(
        "tuition_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "installment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_installments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
        sa.Column(
            "approved_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "institution_id",
            "idempotency_key",
            name="uq_tuition_adjustment_idempotency",
        ),
        sa.CheckConstraint(
            "kind IN ('discount','waiver')", name="ck_tuition_adjustment_kind"
        ),
        sa.CheckConstraint(
            "status IN ('posted','reversed')", name="ck_tuition_adjustment_status"
        ),
        sa.CheckConstraint("amount > 0", name="ck_tuition_adjustment_amount_positive"),
    )
    op.create_index(
        "ix_tuition_adjustments_institution_id",
        "tuition_adjustments",
        ["institution_id"],
    )
    op.create_index(
        "ix_tuition_adjustments_assignment_id", "tuition_adjustments", ["assignment_id"]
    )

    op.create_table(
        "tuition_ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "installment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_installments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_payments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "adjustment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_adjustments.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("memo", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount <> 0", name="ck_tuition_ledger_amount_nonzero"),
        sa.CheckConstraint(
            "entry_type IN ('charge','payment','discount','waiver')",
            name="ck_tuition_ledger_type",
        ),
        sa.CheckConstraint(
            "(entry_type = 'charge' AND amount > 0) OR "
            "(entry_type IN ('payment','discount','waiver') AND amount < 0)",
            name="ck_tuition_ledger_direction",
        ),
        sa.CheckConstraint(
            "(entry_type = 'payment' AND payment_id IS NOT NULL AND adjustment_id IS NULL) OR "
            "(entry_type IN ('discount','waiver') AND adjustment_id IS NOT NULL AND payment_id IS NULL) OR "
            "(entry_type = 'charge' AND payment_id IS NULL AND adjustment_id IS NULL)",
            name="ck_tuition_ledger_source",
        ),
        sa.UniqueConstraint(
            "payment_id", "installment_id", name="uq_tuition_payment_allocation"
        ),
        sa.UniqueConstraint(
            "adjustment_id", "installment_id", name="uq_tuition_adjustment_allocation"
        ),
    )
    op.create_index(
        "ix_tuition_ledger_entries_institution_id",
        "tuition_ledger_entries",
        ["institution_id"],
    )
    op.create_index(
        "ix_tuition_ledger_entries_assignment_id",
        "tuition_ledger_entries",
        ["assignment_id"],
    )
    op.create_index(
        "ix_tuition_ledger_entries_installment_id",
        "tuition_ledger_entries",
        ["installment_id"],
    )
    op.create_index(
        "ix_tuition_ledger_entries_effective_on",
        "tuition_ledger_entries",
        ["effective_on"],
    )
    op.create_index(
        "ix_tuition_ledger_assignment_effective",
        "tuition_ledger_entries",
        ["assignment_id", "effective_on", "id"],
    )

    op.create_table(
        "tuition_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "institution_id",
            sa.Integer(),
            sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "payment_id",
            sa.Integer(),
            sa.ForeignKey("tuition_payments.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("receipt_number", sa.String(50), nullable=False, unique=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("balance_after", MONEY, nullable=False),
        sa.Column(
            "issued_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("amount > 0", name="ck_tuition_receipt_amount_positive"),
        sa.CheckConstraint(
            "balance_after >= 0", name="ck_tuition_receipt_balance_nonnegative"
        ),
    )
    op.create_index(
        "ix_tuition_receipts_institution_id", "tuition_receipts", ["institution_id"]
    )
    op.create_index(
        "ix_tuition_receipts_assignment_id", "tuition_receipts", ["assignment_id"]
    )
    op.create_index(
        "ix_tuition_receipt_institution_issued",
        "tuition_receipts",
        ["institution_id", "issued_at", "id"],
    )


def downgrade():
    for table in (
        "tuition_receipts",
        "tuition_ledger_entries",
        "tuition_adjustments",
        "tuition_payments",
        "tuition_installments",
        "tuition_fee_assignments",
        "tuition_installment_templates",
        "tuition_fee_components",
        "tuition_fee_plans",
    ):
        op.drop_table(table)
