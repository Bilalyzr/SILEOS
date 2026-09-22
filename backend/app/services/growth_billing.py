"""Contract billing and delivery built on the existing commercial ledger."""
import calendar
import hashlib
import hmac
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func
from app.models.commercial import CommercialContract, CommercialOffer, CommercialInvoice, RevenueLedgerEvent
from app.models.growth import BillingPolicy, BillingOccurrence, CommercialDelivery, PartnerAccrual, PartnerSettlement
from app.models.platform_tenant import PlatformTenantMembership, PlatformTenant
from app.models.user import User
from app.schemas.commercial import InvoiceCreate, PaymentRecord, RefundRecord
from app.services import commercial_service as commerce
from app.services.platform_tenant_service import audit

RESOURCE_STREAMS = {
    "asset_license": ("meiporul", "asset_licensing"), "lab_deployment": ("meiporul", "lab_deployment"),
    "amc": ("meiporul", "amc_support"), "device_service": ("meiporul", "amc_support"),
    "institution_saas": ("seyappaduporul", "institution_operations"),
    "managed_service": ("seyappaduporul", "institution_operations"),
    "franchise": ("seyappaduporul", "franchise_services"),
    "premium_credential": ("utporul", "credentials"), "career_service": ("utporul", "career_services"),
    "creator_commerce": ("utporul", "creator_commerce"),
}


def today():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def tenant_access(db, tenant_id, user, *, finance=False):
    tenant = db.get(PlatformTenant, tenant_id)
    if not tenant or tenant.status in {"suspended", "archived"}:
        raise HTTPException(404, "Active customer workspace not found")
    if user.role in {"admin", "superadmin"}:
        return tenant
    member = db.query(PlatformTenantMembership).filter_by(tenant_id=tenant_id, user_id=user.id, status="active").first()
    if not member or (finance and member.role not in {"owner", "admin", "finance"}):
        raise HTTPException(403, "You do not have billing access to this workspace")
    return tenant


def advance(on, interval, anchor):
    months = {"monthly": 1, "quarterly": 3, "annual": 12}[interval]
    n = on.year * 12 + on.month - 1 + months
    year, month = n // 12, n % 12 + 1
    return date(year, month, min(anchor, calendar.monthrange(year, month)[1]))


def set_policy(db, contract_id, command, actor):
    contract = db.query(CommercialContract).filter_by(id=contract_id).with_for_update().first()
    if not contract:
        raise HTTPException(404, "Contract not found")
    offer = db.get(CommercialOffer, contract.offer_id)
    if RESOURCE_STREAMS[command.resource_type] != (offer.business_vertical, offer.revenue_stream):
        raise HTTPException(422, "The fulfillment type must match the offer's pillar and revenue stream")
    if contract.currency != "INR":
        raise HTTPException(422, "This GST billing workflow currently supports INR")
    if command.automation_enabled and not contract.billing_interval:
        raise HTTPException(422, "Recurring billing requires a contract interval")
    if command.automation_enabled and offer.billing_model != "subscription":
        raise HTTPException(422, "Only subscription agreements may issue automatic recurring invoices")
    for uid in (command.partner_id, command.recipient_id):
        if uid and not db.get(User, uid):
            raise HTTPException(422, "Recipient account does not exist")
    policy = db.get(BillingPolicy, contract_id)
    if not policy:
        policy = BillingPolicy(contract_id=contract_id, created_by=actor.id)
        db.add(policy)
    for key, value in command.model_dump(mode="json").items():
        setattr(policy, key, value)
    if command.automation_enabled and not contract.next_billing_on:
        contract.next_billing_on = contract.starts_on
    audit(db, tenant_id=contract.tenant_id, actor_id=actor.id, action="growth.billing_policy",
          target_type="commercial_contract", target_id=contract_id, after={"resource_type": policy.resource_type, "automated": policy.automation_enabled})
    commerce._commit(db)
    return {"contract_id": contract_id, **command.model_dump(mode="json")}


