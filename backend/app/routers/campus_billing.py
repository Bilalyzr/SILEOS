from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.campus_operations import CampusSubscription
from app.schemas.campus_operations import Subscribe, ReconcileSubscription
from app.services.auth_service import AuthService
from app.services import institution_service as svc, campus_billing as billing

router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


@router.get("/platform/billing-attempts")
def billing_attempts(db: Session = Depends(get_db), user=Current):
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Platform administrator access required.")
    return [
        {
            "id": r.id,
            "institution_id": r.institution_id,
            "plan": r.plan,
            "status": r.status,
            "subscription_id": r.gateway_subscription_id,
        }
        for r in db.query(CampusSubscription)
        .order_by(CampusSubscription.id.desc())
        .limit(100)
    ]


@router.post("/platform/billing-attempts/{attempt_id}/reconcile")
def reconcile_attempt(
    attempt_id: int,
    data: ReconcileSubscription,
    db: Session = Depends(get_db),
    user=Current,
):
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Platform administrator access required.")
    row = db.get(CampusSubscription, attempt_id)
    if not row:
        raise HTTPException(404, "Checkout attempt not found.")
    from app.models.institution import Institution

    db.query(Institution).filter_by(id=row.institution_id).with_for_update().one()
    db.refresh(row)
    try:
        entity = billing.provider().subscription.fetch(data.subscription_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            502, "Could not verify the provider subscription."
        ) from None
    try:
        billing.validate_identity(row, entity)
    except ValueError as e:
        raise HTTPException(409, str(e)) from None
    row.gateway_subscription_id = entity["id"]
    row.checkout_url = billing.checkout_url(entity.get("short_url"))
    state = entity.get("status")
    if row.status not in billing.TERMINAL:
        if state in billing.TERMINAL:
            row.status = state
        elif row.status in ("creating", "created"):
            row.status = "created" if state == "created" else "authenticated"
    svc.audit(db, row.institution_id, user, "subscription.reconciled", str(row.id))
    svc.save(db)
    return {
        "status": row.status,
        "message": "Provider identity reconciled. Paid entitlement still requires a verified charged event.",
    }


@router.get("/{institution_id}/billing")
def status(institution_id: int, db: Session = Depends(get_db), user=Current):
    svc.scope(db, institution_id, user, svc.MANAGERS)
    rows = (
        db.query(CampusSubscription)
        .filter_by(institution_id=institution_id)
        .order_by(CampusSubscription.id.desc())
        .all()
    )
    return {
        "plans": [p for p, v in billing.configured_plans().items() if v],
        "effective_plan": billing.effective_plan(db, institution_id),
        "subscriptions": [
            {
                "id": r.id,
                "plan": r.plan,
                "status": r.status,
                "paid_through": svc.utc(r.paid_through) if r.paid_through else None,
                "checkout_url": billing.checkout_url(r.checkout_url),
            }
            for r in rows
        ],
    }


