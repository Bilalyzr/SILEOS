"""Provider-backed campus subscriptions. Entitlements depend on paid cycles only."""
import os
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import HTTPException
from app.models.campus_operations import CampusSubscription
from app.models.institution import Institution
from app.services.institution_service import utc

TERMINAL = {"cancelled", "completed", "expired"}


def provider():
    from app.routers.memberships import _rzp_client

    return _rzp_client()


def configured_plans():
    return {
        plan: os.environ.get(f"CAMPUS_{plan.upper()}_PLAN_ID", "").strip()
        for plan in ("campus", "enterprise")
    }


def checkout_url(value):
    u = urlparse(value or "")
    return (
        value
        if u.scheme == "https" and u.hostname in ("rzp.io", "razorpay.com", "rzp.in")
        else ""
    )


def effective_plan(db, institution_id):
    now = datetime.now(timezone.utc)
    row = (
        db.query(CampusSubscription)
        .filter(
            CampusSubscription.institution_id == institution_id,
            CampusSubscription.paid_through > now,
        )
        .order_by(CampusSubscription.paid_through.desc())
        .first()
    )
    return row.plan if row else "starter"


def handle_event(db, event):
    entity = (
        (event.payload or {})
        .get("payload", {})
        .get("subscription", {})
        .get("entity", {})
    )
    if not entity.get("id"):
        return False
    row = (
        db.query(CampusSubscription)
        .filter_by(gateway_subscription_id=entity.get("id"))
        .first()
    )
    if not row:
        attempt = (entity.get("notes") or {}).get("campus_attempt")
        if not str(attempt or "").isdigit():
            return False
        row = db.get(CampusSubscription, int(attempt))
        if not row:
            return False
        # A signed webhook can recover a successful creation hidden by an API timeout.
        validate_identity(row, entity)
    db.query(Institution).filter_by(id=row.institution_id).with_for_update().one()
    db.refresh(row)
    if not row.gateway_subscription_id:
        validate_identity(row, entity)
        row.gateway_subscription_id = entity["id"]
        row.checkout_url = checkout_url(entity.get("short_url"))
    if row.gateway_subscription_id != entity.get("id"):
        raise ValueError("Campus subscription identity mismatch")
    if entity.get("plan_id") != row.gateway_plan_id:
        raise ValueError("Campus subscription plan mismatch")
    stamp = int((event.payload or {}).get("created_at") or 0)
    kind = event.event_type
    # Duplicate or delayed charges may extend already-paid time, but never
    # resurrect a terminal subscription or roll the entitlement backwards.
    if kind == "subscription.charged":
        payment = (
            (event.payload or {})
            .get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        end = entity.get("current_end")
        if payment.get("status") != "captured" or not payment.get("id") or not end:
            raise ValueError(
                "Campus charge needs a captured payment and billing period"
            )
        through = datetime.fromtimestamp(int(end), timezone.utc)
        if not row.paid_through or through > utc(row.paid_through):
            row.paid_through = through
    if stamp >= row.last_event_at and row.status not in TERMINAL:
        statuses = {
            "subscription.charged": "active",
            "subscription.activated": "authenticated",
            "subscription.cancelled": "cancelled",
            "subscription.completed": "completed",
            "subscription.halted": "halted",
            "subscription.pending": "pending",
        }
        # Activation is mandate authorization, not proof of a paid cycle.
        if kind != "subscription.activated" or row.status != "active":
            row.status = statuses.get(kind, row.status)
        row.last_event_at = stamp
    db.flush()
    inst = db.get(Institution, row.institution_id)
    inst.plan = effective_plan(db, inst.id)
    return True


def validate_identity(row, entity):
    notes = entity.get("notes") or {}
    if (
        str(notes.get("institution_id")) != str(row.institution_id)
        or str(notes.get("campus_attempt")) != str(row.id)
        or entity.get("plan_id") != row.gateway_plan_id
        or (
            row.gateway_subscription_id
            and row.gateway_subscription_id != entity.get("id")
        )
    ):
        raise ValueError(
            "The provider subscription does not match this campus checkout attempt."
        )


def reconcile(db):
    for inst in db.query(Institution).filter(Institution.plan != "starter"):
        inst.plan = effective_plan(db, inst.id)
    db.commit()