def tax_breakdown(subtotal, profile):
    # Rate and classification come from a reviewed profile, never an inferred default.
    tax = commerce.money(subtotal * Decimal(profile["rate_bps"]) / 10000)
    if profile.get("reverse_charge"):
        return {"cgst": "0.00", "sgst": "0.00", "igst": "0.00", "reverse_charge_tax": str(tax), "total": "0.00"}
    same = profile["supplier_state"] == profile["place_of_supply"]
    half = commerce.money(tax / 2)
    return {"cgst": str(half if same else 0), "sgst": str(tax - half if same else 0), "igst": str(0 if same else tax), "total": str(tax)}


def issue(db, contract_id, period_key, actor_id, *, milestone_bps=10000, scheduled=False):
    contract = db.query(CommercialContract).filter_by(id=contract_id).with_for_update().first()
    if not contract or contract.status != "active":
        raise HTTPException(409, "An active contract is required")
    existing = db.query(BillingOccurrence).filter_by(contract_id=contract_id, period_key=period_key).first()
    if existing:
        if existing.snapshot.get("milestone_bps", 10000) != milestone_bps:
            raise HTTPException(409, "Billing key was already used for a different amount")
        return commerce._serialize_invoice(db.get(CommercialInvoice, existing.invoice_id))
    policy = db.get(BillingPolicy, contract_id)
    if not policy:
        raise HTTPException(409, "Configure reviewed tax and fulfillment details first")
    offer = db.get(CommercialOffer, contract.offer_id)
    if contract.starts_on > today():
        raise HTTPException(409, "Contract has not started")
    if contract.billing_interval:
        cycle = contract.next_billing_on or contract.starts_on
        if cycle > today() or (contract.ends_on and cycle >= contract.ends_on):
            raise HTTPException(409, "No billing cycle is due")
        if period_key != "cycle:" + cycle.isoformat():
            raise HTTPException(422, "Use the due cycle key: cycle:" + cycle.isoformat())
        scheduled = True
        contract.next_billing_on = cycle
    base = commerce.money(contract.quantity * contract.unit_amount)
    if offer.billing_model == "milestone":
        portions = sum(int((r.snapshot or {}).get("milestone_bps", 0)) for r in db.query(BillingOccurrence).filter_by(contract_id=contract_id))
        if portions + milestone_bps > 10000:
            raise HTTPException(409, "Milestone invoices exceed the agreed contract value")
    elif milestone_bps != 10000:
        raise HTTPException(422, "Partial amounts are reserved for milestone contracts")
    elif offer.billing_model in {"one_time", "royalty"} and db.query(BillingOccurrence.id).filter_by(contract_id=contract_id).first():
        raise HTTPException(409, "This one-time agreement has already been invoiced")
    subtotal = commerce.money(base * Decimal(milestone_bps) / 10000)
    if offer.billing_model == "milestone" and portions + milestone_bps == 10000:
        prior_total = db.query(func.coalesce(func.sum(CommercialInvoice.subtotal), 0)).join(
            BillingOccurrence, BillingOccurrence.invoice_id == CommercialInvoice.id).filter(BillingOccurrence.contract_id == contract_id).scalar()
        subtotal = base - Decimal(prior_total)
    taxes = tax_breakdown(subtotal, policy.tax_profile)
    period_start = contract.next_billing_on if scheduled else today()
    through = advance(period_start, contract.billing_interval, contract.starts_on.day) if contract.billing_interval else contract.ends_on
    if through and contract.ends_on:
        through = min(through, contract.ends_on)
    snapshot = {"tax_profile": policy.tax_profile, "taxes": taxes, "resource_type": policy.resource_type,
        "resource_reference": policy.resource_reference, "recipient_id": policy.recipient_id,
        "partner_id": policy.partner_id, "partner_bps": policy.partner_bps,
        "valid_until": through.isoformat() if through else None, "milestone_bps": milestone_bps,
        "period_start": period_start.isoformat(), "attribution": (contract.terms or {}).get("attribution", {}),
        "experiment_assignments": (contract.terms or {}).get("experiment_assignments", []),
        "entitlement_grants": offer.entitlement_grants or []}
    data = commerce.create_invoice(db, InvoiceCreate(contract_id=contract_id, tax_amount=taxes["total"],
        due_on=today() + timedelta(days=policy.payment_terms_days), note=period_key), actor_id,
        commit=False, subtotal_override=subtotal, number_on=today())
    invoice = db.get(CommercialInvoice, data["id"])
    invoice.lines = [{**line, "billing_snapshot": snapshot} for line in invoice.lines]
    db.add(BillingOccurrence(contract_id=contract_id, period_key=period_key, invoice_id=invoice.id, snapshot=snapshot))
    if scheduled:
        contract.next_billing_on = advance(period_start, contract.billing_interval, contract.starts_on.day)
    commerce._commit(db)
    return commerce._serialize_invoice(invoice)


