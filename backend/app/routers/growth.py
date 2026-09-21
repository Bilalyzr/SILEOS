"""Revenue operations: platform administration and tenant-scoped checkout."""
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.commercial import CommercialInvoice
from app.models.platform_tenant import PlatformTenant, PlatformTenantMembership
from app.models.growth import GrowthTask, GrowthValidation, GrowthRecommendation
from app.schemas.growth import (PolicyCommand, IssueCommand, DeliveryCommand, SettlementCommand, LeadCreate, LeadUpdate,
    SpendCommand, TouchCommand, ExperimentCommand, StatusCommand, AcceptOffer, VerifyCommand, ValidationCommand)
from app.services.auth_service import AuthService
from app.services import growth_service as svc, growth_billing as billing, commercial_service as commerce
from app.services import growth_fulfillment
from app.schemas.growth import CancellationCommand
from app.schemas.growth import LeadWorkspace

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(AuthService.require_admin)]
Account = Annotated[User, Depends(AuthService.get_current_active_user)]


@router.get("/admin")
def admin_snapshot(db: DB, user: Admin):
    return svc.snapshot(db)


@router.get("/analytics")
def analytics(db: DB, user: Admin, days: int = Query(90, ge=7, le=365), vertical: str | None = Query(None, pattern="^(meiporul|seyappaduporul|utporul)$")):
    return svc.analytics(db, days, vertical)


@router.put("/contracts/{cid}/policy")
def policy(cid: int, command: PolicyCommand, db: DB, user: Admin):
    return billing.set_policy(db, cid, command, user)


@router.post("/contracts/{cid}/issue")
def issue(cid: int, command: IssueCommand, db: DB, user: Admin):
    return billing.issue(db, cid, command.period_key, user.id, milestone_bps=command.milestone_bps)


@router.post("/maintenance")
def maintenance(db: DB, user: Admin):
    svc.log(db, user, "maintenance_requested", "manual")
    return svc.maintenance(db)


@router.post("/deliveries/{did}/complete")
def deliver(did: int, command: DeliveryCommand, db: DB, user: Admin):
    return billing.complete_delivery(db, did, command.evidence, user)


@router.post("/settlements")
def settle(command: SettlementCommand, db: DB, user: Admin):
    return billing.settle(db, command, user)


@router.post("/leads", status_code=201)
def lead(command: LeadCreate, db: DB, user: Account):
    return svc.create_lead(db, command, user)


@router.put("/leads/{lid}")
def update_lead(lid: int, command: LeadUpdate, db: DB, user: Admin):
    return svc.update_lead(db, lid, command, user)


@router.put('/leads/{lid}/workspace')
def lead_workspace(lid: int, command: LeadWorkspace, db: DB, user: Admin):
    from app.models.growth import GrowthLead
    row = db.query(GrowthLead).filter_by(id=lid).with_for_update().first()
    if not row:
        raise HTTPException(404,'Lead not found')
    if row.version != command.version:
        raise HTTPException(409,'Lead changed; refresh before linking a workspace')
    billing.tenant_access(db,command.tenant_id,user,finance=True)
    if row.contract_id and row.tenant_id != command.tenant_id:
        raise HTTPException(409,'Unlink the existing contract before changing this customer workspace')
    row.tenant_id = command.tenant_id
    row.version += 1
    svc.log(db,user,'lead_workspace_linked',row.id,row.tenant_id)
    commerce._commit(db)
    return svc.row_dict(row)


@router.post("/tasks/{tid}/complete")
def complete_task(tid: int, db: DB, user: Admin):
    row = db.query(GrowthTask).filter_by(id=tid).with_for_update().first()
    if not row:
        raise HTTPException(404, "Task not found")
    row.status = "completed"
    svc.log(db, user, "task_completed", tid)
    commerce._commit(db)
    return svc.row_dict(row)


@router.post("/spend")
def spend(command: SpendCommand, db: DB, user: Admin):
    return svc.add_spend(db, command, user)


@router.post("/touches")
def touch(command: TouchCommand, db: DB, user: Account):
    return svc.touch(db, command, user)


@router.post("/experiments")
def experiment(command: ExperimentCommand, db: DB, user: Admin):
    return svc.create_experiment(db, command, user)


@router.post("/experiments/{eid}/status")
def status(eid: int, command: StatusCommand, db: DB, user: Admin):
    return svc.experiment_status(db, eid, command.status, user)


@router.get("/experiments/{eid}/results")
def results(eid: int, db: DB, user: Admin):
    return svc.experiment_results(db, eid)


@router.post("/recommendations/{tenant_id}")
def recommend(tenant_id: int, db: DB, user: Admin):
    return svc.recommend(db, tenant_id, user)


@router.post("/recommendations/{rid}/review")
def review(rid: int, db: DB, user: Admin, decision: str = Query(pattern="^(approved|rejected)$")):
    row = db.query(GrowthRecommendation).filter_by(id=rid).with_for_update().first()
    if not row:
        raise HTTPException(404, "Recommendation not found")
    row.status = decision
    svc.log(db, user, "recommendation_reviewed", rid, row.tenant_id, {"decision": decision})
    commerce._commit(db)
    return svc.row_dict(row)


