"""Live, source-scoped access: refunds and expiry revoke only the purchase they own."""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.models.commercial import CommercialContract, CommercialInvoice
from app.models.growth import CommercialDelivery, BillingOccurrence, BillingPolicy
from app.models.platform_tenant import PlatformTenant, PlatformTenantMembership
from app.services import growth_billing as billing, commercial_service as commerce
from app.services.platform_tenant_service import audit


def active_deliveries(db, tenant_id):
    return db.query(CommercialDelivery).join(CommercialInvoice, CommercialInvoice.id == CommercialDelivery.invoice_id).join(
        PlatformTenant, PlatformTenant.id == CommercialDelivery.tenant_id).filter(
        CommercialDelivery.tenant_id == tenant_id, PlatformTenant.status.in_(['active', 'trial']),
        CommercialDelivery.status.in_(['active', 'completed']), CommercialInvoice.status == 'paid',
        (CommercialDelivery.valid_until.is_(None)) | (CommercialDelivery.valid_until > billing.today()))


def feature_access(db, tenant_id, vertical, feature_key):
    for delivery in active_deliveries(db, tenant_id):
        snapshot = billing.invoice_snapshot(db, delivery.invoice_id) or {}
        if any(g.get('vertical') == vertical and g.get('feature_key') == feature_key for g in snapshot.get('entitlement_grants', [])):
            return True
    return False


def asset_access(db, user_id, model_id):
    tenant_ids = db.query(PlatformTenantMembership.tenant_id).filter_by(user_id=user_id, status='active')
    return db.query(CommercialDelivery.id).join(CommercialInvoice, CommercialInvoice.id == CommercialDelivery.invoice_id).join(
        PlatformTenant, PlatformTenant.id == CommercialDelivery.tenant_id).filter(
        CommercialDelivery.tenant_id.in_(tenant_ids), PlatformTenant.status.in_(['active', 'trial']),
        CommercialDelivery.resource_type == 'asset_license', CommercialDelivery.resource_reference == str(model_id),
        CommercialDelivery.status == 'active', CommercialInvoice.status == 'paid',
        (CommercialDelivery.valid_until.is_(None)) | (CommercialDelivery.valid_until > billing.today())).first() is not None


def institution_plan(db, tenant_id):
    if not tenant_id:
        return 'starter'
    plans = {r.resource_reference for r in active_deliveries(db, tenant_id).filter(CommercialDelivery.resource_type == 'institution_saas')}
    return 'enterprise' if 'enterprise' in plans else 'campus' if 'campus' in plans else 'starter'


def cancel_renewal(db, contract_id, reason, user):
    row = db.query(CommercialContract).filter_by(id=contract_id).with_for_update().first()
    if not row:
        raise HTTPException(404, 'Agreement not found')
    billing.tenant_access(db, row.tenant_id, user, finance=True)
    if not row.billing_interval:
        raise HTTPException(409, 'This is not a recurring agreement; contact support for a service cancellation')
    if row.status == 'cancelled':
        return commerce._serialize_contract(row)
    row.status = 'cancelled'
    row.next_billing_on = None
    policy = db.get(BillingPolicy, row.id)
    if policy:
        policy.automation_enabled = False
    row.terms = {**(row.terms or {}), 'renewal_cancelled_at': datetime.now(timezone.utc).isoformat(), 'cancellation_reason': reason}
    audit(db, tenant_id=row.tenant_id, actor_id=user.id, action='growth.renewal_cancelled', target_type='commercial_contract', target_id=row.id, reason=reason)
    commerce._commit(db)
    # Existing invoices remain obligations; paid access lasts through its purchased period.
    return commerce._serialize_contract(row)


def delivery_list(db, user):
    ids = db.query(PlatformTenantMembership.tenant_id).filter_by(user_id=user.id, status='active')
    rows = db.query(CommercialDelivery).filter(CommercialDelivery.tenant_id.in_(ids)).order_by(CommercialDelivery.id.desc()).limit(100)
    result = []
    for row in rows:
        active = active_deliveries(db, row.tenant_id).filter(CommercialDelivery.id == row.id).first() is not None
        result.append({'id':row.id, 'tenant_id':row.tenant_id, 'invoice_id':row.invoice_id, 'resource_type':row.resource_type,
            'resource_reference':row.resource_reference, 'status':row.status if active or row.status != 'active' else 'inactive',
            'access_active':active, 'valid_until':row.valid_until, 'evidence':row.evidence,
            'asset_url':f'/api/v1/three-d/models/{row.resource_reference}/file' if active and row.resource_type == 'asset_license' else None})
    return result