def invoice_snapshot(db, invoice_id):
    occurrence = db.query(BillingOccurrence).filter_by(invoice_id=invoice_id).first()
    return occurrence.snapshot if occurrence else None


def invoice_partner_share(db, invoice, basis, fallback):
    snapshot = invoice_snapshot(db, invoice.id)
    return commerce.money(basis * Decimal(snapshot.get("partner_bps", 0)) / 10000) if snapshot else fallback


def on_capture(db, invoice, event):
    snapshot = invoice_snapshot(db, invoice.id)
    if not snapshot:
        return
    event.metadata_json = {**event.metadata_json, "attribution": snapshot.get("attribution", {}),
        "experiment_assignments": snapshot.get("experiment_assignments", [])}
    if snapshot.get("partner_id") and event.partner_share:
        db.add(PartnerAccrual(event_id=event.id, partner_id=snapshot["partner_id"], amount=event.partner_share,
            currency=event.currency, available_on=today() + timedelta(days=14)))
    previous = db.query(CommercialDelivery).join(CommercialInvoice,CommercialInvoice.id == CommercialDelivery.invoice_id).filter(
        CommercialInvoice.contract_id == invoice.contract_id, CommercialInvoice.status == 'paid',
        CommercialDelivery.resource_type == snapshot['resource_type'], CommercialDelivery.resource_reference == snapshot['resource_reference'],
        CommercialDelivery.status.in_(['active','expired']), CommercialDelivery.completed_at.isnot(None)).first()
    renewal = previous is not None and snapshot['resource_type'] in {'asset_license','institution_saas','amc','franchise'}
    db.add(CommercialDelivery(invoice_id=invoice.id, tenant_id=invoice.tenant_id,
        resource_type=snapshot["resource_type"], resource_reference=snapshot["resource_reference"],
        recipient_id=snapshot.get("recipient_id"), status="active" if renewal else "pending",
        completed_at=datetime.now(timezone.utc) if renewal else None,
        evidence=f'Paid renewal of fulfilled delivery {previous.id}' if renewal else '',
        valid_until=date.fromisoformat(snapshot["valid_until"]) if snapshot.get("valid_until") else None))


def on_refund(db, capture, refund, full):
    if full and capture.source_type == 'campus_subscription':
        from app.services.growth_campus_ledger import recompute_paid_through
        recompute_paid_through(db, capture)
    refund.metadata_json = {**refund.metadata_json, "attribution": (capture.metadata_json or {}).get("attribution", {})}
    accrual = db.query(PartnerAccrual).filter_by(event_id=capture.id).first()
    if accrual:
        # Sum prior clawbacks so rounding never recovers more than the original share.
        previous = db.query(func.coalesce(func.sum(PartnerAccrual.amount), 0)).join(
            RevenueLedgerEvent, RevenueLedgerEvent.id == PartnerAccrual.event_id).filter(
            RevenueLedgerEvent.reverses_event_id == capture.id, PartnerAccrual.event_id != refund.id).scalar()
        remaining = max(Decimal(0), accrual.amount + Decimal(previous))
        share = remaining if full else min(remaining, commerce.money(accrual.amount * refund.gross_amount / capture.gross_amount))
        db.add(PartnerAccrual(event_id=refund.id, partner_id=accrual.partner_id, amount=-share,
            currency=refund.currency, available_on=today()))
        refund.partner_share = share
        refund.net_amount = max(Decimal(0), refund.net_amount - share)
    delivery = db.query(CommercialDelivery).filter_by(invoice_id=capture.invoice_id).first()
    if full and delivery:
        delivery.status = "revoked"


