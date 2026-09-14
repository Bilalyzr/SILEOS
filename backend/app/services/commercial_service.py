"""Transactional commercial workflows for every SashaInfinity vertical."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.business_verticals import REVENUE_STREAMS, normalize_vertical
from app.models.commercial import (
    CommercialContract,
    CommercialInvoice,
    CommercialInvoiceCounter,
    CommercialOffer,
    RevenueLedgerEvent,
)
from app.models.platform_tenant import PlatformTenantEntitlement
from app.services import platform_tenant_service as tenant_service


MONEY = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(value or 0).quantize(MONEY, rounding=ROUND_HALF_UP)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _stream(vertical: str, stream: str) -> tuple[str, str]:
    canonical = normalize_vertical(vertical)
    if canonical is None or stream not in REVENUE_STREAMS[canonical]:
        raise HTTPException(422, "Revenue stream does not belong to this business vertical.")
    return canonical, stream


def _commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This commercial record already exists.") from None


def _serialize_offer(row: CommercialOffer) -> dict:
    return {
        "id": row.id,
        "sku": row.sku,
        "business_vertical": row.business_vertical,
        "revenue_stream": row.revenue_stream,
        "name": row.name,
        "description": row.description,
        "billing_model": row.billing_model,
        "currency": row.currency,
        "unit_amount": float(row.unit_amount),
        "tax_code": row.tax_code,
        "entitlement_grants": row.entitlement_grants,
        "is_active": row.is_active,
    }


def _serialize_contract(row: CommercialContract) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "offer_id": row.offer_id,
        "status": row.status,
        "quantity": float(row.quantity),
        "unit_amount": float(row.unit_amount),
        "currency": row.currency,
        "billing_interval": row.billing_interval,
        "starts_on": row.starts_on,
        "ends_on": row.ends_on,
        "next_billing_on": row.next_billing_on,
        "external_reference": row.external_reference,
        "terms": row.terms,
    }


def _serialize_invoice(row: CommercialInvoice) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "contract_id": row.contract_id,
        "invoice_number": row.invoice_number,
        "status": row.status,
        "currency": row.currency,
        "subtotal": float(row.subtotal),
        "tax_amount": float(row.tax_amount),
        "discount_amount": float(row.discount_amount),
        "total_amount": float(row.total_amount),
        "lines": row.lines,
        "due_on": row.due_on,
        "issued_at": row.issued_at,
        "paid_at": row.paid_at,
    }


def _serialize_ledger(row: RevenueLedgerEvent) -> dict:
    sign = -1 if row.event_type == "refund" else 1
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "business_vertical": row.business_vertical,
        "revenue_stream": row.revenue_stream,
        "event_type": row.event_type,
        "status": row.status,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "source_event_key": row.source_event_key,
        "invoice_id": row.invoice_id,
        "currency": row.currency,
        "gross_amount": float(row.gross_amount) * sign,
        "tax_amount": float(row.tax_amount) * sign,
        "gateway_fee": float(row.gateway_fee),
        "partner_share": float(row.partner_share),
        "net_amount": float(row.net_amount) * sign,
        "occurred_at": row.occurred_at,
        "reverses_event_id": row.reverses_event_id,
        "metadata": row.metadata_json,
    }


def list_offers(db, vertical: str | None = None, active_only: bool = True) -> list[dict]:
    query = db.query(CommercialOffer)
    if vertical:
        canonical = normalize_vertical(vertical)
        if canonical is None:
            raise HTTPException(422, "Unknown business vertical.")
        query = query.filter(CommercialOffer.business_vertical == canonical)
    if active_only:
        query = query.filter(CommercialOffer.is_active.is_(True))
    return [_serialize_offer(row) for row in query.order_by(CommercialOffer.sku).all()]


def create_offer(db, command, actor_id: int) -> dict:
    vertical, stream = _stream(command.business_vertical, command.revenue_stream)
    row = CommercialOffer(
        **command.model_dump(
            exclude={
                "sku",
                "business_vertical",
                "revenue_stream",
                "entitlement_grants",
            }
        ),
        sku=command.sku.upper(),
        business_vertical=vertical,
        revenue_stream=stream,
        entitlement_grants=[grant.model_dump() for grant in command.entitlement_grants],
        created_by=actor_id,
    )
    db.add(row)
    tenant_service.audit(
        db,
        tenant_id=None,
        actor_id=actor_id,
        action="commercial.offer_created",
        target_type="commercial_offer",
        target_id=command.sku.upper(),
        after={"vertical": vertical, "stream": stream},
    )
    _commit(db)
    return _serialize_offer(row)


def create_contract(db, command, actor_id: int) -> dict:
    tenant = tenant_service.get_tenant(db, command.tenant_id, lock=True)
    if tenant.status in {"suspended", "archived"}:
        raise HTTPException(409, "This tenant cannot start a commercial contract.")
    offer = db.get(CommercialOffer, command.offer_id)
    if offer is None or not offer.is_active:
        raise HTTPException(404, "Active offer not found.")
    if offer.billing_model == "subscription" and not command.billing_interval:
        raise HTTPException(422, "A subscription contract needs a billing interval.")
    row = CommercialContract(
        tenant_id=tenant.id,
        offer_id=offer.id,
        status="active",
        quantity=command.quantity,
        unit_amount=command.unit_amount if command.unit_amount is not None else offer.unit_amount,
        currency=offer.currency,
        billing_interval=command.billing_interval,
        starts_on=command.starts_on,
        ends_on=command.ends_on,
        next_billing_on=command.next_billing_on,
        external_reference=command.external_reference,
        terms=command.terms,
        created_by=actor_id,
    )
    db.add(row)
    db.flush()
    tenant_service.audit(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="commercial.contract_created",
        target_type="commercial_contract",
        target_id=row.id,
        after={"offer_id": offer.id, "status": row.status},
    )
    tenant_service.enqueue(
        db,
        tenant_id=tenant.id,
        topic="commercial.contract.created",
        aggregate_type="commercial_contract",
        aggregate_id=row.id,
        payload={"contract_id": row.id, "tenant_id": tenant.id, "offer_id": offer.id},
        idempotency_key=f"commercial:contract:{row.id}:created:v1",
    )
    _commit(db)
    return _serialize_contract(row)


def _fiscal_year(on_date: date) -> str:
    start = on_date.year if on_date.month >= 4 else on_date.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def _next_invoice_number(db, due_on: date) -> str:
    fiscal_year = _fiscal_year(due_on)
    counter = (
        db.query(CommercialInvoiceCounter)
        .filter_by(fiscal_year=fiscal_year)
        .with_for_update()
        .first()
    )
    if counter is None:
        counter = CommercialInvoiceCounter(fiscal_year=fiscal_year, next_number=2)
        sequence = 1
        db.add(counter)
    else:
        sequence = counter.next_number
        counter.next_number += 1
    return f"SI/{fiscal_year}/{sequence:06d}"


def create_invoice(db, command, actor_id: int) -> dict:
    contract = (
        db.query(CommercialContract)
        .filter_by(id=command.contract_id)
        .with_for_update()
        .first()
    )
    if contract is None:
        raise HTTPException(404, "Contract not found.")
    if contract.status != "active":
        raise HTTPException(409, "Only an active contract can be invoiced.")
    offer = db.get(CommercialOffer, contract.offer_id)
    subtotal = money(Decimal(contract.quantity) * Decimal(contract.unit_amount))
    tax = money(command.tax_amount)
    discount = money(command.discount_amount)
    total = subtotal + tax - discount
    if total < 0:
        raise HTTPException(422, "Discount cannot exceed the invoice subtotal and tax.")
    now = datetime.now(timezone.utc)
    row = CommercialInvoice(
        tenant_id=contract.tenant_id,
        contract_id=contract.id,
        invoice_number=_next_invoice_number(db, command.due_on),
        status="issued",
        currency=contract.currency,
        subtotal=subtotal,
        tax_amount=tax,
        discount_amount=discount,
        total_amount=total,
        lines=[
            {
                "sku": offer.sku,
                "description": offer.name,
                "quantity": str(contract.quantity),
                "unit_amount": str(contract.unit_amount),
                "subtotal": str(subtotal),
                "business_vertical": offer.business_vertical,
                "revenue_stream": offer.revenue_stream,
                "note": command.note,
            }
        ],
        due_on=command.due_on,
        issued_at=now,
        created_by=actor_id,
    )
    db.add(row)
    db.flush()
    tenant_service.audit(
        db,
        tenant_id=contract.tenant_id,
        actor_id=actor_id,
        action="commercial.invoice_issued",
        target_type="commercial_invoice",
        target_id=row.id,
        after={"number": row.invoice_number, "total": str(total), "currency": row.currency},
    )
    tenant_service.enqueue(
        db,
        tenant_id=contract.tenant_id,
        topic="commercial.invoice.issued",
        aggregate_type="commercial_invoice",
        aggregate_id=row.id,
        payload={"invoice_id": row.id, "tenant_id": contract.tenant_id},
        idempotency_key=f"commercial:invoice:{row.id}:issued:v1",
    )
    _commit(db)
    return _serialize_invoice(row)


def _grant_entitlements(db, contract: CommercialContract, offer: CommercialOffer, actor_id: int):
    for grant in offer.entitlement_grants or []:
        vertical = normalize_vertical(grant.get("vertical"))
        feature_key = str(grant.get("feature_key") or "").strip()
        if vertical is None or not feature_key:
            continue
        row = (
            db.query(PlatformTenantEntitlement)
            .filter_by(
                tenant_id=contract.tenant_id,
                vertical=vertical,
                feature_key=feature_key,
            )
            .first()
        )
        if row is None:
            row = PlatformTenantEntitlement(
                tenant_id=contract.tenant_id,
                vertical=vertical,
                feature_key=feature_key,
            )
            db.add(row)
        row.enabled = True
        row.quota = grant.get("quota") or {}
        row.effective_from = datetime.now(timezone.utc)
        row.effective_through = None
        row.updated_by = actor_id


def record_payment(db, invoice_id: int, command, actor_id: int) -> dict:
    existing = (
        db.query(RevenueLedgerEvent)
        .filter_by(source_event_key=command.source_event_key)
        .first()
    )
    if existing:
        if existing.event_type != "capture" or existing.invoice_id != invoice_id:
            raise HTTPException(409, "This payment idempotency key belongs to another operation.")
        return _serialize_ledger(existing)
    invoice = (
        db.query(CommercialInvoice).filter_by(id=invoice_id).with_for_update().first()
    )
    if invoice is None:
        raise HTTPException(404, "Invoice not found.")
    if invoice.status not in {"issued", "overdue"}:
        raise HTTPException(409, "This invoice cannot accept a payment.")
    contract = db.get(CommercialContract, invoice.contract_id)
    offer = db.get(CommercialOffer, contract.offer_id) if contract else None
    if contract is None or offer is None:
        raise HTTPException(409, "Invoice commercial attribution is incomplete.")
    gross = money(invoice.total_amount)
    tax = money(invoice.tax_amount)
    gateway_fee = money(command.gateway_fee)
    partner_share = money(command.partner_share)
    net = gross - tax - gateway_fee - partner_share
    if net < 0:
        raise HTTPException(422, "Tax, gateway fee, and partner share exceed the payment.")
    event = RevenueLedgerEvent(
        tenant_id=invoice.tenant_id,
        business_vertical=offer.business_vertical,
        revenue_stream=offer.revenue_stream,
        event_type="capture",
        status="posted",
        source_type="commercial_invoice",
        source_id=str(invoice.id),
        source_event_key=command.source_event_key,
        invoice_id=invoice.id,
        currency=invoice.currency,
        gross_amount=gross,
        tax_amount=tax,
        gateway_fee=gateway_fee,
        partner_share=partner_share,
        net_amount=net,
        occurred_at=_utc(command.occurred_at),
        metadata_json={**command.metadata, "payment_reference": command.payment_reference},
        recorded_by=actor_id,
    )
    db.add(event)
    invoice.status = "paid"
    invoice.paid_at = _utc(command.occurred_at)
    _grant_entitlements(db, contract, offer, actor_id)
    tenant_service.audit(
        db,
        tenant_id=invoice.tenant_id,
        actor_id=actor_id,
        action="commercial.payment_recorded",
        target_type="revenue_ledger_event",
        target_id=command.source_event_key,
        reason=command.reason,
        after={"invoice_id": invoice.id, "gross": str(gross), "currency": invoice.currency},
    )
    tenant_service.enqueue(
        db,
        tenant_id=invoice.tenant_id,
        topic="commercial.payment.captured",
        aggregate_type="commercial_invoice",
        aggregate_id=invoice.id,
        payload={"invoice_id": invoice.id, "tenant_id": invoice.tenant_id},
        idempotency_key=f"outbox:{command.source_event_key}",
    )
    _commit(db)
    return _serialize_ledger(event)


def record_refund(db, event_id: int, command, actor_id: int) -> dict:
    existing = (
        db.query(RevenueLedgerEvent)
        .filter_by(source_event_key=command.source_event_key)
        .first()
    )
    if existing:
        if existing.event_type != "refund" or existing.reverses_event_id != event_id:
            raise HTTPException(409, "This refund idempotency key belongs to another operation.")
        return _serialize_ledger(existing)
    capture = (
        db.query(RevenueLedgerEvent).filter_by(id=event_id).with_for_update().first()
    )
    if capture is None or capture.event_type != "capture" or capture.status != "posted":
        raise HTTPException(404, "Posted capture event not found.")
    already_refunded = sum(
        (
            money(row.gross_amount)
            for row in db.query(RevenueLedgerEvent)
            .filter_by(reverses_event_id=capture.id, event_type="refund", status="posted")
            .all()
        ),
        Decimal("0"),
    )
    amount = money(command.amount)
    if already_refunded + amount > money(capture.gross_amount):
        raise HTTPException(409, "Refund exceeds the remaining captured amount.")
    tax = money(command.tax_amount)
    if tax > amount:
        raise HTTPException(422, "Refunded tax cannot exceed the refund amount.")
    event = RevenueLedgerEvent(
        tenant_id=capture.tenant_id,
        business_vertical=capture.business_vertical,
        revenue_stream=capture.revenue_stream,
        event_type="refund",
        status="posted",
        source_type=capture.source_type,
        source_id=capture.source_id,
        source_event_key=command.source_event_key,
        invoice_id=capture.invoice_id,
        currency=capture.currency,
        gross_amount=amount,
        tax_amount=tax,
        gateway_fee=0,
        partner_share=0,
        net_amount=amount - tax,
        occurred_at=_utc(command.occurred_at),
        metadata_json={**command.metadata, "refund_reference": command.refund_reference},
        recorded_by=actor_id,
        reverses_event_id=capture.id,
    )
    db.add(event)
    if capture.invoice_id and already_refunded + amount == money(capture.gross_amount):
        invoice = db.get(CommercialInvoice, capture.invoice_id)
        if invoice:
            invoice.status = "refunded"
    tenant_service.audit(
        db,
        tenant_id=capture.tenant_id,
        actor_id=actor_id,
        action="commercial.refund_recorded",
        target_type="revenue_ledger_event",
        target_id=command.source_event_key,
        reason=command.reason,
        after={"capture_event_id": capture.id, "gross": str(amount)},
    )
    tenant_service.enqueue(
        db,
        tenant_id=capture.tenant_id,
        topic="commercial.payment.refunded",
        aggregate_type="revenue_ledger_event",
        aggregate_id=capture.id,
        payload={"capture_event_id": capture.id, "refund_event_key": command.source_event_key},
        idempotency_key=f"outbox:{command.source_event_key}",
    )
    _commit(db)
    return _serialize_ledger(event)


def list_ledger(
    db,
    *,
    start: datetime,
    end: datetime,
    vertical: str | None = None,
    tenant_id: int | None = None,
) -> list[dict]:
    if end <= start:
        raise HTTPException(422, "end must be later than start")
    query = db.query(RevenueLedgerEvent).filter(
        RevenueLedgerEvent.occurred_at >= _utc(start),
        RevenueLedgerEvent.occurred_at < _utc(end),
        RevenueLedgerEvent.status == "posted",
    )
    if vertical:
        canonical = normalize_vertical(vertical)
        if canonical is None:
            raise HTTPException(422, "Unknown business vertical.")
        query = query.filter(RevenueLedgerEvent.business_vertical == canonical)
    if tenant_id:
        query = query.filter(RevenueLedgerEvent.tenant_id == tenant_id)
    return [
        _serialize_ledger(row)
        for row in query.order_by(RevenueLedgerEvent.occurred_at.desc(), RevenueLedgerEvent.id.desc())
        .limit(2000)
        .all()
    ]
