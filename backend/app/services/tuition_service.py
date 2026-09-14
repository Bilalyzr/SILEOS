"""Tenant-scoped tuition accounting for schools and colleges.

Every write locks the institution row and commits the source record, ledger
allocations, receipt and institution audit together.  Readers derive balances
from ledger entries; cached status is presentation/convenience state only.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.campus_operations import ParentLinkRequest
from app.models.institution import InstitutionMember
from app.models.tuition import (
    TuitionAdjustment,
    TuitionFeeAssignment,
    TuitionFeeComponent,
    TuitionFeePlan,
    TuitionInstallment,
    TuitionInstallmentTemplate,
    TuitionLedgerEntry,
    TuitionPayment,
    TuitionReceipt,
)
from app.models.user import User
from app.services import institution_service as institution_svc


CENT = Decimal("0.01")
ZERO = Decimal("0.00")
FEE_MANAGERS = ("owner", "admin")
CASH_METHODS = ("cash", "cheque")
RECEIVER_ROLES = ("owner", "admin", "teacher")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def number(value) -> float:
    return float(money(value))


def local_today(institution) -> date:
    try:
        zone = ZoneInfo(institution.timezone)
    except Exception:
        zone = timezone.utc
    return datetime.now(timezone.utc).astimezone(zone).date()


def _payload_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _manager_scope(db, institution_id, user, *, lock=False):
    return institution_svc.scope(db, institution_id, user, FEE_MANAGERS, lock=lock)


def _plan(db, institution_id, plan_id, *, lock=False):
    query = db.query(TuitionFeePlan).filter_by(
        id=plan_id, institution_id=institution_id
    )
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Tuition fee plan not found.")
    return row


def _plan_parts(db, plan_id):
    components = (
        db.query(TuitionFeeComponent)
        .filter_by(plan_id=plan_id)
        .order_by(TuitionFeeComponent.position)
        .all()
    )
    installments = (
        db.query(TuitionInstallmentTemplate)
        .filter_by(plan_id=plan_id)
        .order_by(TuitionInstallmentTemplate.sequence)
        .all()
    )
    return components, installments


def serialize_plan(db, row):
    components, installments = _plan_parts(db, row.id)
    return {
        "id": row.id,
        "name": row.name,
        "academic_year": row.academic_year,
        "currency": row.currency,
        "description": row.description,
        "status": row.status,
        "total_amount": number(row.total_amount),
        "components": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "amount": number(item.amount),
            }
            for item in components
        ],
        "installments": [
            {
                "id": item.id,
                "name": item.name,
                "sequence": item.sequence,
                "due_on": item.due_on,
                "amount": number(item.amount),
            }
            for item in installments
        ],
        "created_at": row.created_at,
    }


def create_plan(db, institution_id, user, data):
    _manager_scope(db, institution_id, user, lock=True)
    duplicate = (
        db.query(TuitionFeePlan)
        .filter_by(
            institution_id=institution_id,
            name=data.name,
            academic_year=data.academic_year,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            409, "A tuition fee plan with this name already exists for the year."
        )

    total = sum((money(item.amount) for item in data.components), ZERO)
    row = TuitionFeePlan(
        institution_id=institution_id,
        name=data.name,
        academic_year=data.academic_year,
        currency=data.currency,
        description=data.description,
        status="draft",
        total_amount=total,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    for position, item in enumerate(data.components, 1):
        db.add(
            TuitionFeeComponent(
                plan_id=row.id,
                code=item.code,
                name=item.name,
                amount=money(item.amount),
                position=position,
            )
        )
    for sequence, item in enumerate(data.installments, 1):
        db.add(
            TuitionInstallmentTemplate(
                plan_id=row.id,
                name=item.name,
                sequence=sequence,
                due_on=item.due_on,
                amount=money(item.amount),
            )
        )
    institution_svc.audit(
        db,
        institution_id,
        user,
        "tuition.plan_created",
        f"{row.name} · {row.academic_year} · {row.currency} {total}",
    )
    institution_svc.save(db)
    db.refresh(row)
    return serialize_plan(db, row)


def list_plans(db, institution_id, user):
    _manager_scope(db, institution_id, user)
    rows = (
        db.query(TuitionFeePlan)
        .filter_by(institution_id=institution_id)
        .order_by(
            TuitionFeePlan.academic_year.desc(), TuitionFeePlan.name, TuitionFeePlan.id
        )
        .limit(200)
        .all()
    )
    return {"items": [serialize_plan(db, row) for row in rows]}


def publish_plan(db, institution_id, plan_id, user):
    _manager_scope(db, institution_id, user, lock=True)
    row = _plan(db, institution_id, plan_id, lock=True)
    if row.status == "published":
        return serialize_plan(db, row)
    if row.status != "draft":
        raise HTTPException(409, "Only a draft tuition fee plan can be published.")
    components, installments = _plan_parts(db, row.id)
    component_total = sum((money(item.amount) for item in components), ZERO)
    installment_total = sum((money(item.amount) for item in installments), ZERO)
    if not components or not installments or component_total <= ZERO:
        raise HTTPException(
            409, "Add fee components and installments before publishing."
        )
    if component_total != installment_total or component_total != money(
        row.total_amount
    ):
        raise HTTPException(
            409, "Fee component and installment totals no longer match."
        )
    row.status = "published"
    institution_svc.audit(
        db,
        institution_id,
        user,
        "tuition.plan_published",
        f"{row.name} · {row.academic_year}",
    )
    institution_svc.save(db)
    db.refresh(row)
    return serialize_plan(db, row)


def _student(db, institution_id, member_id):
    result = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            InstitutionMember.id == member_id,
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.role == "student",
            InstitutionMember.status == "active",
            User.is_active.is_(True),
        )
        .first()
    )
    if not result:
        raise HTTPException(404, "Active student not found in this institution.")
    return result


def _assignment(db, institution_id, assignment_id, *, lock=False):
    query = db.query(TuitionFeeAssignment).filter_by(
        id=assignment_id, institution_id=institution_id
    )
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Tuition fee account not found.")
    return row


def assign_plan(db, institution_id, user, data):
    institution, _ = _manager_scope(db, institution_id, user, lock=True)
    plan = _plan(db, institution_id, data.plan_id, lock=True)
    if plan.status != "published":
        raise HTTPException(409, "Publish the tuition fee plan before assigning it.")
    member, _student_user = _student(db, institution_id, data.student_member_id)
    existing = (
        db.query(TuitionFeeAssignment)
        .filter_by(student_member_id=member.id, plan_id=plan.id)
        .first()
    )
    if existing:
        raise HTTPException(
            409, "This tuition fee plan is already assigned to the student."
        )
    templates = (
        db.query(TuitionInstallmentTemplate)
        .filter_by(plan_id=plan.id)
        .order_by(TuitionInstallmentTemplate.sequence)
        .all()
    )
    if not templates or sum((money(item.amount) for item in templates), ZERO) != money(
        plan.total_amount
    ):
        raise HTTPException(409, "The tuition plan installment schedule is invalid.")

    assigned_on = local_today(institution)
    row = TuitionFeeAssignment(
        institution_id=institution_id,
        student_member_id=member.id,
        plan_id=plan.id,
        currency=plan.currency,
        gross_amount=money(plan.total_amount),
        status="active",
        note=data.note,
        assigned_on=assigned_on,
        assigned_by=user.id,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "This tuition fee plan is already assigned to the student."
        ) from None

    for template in templates:
        installment = TuitionInstallment(
            assignment_id=row.id,
            template_id=template.id,
            name=template.name,
            sequence=template.sequence,
            due_on=template.due_on,
            amount_due=money(template.amount),
        )
        db.add(installment)
        db.flush()
        db.add(
            TuitionLedgerEntry(
                institution_id=institution_id,
                assignment_id=row.id,
                installment_id=installment.id,
                entry_type="charge",
                amount=money(template.amount),
                effective_on=assigned_on,
                memo=f"{plan.name}: {template.name}",
                created_by=user.id,
            )
        )
    institution_svc.audit(
        db,
        institution_id,
        user,
        "tuition.plan_assigned",
        f"Plan #{plan.id} → student member #{member.id}",
    )
    institution_svc.save(db)
    db.refresh(row)
    return serialize_assignment(db, row)


def _entries_by_installment(entries):
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry.installment_id].append(entry)
    return grouped


def _financial_snapshot(assignment, installments, entries, as_of):
    grouped = _entries_by_installment(entries)
    totals = {"assessed": ZERO, "discounts": ZERO, "waivers": ZERO, "paid": ZERO}
    for entry in entries:
        amount = money(entry.amount)
        if entry.entry_type == "charge":
            totals["assessed"] += amount
        elif entry.entry_type in ("payment", "discount", "waiver"):
            totals[
                {"payment": "paid", "discount": "discounts", "waiver": "waivers"}[
                    entry.entry_type
                ]
            ] += -amount

    rows = []
    aging = {
        "current": ZERO,
        "days_1_30": ZERO,
        "days_31_60": ZERO,
        "days_61_90": ZERO,
        "days_91_plus": ZERO,
    }
    overdue = ZERO
    due_today = ZERO
    due_next_30_days = ZERO
    outstanding_dates = []
    for installment in sorted(
        installments, key=lambda item: (item.due_on, item.sequence, item.id)
    ):
        raw_balance = sum(
            (money(entry.amount) for entry in grouped[installment.id]), ZERO
        )
        balance = max(ZERO, money(raw_balance))
        credited = max(ZERO, money(installment.amount_due) - balance)
        if balance <= ZERO:
            status = "paid"
        elif installment.due_on < as_of:
            status = "overdue"
        elif installment.due_on == as_of:
            status = "due"
        else:
            status = "upcoming"
        if balance > ZERO:
            outstanding_dates.append(installment.due_on)
            days = (as_of - installment.due_on).days
            if days <= 0:
                aging["current"] += balance
            elif days <= 30:
                aging["days_1_30"] += balance
            elif days <= 60:
                aging["days_31_60"] += balance
            elif days <= 90:
                aging["days_61_90"] += balance
            else:
                aging["days_91_plus"] += balance
            if installment.due_on < as_of:
                overdue += balance
            elif installment.due_on == as_of:
                due_today += balance
            elif installment.due_on <= as_of + timedelta(days=30):
                due_next_30_days += balance
        rows.append(
            {
                "id": installment.id,
                "name": installment.name,
                "sequence": installment.sequence,
                "due_on": installment.due_on,
                "amount_due": number(installment.amount_due),
                "credited": number(credited),
                "balance": number(balance),
                "status": status,
            }
        )
    return {
        **totals,
        "balance": sum((money(row["balance"]) for row in rows), ZERO),
        "overdue": overdue,
        "due_today": due_today,
        "due_next_30_days": due_next_30_days,
        "aging": aging,
        "oldest_due_on": min(outstanding_dates) if outstanding_dates else None,
        "installments": rows,
    }


def _snapshot_for(db, assignment, as_of=None):
    as_of = as_of or date.today()
    installments = (
        db.query(TuitionInstallment)
        .filter_by(assignment_id=assignment.id)
        .order_by(TuitionInstallment.due_on, TuitionInstallment.sequence)
        .all()
    )
    entries = (
        db.query(TuitionLedgerEntry)
        .filter(
            TuitionLedgerEntry.assignment_id == assignment.id,
            TuitionLedgerEntry.effective_on <= as_of,
        )
        .order_by(TuitionLedgerEntry.id)
        .all()
    )
    return _financial_snapshot(assignment, installments, entries, as_of)


def _student_dict(member, user):
    return {
        "member_id": member.id,
        "user_id": user.id,
        "name": user.display_name or "Student",
        "email": user.user_email,
    }


def _person(db, user_id):
    if not user_id:
        return None
    row = db.get(User, user_id)
    return {"id": user_id, "name": (row.display_name if row else None) or "Staff"}


def _payment_dict(db, payment):
    receipt = db.query(TuitionReceipt).filter_by(payment_id=payment.id).one()
    return {
        "id": payment.id,
        "amount": number(payment.amount),
        "paid_at": payment.paid_at,
        "method": payment.method,
        "reference": payment.reference,
        "note": payment.note,
        "status": payment.status,
        "receipt": {
            "id": receipt.id,
            "receipt_number": receipt.receipt_number,
            "issued_at": receipt.issued_at,
        },
        "received_by": _person(db, payment.received_by),
        "verification": {
            "status": payment.verification_status,
            "verified_by": _person(db, payment.verified_by),
            "verified_at": payment.verified_at,
            "note": payment.verification_note,
        },
    }


def _receiver(db, institution_id, data):
    """User id of the staff member who took cash or a cheque; None otherwise."""
    if data.method not in CASH_METHODS:
        return None
    if not data.received_by_member_id:
        raise HTTPException(422, "Choose who received the cash or cheque.")
    member = (
        db.query(InstitutionMember)
        .filter_by(
            id=data.received_by_member_id,
            institution_id=institution_id,
            status="active",
        )
        .first()
    )
    if not member or member.role not in RECEIVER_ROLES:
        raise HTTPException(
            404, "Receiver must be an active owner, admin or teacher of this institution."
        )
    return member.user_id


def _adjustment_dict(adjustment):
    return {
        "id": adjustment.id,
        "kind": adjustment.kind,
        "amount": number(adjustment.amount),
        "reason": adjustment.reason,
        "installment_id": adjustment.installment_id,
        "status": adjustment.status,
        "created_at": adjustment.created_at,
    }


def serialize_assignment(db, assignment, *, as_of=None):
    member, student = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.id == assignment.student_member_id)
        .one()
    )
    plan = db.get(TuitionFeePlan, assignment.plan_id)
    snapshot = _snapshot_for(db, assignment, as_of)
    payments = (
        db.query(TuitionPayment)
        .filter_by(assignment_id=assignment.id)
        .order_by(TuitionPayment.paid_at.desc(), TuitionPayment.id.desc())
        .limit(250)
        .all()
    )
    adjustments = (
        db.query(TuitionAdjustment)
        .filter_by(assignment_id=assignment.id)
        .order_by(TuitionAdjustment.id.desc())
        .limit(250)
        .all()
    )
    return {
        "id": assignment.id,
        "institution_id": assignment.institution_id,
        "student": _student_dict(member, student),
        "plan": {"id": plan.id, "name": plan.name, "academic_year": plan.academic_year},
        "currency": assignment.currency,
        "status": assignment.status,
        "assigned_on": assignment.assigned_on,
        "note": assignment.note,
        "gross_amount": number(assignment.gross_amount),
        "discounts_total": number(snapshot["discounts"]),
        "waivers_total": number(snapshot["waivers"]),
        "paid_total": number(snapshot["paid"]),
        "balance": number(snapshot["balance"]),
        "installments": snapshot["installments"],
        "payments": [_payment_dict(db, payment) for payment in payments],
        "adjustments": [_adjustment_dict(item) for item in adjustments],
    }


def _can_view_assignment(db, assignment, user):
    member = (
        db.query(InstitutionMember)
        .filter_by(
            institution_id=assignment.institution_id, user_id=user.id, status="active"
        )
        .first()
    )
    if member and member.role in FEE_MANAGERS:
        return True
    if (
        member
        and member.role == "student"
        and member.id == assignment.student_member_id
    ):
        return True
    if user.role == "parent":
        student_member = db.get(InstitutionMember, assignment.student_member_id)
        return bool(
            student_member
            and student_member.status == "active"
            and db.query(ParentLinkRequest)
            .filter_by(
                parent_user_id=user.id,
                student_user_id=student_member.user_id,
                status="approved",
            )
            .first()
        )
    return False


def assignment_detail(db, institution_id, assignment_id, user):
    row = _assignment(db, institution_id, assignment_id)
    if not _can_view_assignment(db, row, user):
        raise HTTPException(404, "Tuition fee account not found.")
    return serialize_assignment(db, row)


def self_accounts(db, institution_id, user, student_user_id=None):
    if user.role == "parent":
        if not student_user_id:
            raise HTTPException(422, "Choose an approved student account.")
        approved = (
            db.query(ParentLinkRequest)
            .filter_by(
                parent_user_id=user.id,
                student_user_id=student_user_id,
                status="approved",
            )
            .first()
        )
        if not approved:
            raise HTTPException(404, "Approved student account not found.")
        member_user_id = student_user_id
    else:
        if student_user_id and student_user_id != user.id:
            raise HTTPException(404, "Student account not found.")
        member_user_id = user.id
    result = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.user_id == member_user_id,
            InstitutionMember.role == "student",
            InstitutionMember.status == "active",
        )
        .first()
    )
    if not result:
        raise HTTPException(
            404, "Active student account not found in this institution."
        )
    member, student = result
    rows = (
        db.query(TuitionFeeAssignment)
        .filter_by(institution_id=institution_id, student_member_id=member.id)
        .order_by(
            TuitionFeeAssignment.assigned_on.desc(), TuitionFeeAssignment.id.desc()
        )
        .all()
    )
    return {
        "student": _student_dict(member, student),
        "assignments": [serialize_assignment(db, row) for row in rows],
    }


def _allocate_credit(
    db,
    assignment,
    snapshot,
    amount,
    *,
    entry_type,
    source,
    user,
    effective_on,
    installment_id=None,
):
    remaining = money(amount)
    states = snapshot["installments"]
    if installment_id:
        states = [row for row in states if row["id"] == installment_id]
        if not states:
            raise HTTPException(
                404, "Installment not found in this tuition fee account."
            )
    if remaining > sum((money(row["balance"]) for row in states), ZERO):
        raise HTTPException(422, "The amount exceeds the outstanding tuition balance.")
    for state in sorted(
        states, key=lambda row: (row["due_on"], row["sequence"], row["id"])
    ):
        available = money(state["balance"])
        allocation = min(remaining, available)
        if allocation <= ZERO:
            continue
        db.add(
            TuitionLedgerEntry(
                institution_id=assignment.institution_id,
                assignment_id=assignment.id,
                installment_id=state["id"],
                payment_id=source.id if entry_type == "payment" else None,
                adjustment_id=source.id
                if entry_type in ("discount", "waiver")
                else None,
                entry_type=entry_type,
                amount=-allocation,
                effective_on=effective_on,
                memo=(source.reference if entry_type == "payment" else source.reason)[
                    :500
                ],
                created_by=user.id,
            )
        )
        remaining -= allocation
        if remaining <= ZERO:
            break
    if remaining > ZERO:
        raise HTTPException(422, "The amount exceeds the outstanding tuition balance.")


def _existing_payment(db, institution_id, key, fingerprint):
    row = (
        db.query(TuitionPayment)
        .filter_by(institution_id=institution_id, idempotency_key=key)
        .first()
    )
    if not row:
        return None
    if row.request_hash != fingerprint:
        raise HTTPException(
            409, "This idempotency key was already used for another payment."
        )
    receipt = db.query(TuitionReceipt).filter_by(payment_id=row.id).first()
    if not receipt:
        raise HTTPException(
            409, "The existing payment is still being finalized. Retry shortly."
        )
    assignment = db.get(TuitionFeeAssignment, row.assignment_id)
    return {
        "replayed": True,
        "payment": _payment_dict(db, row),
        "balance": number(_snapshot_for(db, assignment)["balance"]),
    }


def _zone(institution):
    try:
        return ZoneInfo(institution.timezone)
    except Exception:
        return timezone.utc


def _post_payment(
    db,
    institution,
    assignment,
    actor,
    *,
    amount,
    paid_at,
    method,
    reference,
    note,
    idempotency_key,
    fingerprint,
    received_by=None,
):
    """Post one payment inside a savepoint: payment row, ledger allocations,
    numbered receipt, status refresh and audit. Shared by the counter
    (``record_payment``) and the online gateway (``tuition_collection``).
    The caller owns the outer commit and IntegrityError handling.
    Returns ``(payment, receipt, balance_after)``."""
    zone = _zone(institution)
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=zone)
    paid_at = paid_at.astimezone(timezone.utc)
    if paid_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(422, "Payment time cannot be in the future.")
    snapshot = _snapshot_for(db, assignment)
    amount = money(amount)
    if amount > money(snapshot["balance"]):
        raise HTTPException(422, "The payment exceeds the outstanding tuition balance.")
    payment = TuitionPayment(
        institution_id=institution.id,
        assignment_id=assignment.id,
        idempotency_key=idempotency_key,
        request_hash=fingerprint,
        amount=amount,
        currency=assignment.currency,
        paid_at=paid_at,
        method=method,
        reference=reference,
        note=note,
        status="posted",
        recorded_by=actor.id,
        received_by=received_by,
        verification_status="pending" if method in CASH_METHODS else "not_required",
    )
    with db.begin_nested():
        db.add(payment)
        db.flush()
        _allocate_credit(
            db,
            assignment,
            snapshot,
            amount,
            entry_type="payment",
            source=payment,
            user=actor,
            effective_on=paid_at.astimezone(zone).date(),
        )
        db.flush()
        balance_after = money(_snapshot_for(db, assignment)["balance"])
        receipt = TuitionReceipt(
            institution_id=institution.id,
            assignment_id=assignment.id,
            payment_id=payment.id,
            receipt_number=f"TF-{institution.id}-{paid_at.year}-{payment.id:08d}",
            amount=amount,
            currency=assignment.currency,
            balance_after=balance_after,
            issued_by=actor.id,
        )
        db.add(receipt)
        assignment.status = "settled" if balance_after == ZERO else "active"
        receiver = _person(db, received_by)
        institution_svc.audit(
            db,
            institution.id,
            actor,
            "tuition.payment_recorded",
            f"Account #{assignment.id} · {assignment.currency} {amount} · {method}"
            + (f" · received by {receiver['name']}" if receiver else ""),
        )
        db.flush()
    return payment, receipt, balance_after


def record_payment(db, institution_id, assignment_id, user, data, idempotency_key):
    institution, _ = _manager_scope(db, institution_id, user, lock=True)
    assignment = _assignment(db, institution_id, assignment_id, lock=True)
    amount = money(data.amount)
    fingerprint = _payload_hash(
        {
            "assignment_id": assignment_id,
            "amount": str(amount),
            "paid_at": data.paid_at.isoformat() if data.paid_at else None,
            "method": data.method,
            "reference": data.reference,
            "note": data.note,
            "received_by_member_id": data.received_by_member_id,
        }
    )
    existing = _existing_payment(db, institution_id, idempotency_key, fingerprint)
    if existing:
        return existing
    if assignment.status == "cancelled":
        raise HTTPException(
            409, "A cancelled tuition fee account cannot receive payments."
        )
    if amount > money(_snapshot_for(db, assignment)["balance"]):
        raise HTTPException(422, "The payment exceeds the outstanding tuition balance.")
    received_by = _receiver(db, institution_id, data)
    try:
        payment, receipt, balance_after = _post_payment(
            db,
            institution,
            assignment,
            user,
            amount=amount,
            paid_at=data.paid_at or datetime.now(timezone.utc),
            method=data.method,
            reference=data.reference,
            note=data.note,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
            received_by=received_by,
        )
    except IntegrityError:
        existing = _existing_payment(db, institution_id, idempotency_key, fingerprint)
        if existing:
            return existing
        raise HTTPException(
            409, "The payment could not be claimed safely. Retry with the same key."
        ) from None
    institution_svc.save(db)
    db.refresh(payment)
    # Receipt notices ride on the reminder ledger; failures never touch the payment.
    from app.services import tuition_reminders

    tuition_reminders.queue_receipt(db, institution, assignment, payment, receipt, user.id)
    return {
        "replayed": False,
        "payment": _payment_dict(db, payment),
        "balance": number(balance_after),
    }


def _existing_adjustment(db, institution_id, key, fingerprint):
    row = (
        db.query(TuitionAdjustment)
        .filter_by(institution_id=institution_id, idempotency_key=key)
        .first()
    )
    if not row:
        return None
    if row.request_hash != fingerprint:
        raise HTTPException(
            409, "This idempotency key was already used for another adjustment."
        )
    assignment = db.get(TuitionFeeAssignment, row.assignment_id)
    return {
        "replayed": True,
        "adjustment": _adjustment_dict(row),
        "balance": number(_snapshot_for(db, assignment)["balance"]),
    }


def record_adjustment(db, institution_id, assignment_id, user, data, idempotency_key):
    institution, _ = _manager_scope(db, institution_id, user, lock=True)
    assignment = _assignment(db, institution_id, assignment_id, lock=True)
    amount = money(data.amount)
    fingerprint = _payload_hash(
        {
            "assignment_id": assignment_id,
            "kind": data.kind,
            "amount": str(amount),
            "reason": data.reason,
            "installment_id": data.installment_id,
        }
    )
    existing = _existing_adjustment(db, institution_id, idempotency_key, fingerprint)
    if existing:
        return existing
    if assignment.status == "cancelled":
        raise HTTPException(409, "A cancelled tuition fee account cannot be adjusted.")
    snapshot = _snapshot_for(db, assignment)
    if amount > money(snapshot["balance"]):
        raise HTTPException(
            422, "The adjustment exceeds the outstanding tuition balance."
        )
    adjustment = TuitionAdjustment(
        institution_id=institution_id,
        assignment_id=assignment.id,
        installment_id=data.installment_id,
        idempotency_key=idempotency_key,
        request_hash=fingerprint,
        kind=data.kind,
        amount=amount,
        reason=data.reason,
        status="posted",
        approved_by=user.id,
    )
    try:
        with db.begin_nested():
            db.add(adjustment)
            db.flush()
            effective_on = local_today(institution)
            _allocate_credit(
                db,
                assignment,
                snapshot,
                amount,
                entry_type=data.kind,
                source=adjustment,
                user=user,
                effective_on=effective_on,
                installment_id=data.installment_id,
            )
            db.flush()
            balance_after = money(_snapshot_for(db, assignment)["balance"])
            assignment.status = "settled" if balance_after == ZERO else "active"
            institution_svc.audit(
                db,
                institution_id,
                user,
                f"tuition.{data.kind}_recorded",
                f"Account #{assignment.id} · {assignment.currency} {amount} · {data.reason}",
            )
            db.flush()
    except IntegrityError:
        existing = _existing_adjustment(
            db, institution_id, idempotency_key, fingerprint
        )
        if existing:
            return existing
        raise HTTPException(
            409, "The adjustment could not be claimed safely. Retry with the same key."
        ) from None
    institution_svc.save(db)
    db.refresh(adjustment)
    return {
        "replayed": False,
        "adjustment": _adjustment_dict(adjustment),
        "balance": number(balance_after),
    }


def _manager_assignments(db, institution_id, user, *, after_id=None, limit=None):
    _manager_scope(db, institution_id, user)
    query = db.query(TuitionFeeAssignment).filter_by(institution_id=institution_id)
    if after_id:
        query = query.filter(TuitionFeeAssignment.id > after_id)
    query = query.order_by(TuitionFeeAssignment.id)
    if limit:
        query = query.limit(limit)
    return query.all()


def _snapshots(db, assignments, as_of):
    ids = [row.id for row in assignments]
    if not ids:
        return {}
    installments = (
        db.query(TuitionInstallment)
        .filter(TuitionInstallment.assignment_id.in_(ids))
        .order_by(
            TuitionInstallment.assignment_id,
            TuitionInstallment.due_on,
            TuitionInstallment.sequence,
        )
        .all()
    )
    entries = (
        db.query(TuitionLedgerEntry)
        .filter(
            TuitionLedgerEntry.assignment_id.in_(ids),
            TuitionLedgerEntry.effective_on <= as_of,
        )
        .order_by(TuitionLedgerEntry.assignment_id, TuitionLedgerEntry.id)
        .all()
    )
    installments_by_assignment = defaultdict(list)
    entries_by_assignment = defaultdict(list)
    for row in installments:
        installments_by_assignment[row.assignment_id].append(row)
    for row in entries:
        entries_by_assignment[row.assignment_id].append(row)
    return {
        assignment.id: _financial_snapshot(
            assignment,
            installments_by_assignment[assignment.id],
            entries_by_assignment[assignment.id],
            as_of,
        )
        for assignment in assignments
    }


def list_assignments(
    db,
    institution_id,
    user,
    *,
    status=None,
    student_member_id=None,
    after_id=None,
    limit=100,
):
    institution, _ = _manager_scope(db, institution_id, user)
    query = db.query(TuitionFeeAssignment).filter_by(institution_id=institution_id)
    if status:
        query = query.filter(TuitionFeeAssignment.status == status)
    if student_member_id:
        query = query.filter(
            TuitionFeeAssignment.student_member_id == student_member_id
        )
    if after_id:
        query = query.filter(TuitionFeeAssignment.id > after_id)
    rows = query.order_by(TuitionFeeAssignment.id).limit(limit + 1).all()
    has_more = len(rows) > limit
    page = rows[:limit]
    snapshots = _snapshots(db, page, local_today(institution))
    member_rows = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.id.in_([row.student_member_id for row in page]))
        .all()
        if page
        else []
    )
    members = {member.id: (member, student) for member, student in member_rows}
    plan_rows = (
        db.query(TuitionFeePlan)
        .filter(TuitionFeePlan.id.in_([row.plan_id for row in page]))
        .all()
        if page
        else []
    )
    plans = {plan.id: plan for plan in plan_rows}
    items = []
    for row in page:
        snapshot = snapshots[row.id]
        member, student = members[row.student_member_id]
        plan = plans[row.plan_id]
        next_due = next(
            (
                item["due_on"]
                for item in snapshot["installments"]
                if money(item["balance"]) > ZERO
            ),
            None,
        )
        items.append(
            {
                "id": row.id,
                "student": _student_dict(member, student),
                "plan": {
                    "id": plan.id,
                    "name": plan.name,
                    "academic_year": plan.academic_year,
                },
                "currency": row.currency,
                "status": row.status,
                "gross_amount": number(row.gross_amount),
                "balance": number(snapshot["balance"]),
                "overdue": number(snapshot["overdue"]),
                "next_due_on": next_due,
            }
        )
    return {"items": items, "next_cursor": page[-1].id if has_more and page else None}


def summary(db, institution_id, user, as_of=None):
    institution, _ = _manager_scope(db, institution_id, user)
    as_of = as_of or local_today(institution)
    assignments = _manager_assignments(db, institution_id, user)
    snapshots = _snapshots(db, assignments, as_of)
    currencies = {row.currency for row in assignments}
    if len(currencies) > 1:
        raise HTTPException(409, "Tuition summary cannot combine multiple currencies.")
    totals = {
        "assessed": ZERO,
        "discounts": ZERO,
        "waivers": ZERO,
        "paid": ZERO,
        "outstanding": ZERO,
        "overdue": ZERO,
        "due_today": ZERO,
        "due_next_30_days": ZERO,
    }
    aging = {
        "current": ZERO,
        "days_1_30": ZERO,
        "days_31_60": ZERO,
        "days_61_90": ZERO,
        "days_91_plus": ZERO,
    }
    with_balance = 0
    overdue_accounts = 0
    for assignment in assignments:
        snapshot = snapshots[assignment.id]
        for key in totals:
            totals[key] += money(snapshot[key if key != "outstanding" else "balance"])
        for key in aging:
            aging[key] += money(snapshot["aging"][key])
        with_balance += snapshot["balance"] > ZERO
        overdue_accounts += snapshot["overdue"] > ZERO
    return {
        "as_of": as_of,
        "currency": next(iter(currencies), None),
        "mixed_currency": False,
        "totals": {key: number(value) for key, value in totals.items()},
        "accounts": {
            "total": len(assignments),
            "with_balance": with_balance,
            "overdue": overdue_accounts,
        },
        "aging": {key: number(value) for key, value in aging.items()},
    }


def aging(db, institution_id, user, as_of=None, *, after_id=None, limit=100):
    institution, _ = _manager_scope(db, institution_id, user)
    as_of = as_of or local_today(institution)
    assignments = _manager_assignments(
        db, institution_id, user, after_id=after_id, limit=limit + 1
    )
    has_more = len(assignments) > limit
    page = assignments[:limit]
    snapshots = _snapshots(db, page, as_of)
    members = {
        member.id: (member, student)
        for member, student in db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.id.in_([row.student_member_id for row in page]))
        .all()
    }
    plans = {
        row.id: row
        for row in db.query(TuitionFeePlan)
        .filter(TuitionFeePlan.id.in_([item.plan_id for item in page]))
        .all()
    }
    rows = []
    for assignment in page:
        snapshot = snapshots[assignment.id]
        if snapshot["balance"] <= ZERO:
            continue
        member, student = members[assignment.student_member_id]
        rows.append(
            {
                "assignment_id": assignment.id,
                "student_member_id": member.id,
                "student_user_id": student.id,
                "student_name": student.display_name or "Student",
                "plan_name": plans[assignment.plan_id].name,
                "currency": assignment.currency,
                "outstanding": number(snapshot["balance"]),
                "overdue": number(snapshot["overdue"]),
                "oldest_due_on": snapshot["oldest_due_on"],
                "aging": {
                    key: number(value) for key, value in snapshot["aging"].items()
                },
            }
        )
    return {
        "as_of": as_of,
        "rows": rows,
        "next_cursor": page[-1].id if has_more and page else None,
    }


def receipt_detail(db, institution_id, receipt_id, user):
    receipt = (
        db.query(TuitionReceipt)
        .filter_by(id=receipt_id, institution_id=institution_id)
        .first()
    )
    if not receipt:
        raise HTTPException(404, "Tuition receipt not found.")
    assignment = db.get(TuitionFeeAssignment, receipt.assignment_id)
    if not assignment or not _can_view_assignment(db, assignment, user):
        raise HTTPException(404, "Tuition receipt not found.")
    payment = db.get(TuitionPayment, receipt.payment_id)
    member, student = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.id == assignment.student_member_id)
        .one()
    )
    plan = db.get(TuitionFeePlan, assignment.plan_id)
    institution, _member = (
        institution_svc.scope(db, institution_id, user)
        if user.role != "parent"
        else (None, None)
    )
    if institution is None:
        from app.models.institution import Institution

        institution = db.get(Institution, institution_id)
    return {
        "id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "issued_at": receipt.issued_at,
        "institution_id": institution.id,
        "institution_name": institution.name,
        "student": _student_dict(member, student),
        "plan": {"id": plan.id, "name": plan.name, "academic_year": plan.academic_year},
        "amount": number(receipt.amount),
        "currency": receipt.currency,
        "balance_after": number(receipt.balance_after),
        "paid_at": payment.paid_at,
        "method": payment.method,
        "reference": payment.reference,
    }