def complete_delivery(db, delivery_id, evidence, actor):
    row = db.query(CommercialDelivery).filter_by(id=delivery_id).with_for_update().first()
    if not row or row.status in {"revoked", "expired"}:
        raise HTTPException(409, "This delivery is unavailable")
    if db.get(CommercialInvoice, row.invoice_id).status != "paid":
        raise HTTPException(409, "A captured payment is required")
    if row.valid_until and row.valid_until <= today():
        raise HTTPException(409, "The purchased period has expired")
    if row.resource_type == "asset_license":
        from app.models.three_d import ThreeDModel
        if not row.resource_reference.isdigit() or not db.get(ThreeDModel, int(row.resource_reference)):
            raise HTTPException(422, "Asset license fulfillment requires an existing 3D model ID")
    if row.resource_type == "institution_saas" and row.resource_reference not in {"campus", "enterprise"}:
        raise HTTPException(422, "Institution SaaS reference must select campus or enterprise")
    if row.resource_type == "premium_credential":
        from app.models.enrollment import Enrollment
        if not row.recipient_id or not row.resource_reference.isdigit():
            raise HTTPException(422, "Credential fulfillment requires a recipient and a course ID")
        enrollment = db.query(Enrollment).filter_by(user_id=row.recipient_id, course_id=int(row.resource_reference), enrollment_status="completed").first()
        if not enrollment:
            raise HTTPException(409, "The learner must complete the course before premium credential delivery")
        from app.services.certificate_service import CertificateService
        certificate, _ = CertificateService.issue_certificate_for_enrollment(db, enrollment)
        if not certificate or not certificate.is_valid:
            raise HTTPException(409, "Credential issuance did not pass the existing completion and certificate checks")
    row.status = "active" if row.resource_type in {"asset_license", "amc", "institution_saas", "franchise"} else "completed"
    row.evidence = evidence
    row.completed_at = datetime.now(timezone.utc)
    audit(db, tenant_id=row.tenant_id, actor_id=actor.id, action="growth.delivery_completed", target_type="delivery", target_id=row.id)
    commerce._commit(db)
    return {"id": row.id, "status": row.status}


def settle(db, command, actor):
    if not db.query(User).filter_by(id=command.partner_id).with_for_update().first():
        raise HTTPException(404, "Partner not found")
    prior = db.query(PartnerSettlement).filter_by(reference=command.reference).first()
    if prior:
        if (prior.partner_id, prior.currency, prior.amount) != (command.partner_id, command.currency, command.expected_amount):
            raise HTTPException(409, "Settlement reference belongs to another payout")
        return {"id": prior.id, "amount": float(prior.amount)}
    rows = db.query(PartnerAccrual).filter(PartnerAccrual.partner_id == command.partner_id,
        PartnerAccrual.currency == command.currency, PartnerAccrual.settlement_id.is_(None), PartnerAccrual.available_on <= today()).with_for_update().all()
    amount = commerce.money(sum((r.amount for r in rows), Decimal(0)))
    if amount <= 0 or amount != command.expected_amount:
        raise HTTPException(409, "Available balance changed; refresh before recording settlement")
    settlement = PartnerSettlement(partner_id=command.partner_id, currency=command.currency, amount=amount,
        reference=command.reference, recorded_by=actor.id)
    db.add(settlement); db.flush()
    for row in rows:
        row.settlement_id = settlement.id
    audit(db, tenant_id=None, actor_id=actor.id, action="growth.partner_settled", target_type="partner_settlement",
        target_id=settlement.id, after={"amount": str(amount), "reference": command.reference})
    commerce._commit(db)
    return {"id": settlement.id, "amount": float(amount)}


def gateway():
    from app.services.tuition_collection import _client, _creds
    key, secret = _creds()
    if not key or not secret:
        raise HTTPException(503, "Configure Razorpay in the existing payment settings")
    return _client(), key, secret


