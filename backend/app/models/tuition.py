"""Institution tuition finance records.

Tuition is money owed by a student to a school or college.  It deliberately
does not reuse ``orders``, ``payments`` or ``campus_subscriptions``: those
tables describe SashaInfinity commerce and SaaS billing respectively.

Balances are derived from the append-only ledger.  Positive entries increase
the student's liability and negative entries reduce it.  Source records keep
the user-facing payment/adjustment metadata while ledger entries preserve the
accounting trail and installment allocations.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


MONEY = Numeric(13, 2)


class TuitionFeePlan(Base):
    __tablename__ = "tuition_fee_plans"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(160), nullable=False)
    academic_year = Column(String(32), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    description = Column(String(1000), nullable=False, default="")
    status = Column(String(20), nullable=False, default="draft")
    total_amount = Column(MONEY, nullable=False, default=0)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "name", "academic_year", name="uq_tuition_plan_name_year"
        ),
        CheckConstraint(
            "status IN ('draft','published','archived')", name="ck_tuition_plan_status"
        ),
        CheckConstraint("total_amount >= 0", name="ck_tuition_plan_total_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_tuition_plan_currency"),
    )


class TuitionFeeComponent(Base):
    __tablename__ = "tuition_fee_components"

    id = Column(Integer, primary_key=True)
    plan_id = Column(
        Integer,
        ForeignKey("tuition_fee_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    amount = Column(MONEY, nullable=False)
    position = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("plan_id", "code", name="uq_tuition_component_code"),
        UniqueConstraint("plan_id", "position", name="uq_tuition_component_position"),
        CheckConstraint("amount > 0", name="ck_tuition_component_amount_positive"),
        CheckConstraint("position > 0", name="ck_tuition_component_position_positive"),
    )


class TuitionInstallmentTemplate(Base):
    __tablename__ = "tuition_installment_templates"

    id = Column(Integer, primary_key=True)
    plan_id = Column(
        Integer,
        ForeignKey("tuition_fee_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    sequence = Column(Integer, nullable=False)
    due_on = Column(Date, nullable=False)
    amount = Column(MONEY, nullable=False)

    __table_args__ = (
        UniqueConstraint("plan_id", "sequence", name="uq_tuition_template_sequence"),
        CheckConstraint("amount > 0", name="ck_tuition_template_amount_positive"),
        CheckConstraint("sequence > 0", name="ck_tuition_template_sequence_positive"),
        Index("ix_tuition_template_due", "plan_id", "due_on", "sequence"),
    )


class TuitionFeeAssignment(Base):
    __tablename__ = "tuition_fee_assignments"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_member_id = Column(
        Integer,
        ForeignKey("institution_members.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    plan_id = Column(
        Integer,
        ForeignKey("tuition_fee_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    currency = Column(String(3), nullable=False)
    gross_amount = Column(MONEY, nullable=False)
    status = Column(String(20), nullable=False, default="active")
    note = Column(String(500), nullable=False, default="")
    assigned_on = Column(Date, nullable=False)
    assigned_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_member_id", "plan_id", name="uq_tuition_student_plan"
        ),
        CheckConstraint(
            "status IN ('active','settled','cancelled')",
            name="ck_tuition_assignment_status",
        ),
        CheckConstraint(
            "gross_amount > 0", name="ck_tuition_assignment_gross_positive"
        ),
        Index(
            "ix_tuition_assignment_institution_status", "institution_id", "status", "id"
        ),
    )


class TuitionInstallment(Base):
    __tablename__ = "tuition_installments"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(
        Integer,
        ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    template_id = Column(
        Integer,
        ForeignKey("tuition_installment_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(120), nullable=False)
    sequence = Column(Integer, nullable=False)
    due_on = Column(Date, nullable=False, index=True)
    amount_due = Column(MONEY, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "assignment_id", "sequence", name="uq_tuition_installment_sequence"
        ),
        CheckConstraint(
            "amount_due > 0", name="ck_tuition_installment_amount_positive"
        ),
        Index(
            "ix_tuition_installment_assignment_due",
            "assignment_id",
            "due_on",
            "sequence",
        ),
    )


class TuitionPayment(Base):
    __tablename__ = "tuition_payments"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignment_id = Column(
        Integer,
        ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key = Column(String(64), nullable=False)
    request_hash = Column(String(64), nullable=False)
    amount = Column(MONEY, nullable=False)
    currency = Column(String(3), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=False)
    method = Column(String(30), nullable=False)
    reference = Column(String(120), nullable=False, default="")
    note = Column(String(500), nullable=False, default="")
    status = Column(String(20), nullable=False, default="posted")
    recorded_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # Cash desk (0043): who physically took cash or a cheque, and the second
    # person who counted it. Other methods carry ``not_required``.
    received_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    verification_status = Column(
        String(20),
        nullable=False,
        default="not_required",
        server_default="not_required",
    )
    verified_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_note = Column(
        String(300), nullable=False, default="", server_default=""
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id", "idempotency_key", name="uq_tuition_payment_idempotency"
        ),
        CheckConstraint("amount > 0", name="ck_tuition_payment_amount_positive"),
        CheckConstraint(
            "status IN ('posted','reversed')", name="ck_tuition_payment_status"
        ),
        CheckConstraint(
            "verification_status IN ('not_required','pending','verified')",
            name="ck_tuition_payment_verification",
        ),
        Index("ix_tuition_payment_assignment_paid", "assignment_id", "paid_at", "id"),
        Index(
            "ix_tuition_payment_verification",
            "institution_id",
            "verification_status",
            "paid_at",
        ),
    )


class TuitionAdjustment(Base):
    __tablename__ = "tuition_adjustments"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignment_id = Column(
        Integer,
        ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    installment_id = Column(
        Integer,
        ForeignKey("tuition_installments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    idempotency_key = Column(String(64), nullable=False)
    request_hash = Column(String(64), nullable=False)
    kind = Column(String(20), nullable=False)
    amount = Column(MONEY, nullable=False)
    reason = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="posted")
    approved_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "idempotency_key",
            name="uq_tuition_adjustment_idempotency",
        ),
        CheckConstraint(
            "kind IN ('discount','waiver')", name="ck_tuition_adjustment_kind"
        ),
        CheckConstraint(
            "status IN ('posted','reversed')", name="ck_tuition_adjustment_status"
        ),
        CheckConstraint("amount > 0", name="ck_tuition_adjustment_amount_positive"),
    )


class TuitionLedgerEntry(Base):
    __tablename__ = "tuition_ledger_entries"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignment_id = Column(
        Integer,
        ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    installment_id = Column(
        Integer,
        ForeignKey("tuition_installments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_id = Column(
        Integer, ForeignKey("tuition_payments.id", ondelete="RESTRICT"), nullable=True
    )
    adjustment_id = Column(
        Integer,
        ForeignKey("tuition_adjustments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    entry_type = Column(String(20), nullable=False)
    amount = Column(MONEY, nullable=False)
    effective_on = Column(Date, nullable=False, index=True)
    memo = Column(String(500), nullable=False, default="")
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_tuition_ledger_amount_nonzero"),
        CheckConstraint(
            "entry_type IN ('charge','payment','discount','waiver')",
            name="ck_tuition_ledger_type",
        ),
        CheckConstraint(
            "(entry_type = 'charge' AND amount > 0) OR "
            "(entry_type IN ('payment','discount','waiver') AND amount < 0)",
            name="ck_tuition_ledger_direction",
        ),
        CheckConstraint(
            "(entry_type = 'payment' AND payment_id IS NOT NULL AND adjustment_id IS NULL) OR "
            "(entry_type IN ('discount','waiver') AND adjustment_id IS NOT NULL AND payment_id IS NULL) OR "
            "(entry_type = 'charge' AND payment_id IS NULL AND adjustment_id IS NULL)",
            name="ck_tuition_ledger_source",
        ),
        UniqueConstraint(
            "payment_id", "installment_id", name="uq_tuition_payment_allocation"
        ),
        UniqueConstraint(
            "adjustment_id", "installment_id", name="uq_tuition_adjustment_allocation"
        ),
        Index(
            "ix_tuition_ledger_assignment_effective",
            "assignment_id",
            "effective_on",
            "id",
        ),
    )


class TuitionReceipt(Base):
    __tablename__ = "tuition_receipts"

    id = Column(Integer, primary_key=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assignment_id = Column(
        Integer,
        ForeignKey("tuition_fee_assignments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_id = Column(
        Integer,
        ForeignKey("tuition_payments.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    receipt_number = Column(String(50), nullable=False, unique=True)
    amount = Column(MONEY, nullable=False)
    currency = Column(String(3), nullable=False)
    balance_after = Column(MONEY, nullable=False)
    issued_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    issued_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_tuition_receipt_amount_positive"),
        CheckConstraint(
            "balance_after >= 0", name="ck_tuition_receipt_balance_nonnegative"
        ),
        Index(
            "ix_tuition_receipt_institution_issued", "institution_id", "issued_at", "id"
        ),
    )
