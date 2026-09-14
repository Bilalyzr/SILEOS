"""Fee collection on top of the tuition ledger.

Four concerns, one module:

* cash verification: a second owner/admin confirms cash or cheque was received;
* cash desk: the day's counter takings per receiver, plus CSV;
* documents: receipt PDF data and demand invoices (snapshots, never ledger writes);
* online orders: one Razorpay checkout per account, captured through the same
  posting core as counter payments (``tuition_service._post_payment``).

Gateway credentials are resolved through ``_creds`` and the client through
``_client`` so tests can swap both without touching the network.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import hmac
import io
import csv
import logging
import re
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.institution import Institution, InstitutionMember
from app.models.tuition import (
    TuitionFeeAssignment,
    TuitionFeePlan,
    TuitionInstallment,
    TuitionLedgerEntry,
    TuitionPayment,
    TuitionReceipt,
)
from app.models.tuition_collection import TuitionInvoice, TuitionOnlineOrder
from app.models.user import User
from app.services import institution_service as institution_svc
from app.services import tuition_service
from app.services.tuition_service import CASH_METHODS, money, number


log = logging.getLogger(__name__)
NOT_READY = "Online payment is not set up for this campus yet. Pay at the office or ask them to enable it."


# ------------------------------------------------------------------ helpers


def _institution(db, institution_id):
    row = db.get(Institution, institution_id)
    if not row:
        raise HTTPException(404, "Institution not found.")
    return row


def _viewable_assignment(db, institution_id, assignment_id, user, *, lock=False):
    query = db.query(TuitionFeeAssignment).filter_by(
        id=assignment_id, institution_id=institution_id
    )
    row = query.with_for_update().first() if lock else query.first()
    if not row or not tuition_service._can_view_assignment(db, row, user):
        raise HTTPException(404, "Tuition fee account not found.")
    return row


def _student_of(db, assignment):
    return (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.id == assignment.student_member_id)
        .one()
    )


def _safe_filename(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "file"


def _managers(db, institution_id):
    return (
        db.query(InstitutionMember)
        .filter(
            InstitutionMember.institution_id == institution_id,
            InstitutionMember.status == "active",
            InstitutionMember.role.in_(institution_svc.MANAGERS),
        )
        .all()
    )


# ------------------------------------------------------------ verification


def verify_payment(db, institution_id, payment_id, user, note):
    institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    payment = (
        db.query(TuitionPayment)
        .filter_by(id=payment_id, institution_id=institution_id)
        .with_for_update()
        .first()
    )
    if not payment:
        raise HTTPException(404, "Tuition payment not found.")
    if payment.status != "posted":
        raise HTTPException(409, "A reversed payment cannot be verified.")
    if payment.verification_status != "pending":
        raise HTTPException(
            409, "This payment does not need verification or is already verified."
        )
    tag = ""
    if payment.received_by == user.id:
        others = [m for m in _managers(db, institution_id) if m.user_id != user.id]
        if others:
            raise HTTPException(
                409,
                "The person who received the cash cannot verify it. Ask another owner or admin.",
            )
        tag = " · self_verified_sole_manager"
    payment.verification_status = "verified"
    payment.verified_by = user.id
    payment.verified_at = datetime.now(timezone.utc)
    payment.verification_note = note
    institution_svc.audit(
        db,
        institution_id,
        user,
        "tuition.payment.verified",
        f"Payment #{payment.id} · {payment.currency} {money(payment.amount)}{tag}",
    )
    institution_svc.save(db)
    return tuition_service._payment_dict(db, payment)


def pending_cash(db, institution_id):
    rows = (
        db.query(TuitionPayment.amount)
        .filter_by(institution_id=institution_id, verification_status="pending", status="posted")
        .all()
    )
    return len(rows), number(sum((money(r[0]) for r in rows), Decimal("0")))


def excess_order_count(db, institution_id):
    return (
        db.query(TuitionOnlineOrder)
        .filter_by(institution_id=institution_id, status="paid_excess")
        .count()
    )


# --------------------------------------------------------------- cash desk


def _day_window(institution, day):
    zone = tuition_service._zone(institution)
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(timezone.utc)


def _excess_orders(db, institution_id):
    rows = (
        db.query(TuitionOnlineOrder, InstitutionMember, User)
        .join(TuitionFeeAssignment, TuitionFeeAssignment.id == TuitionOnlineOrder.assignment_id)
        .join(InstitutionMember, InstitutionMember.id == TuitionFeeAssignment.student_member_id)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            TuitionOnlineOrder.institution_id == institution_id,
            TuitionOnlineOrder.status == "paid_excess",
        )
        .order_by(TuitionOnlineOrder.paid_at.desc())
        .all()
    )
    return [
        {
            "id": order.id,
            "student_name": student.display_name or "Student",
            "excess_amount": number(order.excess_amount),
            "currency": order.currency,
            "gateway_payment_id": order.gateway_payment_id,
            "paid_at": order.paid_at,
        }
        for order, _member, student in rows
    ]


def cash_desk(db, institution_id, user, day):
    institution, _ = institution_svc.scope(db, institution_id, user, institution_svc.MANAGERS)
    start, end = _day_window(institution, day)
    rows = (
        db.query(TuitionPayment, TuitionReceipt, TuitionFeeAssignment, TuitionFeePlan, User)
        .join(TuitionReceipt, TuitionReceipt.payment_id == TuitionPayment.id)
        .join(TuitionFeeAssignment, TuitionFeeAssignment.id == TuitionPayment.assignment_id)
        .join(TuitionFeePlan, TuitionFeePlan.id == TuitionFeeAssignment.plan_id)
        .join(InstitutionMember, InstitutionMember.id == TuitionFeeAssignment.student_member_id)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(
            TuitionPayment.institution_id == institution_id,
            TuitionPayment.method.in_(CASH_METHODS),
            TuitionPayment.paid_at >= start,
            TuitionPayment.paid_at < end,
        )
        .order_by(TuitionPayment.paid_at.desc(), TuitionPayment.id.desc())
        .all()
    )
    out_rows = []
    receivers = {}
    pending_total = Decimal("0")
    verified_total = Decimal("0")
    pending_count = 0
    currency = None
    for payment, receipt, _assignment, plan, student in rows:
        currency = currency or payment.currency
        detail = tuition_service._payment_dict(db, payment)
        out_rows.append(
            {
                "payment_id": payment.id,
                "receipt_id": receipt.id,
                "receipt_number": receipt.receipt_number,
                "student_name": student.display_name or "Student",
                "plan_name": plan.name,
                "amount": number(payment.amount),
                "currency": payment.currency,
                "method": payment.method,
                "reference": payment.reference,
                "paid_at": payment.paid_at,
                "status": payment.status,
                "received_by": detail["received_by"],
                "verification": detail["verification"],
            }
        )
        if payment.status != "posted":
            continue
        key = payment.received_by or 0
        bucket = receivers.setdefault(
            key,
            {"id": payment.received_by, "name": (detail["received_by"] or {}).get("name", "Unassigned"), "count": 0, "total": Decimal("0"), "pending": 0},
        )
        bucket["count"] += 1
        bucket["total"] += money(payment.amount)
        if payment.verification_status == "pending":
            bucket["pending"] += 1
            pending_total += money(payment.amount)
            pending_count += 1
        elif payment.verification_status == "verified":
            verified_total += money(payment.amount)
    return {
        "day": day,
        "currency": currency or "INR",
        "rows": out_rows,
        "receivers": [
            {**bucket, "total": number(bucket["total"])}
            for bucket in sorted(receivers.values(), key=lambda b: (-b["total"], b["name"]))
        ],
        "pending_total": number(pending_total),
        "verified_total": number(verified_total),
        "pending_count": pending_count,
        "excess_orders": _excess_orders(db, institution_id),
    }


def cash_desk_csv(db, institution_id, user, day):
    desk = cash_desk(db, institution_id, user, day)
    institution = _institution(db, institution_id)
    zone = tuition_service._zone(institution)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Receipt", "Student", "Plan", "Method", "Reference", "Amount", "Currency", "Paid at", "Received by", "Status", "Verified by"]
    )
    for row in desk["rows"]:
        writer.writerow(
            [
                row["receipt_number"],
                row["student_name"],
                row["plan_name"],
                row["method"],
                row["reference"],
                f"{row['amount']:.2f}",
                row["currency"],
                row["paid_at"].astimezone(zone).strftime("%Y-%m-%d %H:%M"),
                (row["received_by"] or {}).get("name", ""),
                row["verification"]["status"],
                (row["verification"]["verified_by"] or {}).get("name", ""),
            ]
        )
    filename = _safe_filename(f"cash-desk-{institution.slug}-{day.isoformat()}") + ".csv"
    return filename, buffer.getvalue()


# --------------------------------------------------------------- documents


def receipt_document(db, institution_id, receipt_id, user):
    detail = tuition_service.receipt_detail(db, institution_id, receipt_id, user)
    payment = db.get(TuitionPayment, db.get(TuitionReceipt, receipt_id).payment_id)
    institution = _institution(db, institution_id)
    entries = (
        db.query(TuitionLedgerEntry, TuitionInstallment)
        .join(TuitionInstallment, TuitionInstallment.id == TuitionLedgerEntry.installment_id)
        .filter(TuitionLedgerEntry.payment_id == payment.id)
        .order_by(TuitionInstallment.sequence)
        .all()
    )
    payment_dict = tuition_service._payment_dict(db, payment)
    detail.update(
        {
            "academic_year": institution.academic_year,
            "timezone": institution.timezone,
            "note": payment.note,
            "received_by": payment_dict["received_by"],
            "verification": payment_dict["verification"],
            "allocations": [
                {"installment": installment.name, "amount": number(-entry.amount)}
                for entry, installment in entries
            ],
        }
    )
    return detail


def _invoice_number(db, institution_id, year):
    seq = db.query(TuitionInvoice).filter_by(institution_id=institution_id).count() + 1
    return f"TI-{institution_id}-{year}-{seq:06d}"


def invoice_dict(db, invoice):
    assignment = db.get(TuitionFeeAssignment, invoice.assignment_id)
    member, student = _student_of(db, assignment)
    plan = db.get(TuitionFeePlan, assignment.plan_id)
    institution = _institution(db, invoice.institution_id)
    snapshot = tuition_service._snapshot_for(db, assignment)
    covered = {line["installment_id"] for line in invoice.lines_json}
    open_balance = sum(
        (money(row["balance"]) for row in snapshot["installments"] if row["id"] in covered),
        Decimal("0"),
    )
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "institution_id": institution.id,
        "institution_name": institution.name,
        "academic_year": institution.academic_year,
        "timezone": institution.timezone,
        "assignment_id": assignment.id,
        "installment_id": invoice.installment_id,
        "student": tuition_service._student_dict(member, student),
        "plan": {"id": plan.id, "name": plan.name, "academic_year": plan.academic_year},
        "amount": number(invoice.amount),
        "currency": invoice.currency,
        "due_on": invoice.due_on,
        "lines": invoice.lines_json,
        "status": "settled" if open_balance <= 0 else "open",
        "issued_by": tuition_service._person(db, invoice.issued_by),
        "issued_at": invoice.issued_at,
    }


def create_invoice(db, institution_id, assignment_id, user, installment_id):
    institution = _institution(db, institution_id)
    assignment = _viewable_assignment(db, institution_id, assignment_id, user, lock=True)
    snapshot = tuition_service._snapshot_for(db, assignment)
    rows = snapshot["installments"]
    if installment_id:
        rows = [row for row in rows if row["id"] == installment_id]
        if not rows:
            raise HTTPException(404, "Installment not found in this tuition fee account.")
    rows = [row for row in rows if money(row["balance"]) > 0]
    if not rows:
        raise HTTPException(
            422,
            "Nothing is due on this installment." if installment_id else "Nothing is due on this account.",
        )
    lines = [
        {
            "installment_id": row["id"],
            "name": row["name"],
            "due_on": row["due_on"].isoformat(),
            "amount_due": row["amount_due"],
            "credited": row["credited"],
            "balance": row["balance"],
        }
        for row in rows
    ]
    amount = sum((money(row["balance"]) for row in rows), Decimal("0"))
    due_on = min(row["due_on"] for row in rows)
    year = tuition_service.local_today(institution).year
    invoice = None
    for _attempt in range(2):
        invoice = TuitionInvoice(
            institution_id=institution_id,
            assignment_id=assignment.id,
            installment_id=installment_id,
            invoice_number=_invoice_number(db, institution_id, year),
            amount=amount,
            currency=assignment.currency,
            due_on=due_on,
            lines_json=lines,
            issued_by=user.id,
        )
        try:
            with db.begin_nested():
                db.add(invoice)
                db.flush()
            break
        except IntegrityError:
            invoice = None
    if invoice is None:
        raise HTTPException(409, "The invoice number could not be reserved. Retry.")
    institution_svc.audit(
        db,
        institution_id,
        user,
        "tuition.invoice.issued",
        f"{invoice.invoice_number} · Account #{assignment.id} · {assignment.currency} {amount}",
    )
    institution_svc.save(db)
    db.refresh(invoice)
    return invoice_dict(db, invoice)


def list_invoices(db, institution_id, assignment_id, user):
    assignment = _viewable_assignment(db, institution_id, assignment_id, user)
    rows = (
        db.query(TuitionInvoice)
        .filter_by(assignment_id=assignment.id)
        .order_by(TuitionInvoice.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [invoice_dict(db, row) for row in rows]}


def invoice_detail(db, institution_id, invoice_id, user):
    invoice = (
        db.query(TuitionInvoice).filter_by(id=invoice_id, institution_id=institution_id).first()
    )
    if not invoice:
        raise HTTPException(404, "Tuition invoice not found.")
    _viewable_assignment(db, institution_id, invoice.assignment_id, user)
    return invoice_dict(db, invoice)


# ----------------------------------------------------------- online orders


def _creds():
    from app.routers.payments import _razorpay_creds

    return _razorpay_creds()


def online_ready():
    key, secret = _creds()
    return bool(key and secret)


def _client():
    import razorpay

    key, secret = _creds()
    return razorpay.Client(auth=(key, secret))


def order_dict(db, order):
    payment = db.get(TuitionPayment, order.payment_id) if order.payment_id else None
    return {
        "id": order.id,
        "assignment_id": order.assignment_id,
        "installment_id": order.installment_id,
        "status": order.status,
        "amount": number(order.amount),
        "amount_paise": order.amount_paise,
        "currency": order.currency,
        "excess_amount": number(order.excess_amount),
        "gateway_order_id": order.gateway_order_id,
        "gateway_payment_id": order.gateway_payment_id,
        "created_at": order.created_at,
        "paid_at": order.paid_at,
        "payment": tuition_service._payment_dict(db, payment) if payment else None,
    }


def create_online_order(db, institution_id, assignment_id, user, installment_id, amount):
    if not online_ready():
        raise HTTPException(503, NOT_READY)
    institution = _institution(db, institution_id)
    assignment = _viewable_assignment(db, institution_id, assignment_id, user)
    if assignment.status == "cancelled":
        raise HTTPException(409, "A cancelled tuition fee account cannot receive payments.")
    if assignment.currency != "INR":
        raise HTTPException(422, "Online payment supports INR accounts only.")
    snapshot = tuition_service._snapshot_for(db, assignment)
    label = "Fee balance"
    if installment_id:
        row = next((r for r in snapshot["installments"] if r["id"] == installment_id), None)
        if not row:
            raise HTTPException(404, "Installment not found in this tuition fee account.")
        limit = money(row["balance"])
        label = row["name"]
    else:
        limit = money(snapshot["balance"])
    amount = money(amount) if amount is not None else limit
    if amount <= 0 or amount > limit:
        raise HTTPException(422, "The amount must be between 0.01 and the outstanding balance.")
    paise = int((amount * 100).to_integral_value())
    plan = db.get(TuitionFeePlan, assignment.plan_id)
    order = TuitionOnlineOrder(
        institution_id=institution_id,
        assignment_id=assignment.id,
        installment_id=installment_id,
        payer_user_id=user.id,
        gateway_order_id=f"pending-{uuid4().hex}",
        amount=amount,
        amount_paise=paise,
        currency="INR",
        status="created",
        excess_amount=Decimal("0"),
    )
    db.add(order)
    db.flush()
    try:
        gateway = _client().order.create(
            {
                "amount": paise,
                "currency": "INR",
                "receipt": f"tf-{order.id}",
                "notes": {"tuition_order_id": str(order.id), "institution_id": str(institution_id)},
            }
        )
    except Exception:
        db.rollback()
        log.exception("Razorpay tuition order failed (institution=%s account=%s)", institution_id, assignment_id)
        raise HTTPException(503, "Checkout could not start. Nothing was charged.") from None
    order.gateway_order_id = gateway["id"]
    institution_svc.audit(
        db,
        institution_id,
        user,
        "tuition.online_order.created",
        f"Order #{order.id} · Account #{assignment.id} · INR {amount} · {gateway['id']}",
    )
    institution_svc.save(db)
    db.refresh(order)
    key, _secret = _creds()
    return {
        "order": order_dict(db, order),
        "checkout": {
            "key": key,
            "order_id": gateway["id"],
            "amount_paise": paise,
            "currency": "INR",
            "name": institution.name,
            "description": f"{plan.name} · {label}",
            "prefill": {"name": user.display_name or "", "email": user.user_email or ""},
        },
    }


def fulfil_online_order(db, order, entity):
    """Apply one captured gateway payment to its order. Idempotent: the same
    payment id applied twice is a no-op. Raises ValueError when the entity does
    not match the order; the caller decides how to surface that."""
    order = (
        db.query(TuitionOnlineOrder)
        .filter_by(id=order.id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    payment_id = str(entity.get("id") or "")
    if not payment_id or entity.get("status") != "captured":
        raise ValueError("Payment is not captured.")
    if entity.get("order_id") != order.gateway_order_id:
        raise ValueError("Payment does not belong to this order.")
    if entity.get("currency") != "INR" or int(entity.get("amount", 0)) != order.amount_paise:
        raise ValueError("Payment amount or currency does not match the order.")
    if int(entity.get("amount_refunded", 0) or 0):
        raise ValueError("Payment was refunded at the gateway.")
    if order.gateway_payment_id:
        if order.gateway_payment_id != payment_id:
            raise ValueError("This order already has a different payment.")
        return order
    if db.query(TuitionOnlineOrder).filter_by(gateway_payment_id=payment_id).first():
        raise ValueError("This payment was already used for another order.")

    institution = _institution(db, order.institution_id)
    assignment = (
        db.query(TuitionFeeAssignment).filter_by(id=order.assignment_id).with_for_update().one()
    )
    payer = db.get(User, order.payer_user_id)
    now = datetime.now(timezone.utc)
    balance = money(tuition_service._snapshot_for(db, assignment)["balance"])
    post = min(money(order.amount), balance)
    if post > 0:
        payment, receipt, _balance_after = tuition_service._post_payment(
            db,
            institution,
            assignment,
            payer,
            amount=post,
            paid_at=now,
            method="online",
            reference=payment_id,
            note=f"Razorpay order {order.gateway_order_id}",
            idempotency_key=f"rzp:{payment_id}"[:64],
            fingerprint=hashlib.sha256(f"{order.id}:{payment_id}".encode()).hexdigest(),
            received_by=None,
        )
        order.payment_id = payment.id
        from app.services import tuition_reminders

        tuition_reminders.queue_receipt(db, institution, assignment, payment, receipt, payer.id)
    order.excess_amount = money(order.amount) - post
    order.status = "paid_excess" if order.excess_amount > 0 else "paid"
    order.gateway_payment_id = payment_id
    order.paid_at = now
    institution_svc.audit(
        db,
        order.institution_id,
        payer,
        "tuition.online_order.paid",
        f"Order #{order.id} · {payment_id} · posted INR {post}",
    )
    if order.excess_amount > 0:
        institution_svc.audit(
            db,
            order.institution_id,
            payer,
            "tuition.online_order.excess",
            f"Order #{order.id} · INR {order.excess_amount} needs a manual refund",
        )
    db.flush()
    return order


def _order_for(db, institution_id, order_id, user):
    order = (
        db.query(TuitionOnlineOrder).filter_by(id=order_id, institution_id=institution_id).first()
    )
    if not order:
        raise HTTPException(404, "Online order not found.")
    _viewable_assignment(db, institution_id, order.assignment_id, user)
    return order


def verify_online_order(db, institution_id, order_id, user, body):
    order = _order_for(db, institution_id, order_id, user)
    if body.razorpay_order_id != order.gateway_order_id:
        raise HTTPException(400, "Checkout does not belong to this order.")
    _key, secret = _creds()
    expected = hmac.new(
        secret.encode(),
        f"{order.gateway_order_id}|{body.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not secret or not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "Invalid payment signature.")
    try:
        entity = _client().payment.fetch(body.razorpay_payment_id)
        fulfil_online_order(db, order, entity)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Payment is being verified. Refresh; do not pay again.") from None
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        log.exception("Tuition online verify failed (order=%s)", order_id)
        raise HTTPException(503, "Payment verification is pending. Refresh; do not pay again.") from None
    db.refresh(order)
    return order_dict(db, order)


def reconcile_online_order(db, institution_id, order_id, user):
    order = _order_for(db, institution_id, order_id, user)
    if order.status != "created":
        return order_dict(db, order)
    try:
        items = _client().order.payments(order.gateway_order_id).get("items", [])
        for entity in items:
            if entity.get("status") == "captured":
                fulfil_online_order(db, order, entity)
                db.commit()
                break
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from None
    except Exception:
        db.rollback()
        log.exception("Tuition online reconcile failed (order=%s)", order_id)
        raise HTTPException(503, "Payment status is temporarily unavailable. Do not pay again.") from None
    db.refresh(order)
    return order_dict(db, order)
