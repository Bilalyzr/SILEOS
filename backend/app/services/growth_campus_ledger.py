"""Adapt verified campus charges to the shared ledger, once per provider payment."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import func
from app.models.commercial import RevenueLedgerEvent
from app.models.institution import Institution
from app.models.campus_operations import CampusSubscription
from app.models.platform_tenant import PlatformTenant


def record_charge(db, subscription, payment, through):
    # Older imported events may not contain monetary evidence. Never invent it.
    amount = payment.get('amount')
    currency = payment.get('currency')
    institution = db.get(Institution, subscription.institution_id)
    if not isinstance(amount, int) or amount <= 0 or not currency or not institution or not institution.tenant_id:
        return None
    tenant = db.get(PlatformTenant, institution.tenant_id)
    if not tenant or not tenant.created_by:
        return None
    key = 'razorpay:' + payment['id']
    existing = db.query(RevenueLedgerEvent).filter_by(source_event_key=key).first()
    if existing:
        if existing.source_type != 'campus_subscription' or existing.source_id != str(subscription.id):
            raise ValueError('Campus payment belongs to another ledger source')
        refunded = db.query(func.coalesce(func.sum(RevenueLedgerEvent.gross_amount),0)).filter_by(
            reverses_event_id=existing.id,event_type='refund',status='posted').scalar()
        return refunded < existing.gross_amount
    gross = Decimal(amount)/100
    fee = Decimal(payment.get('fee') or 0)/100
    db.add(RevenueLedgerEvent(tenant_id=institution.tenant_id,business_vertical='seyappaduporul',revenue_stream='institution_operations',
        event_type='capture',status='posted',source_type='campus_subscription',source_id=str(subscription.id),source_event_key=key,
        currency=str(currency).upper(),gross_amount=gross,tax_amount=0,gateway_fee=fee,partner_share=0,net_amount=gross-fee,
        occurred_at=datetime.fromtimestamp(payment.get('created_at') or datetime.now(timezone.utc).timestamp(),timezone.utc),
        metadata_json={'payment_reference':payment['id'],'paid_through':through.isoformat(),'tax_classification':'unverified_provider_charge'},
        recorded_by=tenant.created_by))
    db.flush()
    return True


def recompute_paid_through(db, capture):
    subscription = db.query(CampusSubscription).filter_by(id=int(capture.source_id)).with_for_update().first()
    if not subscription:
        return
    remaining = []
    events = db.query(RevenueLedgerEvent).filter_by(source_type='campus_subscription',source_id=capture.source_id,event_type='capture',status='posted')
    for event in events:
        refunded = db.query(func.coalesce(func.sum(RevenueLedgerEvent.gross_amount),0)).filter_by(reverses_event_id=event.id,event_type='refund',status='posted').scalar()
        if refunded < event.gross_amount and event.metadata_json.get('paid_through'):
            remaining.append(datetime.fromisoformat(event.metadata_json['paid_through']))
    subscription.paid_through = max(remaining) if remaining else None
    db.flush()
    from app.services.campus_billing import effective_plan
    institution = db.get(Institution, subscription.institution_id)
    if institution:
        institution.plan = effective_plan(db,institution.id)