@router.get("/{institution_id}/billing/plans/{plan}")
def plan_details(
    institution_id: int, plan: str, db: Session = Depends(get_db), user=Current
):
    svc.scope(db, institution_id, user, svc.MANAGERS)
    plan_id = billing.configured_plans().get(plan)
    if not plan_id:
        raise HTTPException(503, "This institutional plan has not been configured.")
    try:
        row = billing.provider().plan.fetch(plan_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Could not retrieve the current price.") from None
    item = row.get("item", {})
    return {
        "plan": plan,
        "gateway_plan_id": plan_id,
        "name": item.get("name", plan),
        "amount": item.get("amount"),
        "currency": item.get("currency"),
        "period": row.get("period"),
        "interval": row.get("interval"),
        "total_cycles": 12,
    }


@router.post("/{institution_id}/billing/subscribe")
def subscribe(
    institution_id: int, data: Subscribe, db: Session = Depends(get_db), user=Current
):
    svc.verified(user)
    svc.scope(db, institution_id, user, ("owner",), lock=True)
    plan_id = billing.configured_plans().get(data.plan)
    if not plan_id:
        raise HTTPException(
            503, "Configure the institution's Razorpay plan before starting checkout."
        )
    if data.expected_plan_id != plan_id:
        raise HTTPException(
            409, "The plan changed. Review the current price before continuing."
        )
    client = billing.provider()
    existing = (
        db.query(CampusSubscription)
        .filter(
            CampusSubscription.institution_id == institution_id,
            CampusSubscription.status.notin_(billing.TERMINAL),
        )
        .first()
    )
    if existing:
        if existing.status == "created" and existing.plan == data.plan:
            return {"checkout_url": billing.checkout_url(existing.checkout_url)}
        raise HTTPException(
            409,
            "There is an existing subscription or checkout attempt. Check its status before starting another.",
        )
    row = CampusSubscription(
        institution_id=institution_id,
        plan=data.plan,
        gateway_plan_id=plan_id,
        status="creating",
    )
    db.add(row)
    svc.audit(db, institution_id, user, "subscription.checkout_started", data.plan)
    svc.save(db)
    try:
        result = client.subscription.create(
            {
                "plan_id": plan_id,
                "total_count": 12,
                "quantity": 1,
                "customer_notify": False,
                "notes": {
                    "institution_id": str(institution_id),
                    "campus_attempt": str(row.id),
                },
            }
        )
        # A webhook can arrive while the gateway create request is returning.
        # Preserve its paid state instead of overwriting it with "created".
        from app.models.institution import Institution

        db.query(Institution).filter_by(id=institution_id).with_for_update().one()
        db.refresh(row)
        if row.gateway_subscription_id and row.gateway_subscription_id != result["id"]:
            raise ValueError("Checkout identity mismatch")
        row.gateway_subscription_id = result["id"]
        row.checkout_url = billing.checkout_url(result.get("short_url"))
        if row.status == "creating":
            row.status = "created"
        svc.save(db)
        return {"checkout_url": row.checkout_url}
    except Exception:
        # A timeout may hide a successful gateway mutation. Preserve the
        # durable attempt to prevent a second subscription and double billing.
        raise HTTPException(
            502,
            "Checkout creation needs reconciliation. An administrator must check this attempt with the payment provider before retrying.",
        ) from None


@router.post("/{institution_id}/billing/{subscription_id}/cancel")
def cancel(
    institution_id: int,
    subscription_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    svc.scope(db, institution_id, user, ("owner",), lock=True)
    row = (
        db.query(CampusSubscription)
        .filter_by(id=subscription_id, institution_id=institution_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Subscription not found.")
    if row.status in billing.TERMINAL:
        return {"status": row.status}
    if not row.gateway_subscription_id:
        raise HTTPException(409, "Reconcile the checkout attempt first.")
    try:
        response = billing.provider().subscription.cancel(
            row.gateway_subscription_id, {"cancel_at_cycle_end": 1}
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            502,
            "Cancellation could not be confirmed. Refresh the subscription before retrying.",
        ) from None
    row.status = (
        "cancelled" if response.get("status") == "cancelled" else "cancel_scheduled"
    )
    svc.audit(db, institution_id, user, "subscription.cancellation_requested", row.plan)
    svc.save(db)
    return {"status": row.status}


@router.get("/{institution_id}/billing/{subscription_id}/invoices")
def invoices(
    institution_id: int,
    subscription_id: int,
    db: Session = Depends(get_db),
    user=Current,
):
    svc.scope(db, institution_id, user, svc.MANAGERS)
    row = (
        db.query(CampusSubscription)
        .filter_by(id=subscription_id, institution_id=institution_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Subscription not found.")
    if not row.gateway_subscription_id:
        return []
    try:
        items = (
            billing.provider()
            .invoice.all({"subscription_id": row.gateway_subscription_id, "count": 100})
            .get("items", [])
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Invoices could not be loaded.") from None
    return [
        {
            "id": i["id"],
            "amount": i.get("amount"),
            "currency": i.get("currency"),
            "status": i.get("status"),
            "url": billing.checkout_url(i.get("short_url")),
        }
        for i in items
        if i.get("subscription_id") == row.gateway_subscription_id
    ]