def checkout(db, invoice_id, user):
    invoice = db.query(CommercialInvoice).filter_by(id=invoice_id).with_for_update().first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    tenant_access(db, invoice.tenant_id, user, finance=True)
    if invoice.status not in {"issued", "overdue"} or invoice.currency != "INR" or invoice.total_amount <= 0:
        raise HTTPException(409, "Invoice is not payable online")
    client, key, _ = gateway()
    if invoice.gateway_order_id.startswith('pending:'):
        recover_order(db,invoice,client)
    if not invoice.gateway_order_id:
        # Persist intent before the network call. Ambiguous timeouts must not
        # create another payable order on retry.
        invoice.gateway_order_id = f'pending:{invoice.id}'
        commerce._commit(db)
        try:
            order = client.order.create({"amount": int(invoice.total_amount * 100), "currency": invoice.currency,
                "receipt": f"commercial-{invoice.id}", "notes": {"commercial_invoice_id": str(invoice.id), "tenant_id": str(invoice.tenant_id)}})
        except Exception:
            raise HTTPException(502, "Order creation is unconfirmed. Use Check payment to reconcile; a retry will not create another order.") from None
        invoice = db.query(CommercialInvoice).filter_by(id=invoice_id).with_for_update().one()
        invoice.gateway_order_id = order["id"]
        commerce._commit(db)
    return {"key": key, "order_id": invoice.gateway_order_id, "amount_paise": int(invoice.total_amount * 100),
        "currency": invoice.currency, "name": "SashaInfinity", "description": invoice.invoice_number,
        "prefill": {"email": user.user_email, "name": user.display_name or ""}}


def recover_order(db, invoice, client):
    try:
        orders = client.order.all({'receipt':f'commercial-{invoice.id}','count':100}).get('items',[])
    except Exception:
        raise HTTPException(502,'Provider order lookup unavailable; no new order was created') from None
    matches = [o for o in orders if o.get('receipt') == f'commercial-{invoice.id}' and o.get('amount') == int(invoice.total_amount*100)
        and o.get('currency') == invoice.currency and str((o.get('notes') or {}).get('tenant_id')) == str(invoice.tenant_id)]
    if len(matches) != 1:
        raise HTTPException(409,'Order creation remains ambiguous. Reconcile the provider receipt before retrying; no duplicate order was created')
    invoice.gateway_order_id = matches[0]['id']
    commerce._commit(db)


def capture_invoice(db, entity):
    order_id = entity.get('order_id')
    if not order_id:
        return None
    invoice = db.query(CommercialInvoice).filter_by(gateway_order_id=order_id).first()
    if invoice:
        return invoice
    notes = entity.get('notes') or {}
    iid = str(notes.get('commercial_invoice_id') or '')
    if iid.isdigit():
        invoice = db.query(CommercialInvoice).filter_by(id=int(iid),gateway_order_id=f'pending:{iid}').with_for_update().first()
        if invoice and str(notes.get('tenant_id')) == str(invoice.tenant_id) and entity.get('amount') == int(invoice.total_amount*100) and entity.get('currency') == invoice.currency and entity.get('status') == 'captured':
            invoice.gateway_order_id = order_id
            db.flush()
            return invoice
    return None


def capture(db, invoice, entity):
    if (entity.get("status") != "captured" or not entity.get("id") or entity.get("order_id") != invoice.gateway_order_id
        or entity.get("amount") != int(invoice.total_amount * 100) or entity.get("currency") != invoice.currency):
        raise HTTPException(409, "Provider payment does not match the invoice")
    prior = db.query(RevenueLedgerEvent).filter_by(invoice_id=invoice.id, event_type="capture").first()
    if prior and prior.source_event_key != "razorpay:" + entity["id"]:
        raise HTTPException(409, "Invoice already settled with another payment; review excess capture")
    return commerce.record_payment(db, invoice.id, PaymentRecord(source_event_key="razorpay:" + entity["id"],
        payment_reference=entity["id"], occurred_at=datetime.fromtimestamp(entity.get("created_at") or datetime.now(timezone.utc).timestamp(), timezone.utc),
        gateway_fee=Decimal(entity.get("fee") or 0) / 100, reason="Razorpay capture verified against commercial invoice"), invoice.created_by)