@router.post('/recommendations/{rid}/publish')
def publish(rid: int, db: DB, user: Admin):
    return svc.publish_recommendation(db, rid, user)


@router.get('/my-offers')
def my_offers(db: DB, user: Account):
    return svc.customer_recommendations(db, user)


@router.post('/recommendations/{rid}/accept/{index}')
def accept_recommendation(rid: int, index: int, db: DB, user: Account):
    return svc.accept_recommendation(db, rid, index, user)


@router.post("/validations")
def validation(command: ValidationCommand, db: DB, user: Admin):
    row = GrowthValidation(**command.model_dump(), recorded_by=user.id)
    db.add(row); db.flush()
    svc.log(db, user, "validation_evidence_recorded", row.id)
    commerce._commit(db)
    return svc.row_dict(row)


@router.get("/offers")
def offers(db: DB):
    return commerce.list_offers(db)


@router.post("/offers/{oid}/quote")
def quote(oid: int, db: DB, user: Account):
    result = svc.quote(db, oid, user)
    commerce._commit(db)
    return result


@router.post("/offers/{oid}/accept")
def accept(oid: int, command: AcceptOffer, db: DB, user: Account):
    return svc.accept_offer(db, oid, command, user)


@router.get("/my-billing")
def my_billing(db: DB, user: Account):
    tenants = db.query(PlatformTenant).join(PlatformTenantMembership).filter(PlatformTenantMembership.user_id == user.id,
        PlatformTenantMembership.status == "active", PlatformTenantMembership.role.in_(["owner", "admin", "finance"]),
        PlatformTenant.status.in_(["active", "trial"])).all()
    ids = [t.id for t in tenants]
    invoices = db.query(CommercialInvoice).filter(CommercialInvoice.tenant_id.in_(ids)).order_by(CommercialInvoice.id.desc()).limit(100)
    from app.models.commercial import CommercialContract
    contracts = db.query(CommercialContract).filter(CommercialContract.tenant_id.in_(ids)).order_by(CommercialContract.id.desc()).limit(100)
    return {"tenants": [{"id": t.id, "name": t.name} for t in tenants], "invoices": [commerce._serialize_invoice(i) for i in invoices],
        "contracts": [commerce._serialize_contract(c) for c in contracts], "deliveries": growth_fulfillment.delivery_list(db, user)}


@router.post("/contracts/{cid}/cancel-renewal")
def cancel_renewal(cid: int, command: CancellationCommand, db: DB, user: Account):
    return growth_fulfillment.cancel_renewal(db, cid, command.reason, user)


@router.post("/invoices/{iid}/checkout")
def checkout(iid: int, db: DB, user: Account):
    return billing.checkout(db, iid, user)


@router.post("/invoices/{iid}/verify")
def verify(iid: int, command: VerifyCommand, db: DB, user: Account):
    return billing.verify(db, iid, command, user)


@router.post("/invoices/{iid}/reconcile")
def reconcile(iid: int, db: DB, user: Account):
    return billing.reconcile_invoice(db, iid, user)


@router.get("/invoices/{iid}/document")
def document(iid: int, db: DB, user: Account):
    invoice = db.get(CommercialInvoice, iid)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    billing.tenant_access(db, invoice.tenant_id, user, finance=True)
    snapshot = billing.invoice_snapshot(db, iid)
    if not snapshot:
        raise HTTPException(409, "This legacy invoice has no reviewed tax snapshot")
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    profile = snapshot["tax_profile"]
    lines = ["SashaInfinity | Tax invoice" if profile["rate_bps"] else "SashaInfinity | Bill of supply",
        invoice.invoice_number, f"Issued: {invoice.issued_at} | Due: {invoice.due_on}",
        f"Supplier: {profile['supplier_name']}", profile["supplier_address"], f"GSTIN: {profile['supplier_gstin'] or 'Not registered'}",
        f"Customer: {profile['customer_name']}", profile["customer_address"], f"Customer GSTIN: {profile['customer_gstin'] or 'Unregistered'}",
        f"Place of supply: {profile['place_of_supply']} | HSN/SAC: {profile['hsn_sac']}",
        f"Service: {snapshot['resource_type']} / {snapshot['resource_reference']}",
        f"Taxable amount: INR {invoice.subtotal} | Rate: {profile['rate_bps']/100}%",
        " | ".join(f"{k.upper()}: INR {v}" for k, v in snapshot["taxes"].items()),
        f"Total: INR {invoice.total_amount} | Status: {invoice.status}",
        f"Reverse charge: {'Yes' if profile['reverse_charge'] else 'No'}", profile.get("exemption_reason", ""),
        "Computer-generated billing document. E-invoice/IRN and authorized-signatory requirements must be validated for the supplier before production use."]
    output = BytesIO(); styles = getSampleStyleSheet()
    story = []
    for index, line in enumerate(lines):
        story.extend([Paragraph(escape(str(line)), styles["Heading1"] if index == 0 else styles["Normal"]), Spacer(1, 10)])
    SimpleDocTemplate(output).build(story)
    return Response(output.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="invoice-{iid}.pdf"'})
