"""Fee collection records that sit beside the tuition ledger.

``TuitionInvoice`` is a printable demand note: a snapshot of what was owed on
one installment (or the whole account) when it was issued. It never changes
the ledger. ``TuitionOnlineOrder`` is one Razorpay checkout for an account;
its capture posts a normal ``TuitionPayment`` through the shared posting core.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
)

from app.core.database import Base
from app.models.tuition import MONEY


ONLINE_ORDER_STATUSES = ("created", "paid", "paid_excess", "failed")


class TuitionInvoice(Base):
    __tablename__ = "tuition_invoices"

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
    invoice_number = Column(String(50), nullable=False, unique=True)
    amount = Column(MONEY, nullable=False)
    currency = Column(String(3), nullable=False)
    due_on = Column(Date, nullable=False)
    lines_json = Column(JSON, nullable=False, default=list)
    issued_by = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    issued_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_tuition_invoice_amount_positive"),
        Index("ix_tuition_invoice_institution_issued", "institution_id", "issued_at", "id"),
    )


class TuitionOnlineOrder(Base):
    __tablename__ = "tuition_online_orders"

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
    payer_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    gateway_order_id = Column(String(64), nullable=False, unique=True)
    gateway_payment_id = Column(String(64), nullable=True, unique=True)
    payment_id = Column(
        Integer,
        ForeignKey("tuition_payments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amount = Column(MONEY, nullable=False)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="created")
    excess_amount = Column(MONEY, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_tuition_online_order_amount_positive"),
        CheckConstraint(
            "status IN ('created','paid','paid_excess','failed')",
            name="ck_tuition_online_order_status",
        ),
        Index("ix_tuition_online_order_status", "institution_id", "status"),
    )