def verify(db, invoice_id, command, user):
    invoice = db.get(CommercialInvoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    tenant_access(db, invoice.tenant_id, user, finance=True)
    client, _, secret = gateway()
    expected = hmac.new(secret.encode(), f"{invoice.gateway_order_id}|{command.razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    if invoice.gateway_order_id != command.razorpay_order_id or not hmac.compare_digest(expected, command.razorpay_signature):
        raise HTTPException(400, "Invalid payment signature")
    try:
        entity = client.payment.fetch(command.razorpay_payment_id)
    except Exception:
        raise HTTPException(502, "Could not verify payment; webhook or reconciliation will recover it") from None
    return capture(db, invoice, entity)


def reconcile_invoice(db, invoice_id, user):
    invoice = db.get(CommercialInvoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    tenant_access(db, invoice.tenant_id, user, finance=True)
    if invoice.gateway_order_id and invoice.status in {"issued", "overdue"}:
        client, _, _ = gateway()
        if invoice.gateway_order_id.startswith('pending:'):
            recover_order(db,invoice,client)
        try:
            payments = client.order.payments(invoice.gateway_order_id).get("items", [])
        except Exception:
            raise HTTPException(502, "Payment provider reconciliation unavailable") from None
        for entity in payments:
            if entity.get("status") == "captured":
                capture(db, invoice, entity)
                break
    return commerce._serialize_invoice(invoice)


def webhook_refund(db, entity):
    event = db.query(RevenueLedgerEvent).filter_by(source_event_key="razorpay:" + str(entity.get("payment_id")), event_type="capture").first()
    if not event:
        return False
    if entity.get("status") != "processed" or not entity.get("id") or not isinstance(entity.get("amount"), int) or entity["amount"] <= 0:
        raise HTTPException(409, "Refund is not a confirmed provider refund")
    amount = Decimal(entity["amount"]) / 100
    previous = db.query(RevenueLedgerEvent).filter_by(reverses_event_id=event.id, event_type="refund", status="posted").all()
    remaining_tax = event.tax_amount - sum((p.tax_amount for p in previous), Decimal(0))
    remaining_amount = event.gross_amount - sum((p.gross_amount for p in previous), Decimal(0))
    tax = remaining_tax if amount == remaining_amount else min(remaining_tax, commerce.money(event.tax_amount * amount / event.gross_amount))
    commerce.record_refund(db, event.id, RefundRecord(source_event_key="razorpay:" + entity["id"], refund_reference=entity["id"],
        amount=amount, tax_amount=tax, occurred_at=datetime.now(timezone.utc), reason="Signed Razorpay refund webhook"), event.recorded_by)
    return True


def run_billing(db):
    due = db.query(CommercialContract.id).join(BillingPolicy, BillingPolicy.contract_id == CommercialContract.id).filter(
        BillingPolicy.automation_enabled.is_(True), CommercialContract.status == "active",
        CommercialContract.next_billing_on <= today()).order_by(CommercialContract.next_billing_on).limit(100).all()
    issued = 0
    for (cid,) in due:
        contract = db.query(CommercialContract).filter_by(id=cid).with_for_update().one()
        if contract.status != "active" or not contract.next_billing_on or contract.next_billing_on > today():
            db.commit(); continue
        if contract.ends_on and contract.next_billing_on >= contract.ends_on:
            contract.status = "completed"; db.commit(); continue
        policy = db.get(BillingPolicy, cid)
        issue(db, cid, "cycle:" + contract.next_billing_on.isoformat(), policy.created_by, scheduled=True)
        issued += 1
    db.query(CommercialInvoice).filter(CommercialInvoice.status == "issued", CommercialInvoice.due_on < today()).update({"status": "overdue"})
    db.query(CommercialDelivery).filter(CommercialDelivery.status == "active", CommercialDelivery.valid_until <= today()).update({"status": "expired"})
    db.commit()
    return {"invoices_issued": issued}
