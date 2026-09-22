"""Central admin APIs for offers, contracts, invoices, and revenue events."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.commercial import (
    ContractCreate,
    InvoiceCreate,
    OfferCreate,
    PaymentRecord,
    RefundRecord,
)
from app.services import commercial_service as service
from app.services.auth_service import AuthService


router = APIRouter()


@router.get("/offers")
def offers(
    vertical: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: User = Depends(AuthService.require_admin),
):
    return service.list_offers(db, vertical=vertical, active_only=active_only)


@router.post("/offers", status_code=201)
def create_offer(
    command: OfferCreate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.create_offer(db, command, user.id)


@router.post("/contracts", status_code=201)
def create_contract(
    command: ContractCreate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.create_contract(db, command, user.id)


@router.post("/invoices", status_code=201)
def create_invoice(
    command: InvoiceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.create_invoice(db, command, user.id)


@router.post("/invoices/{invoice_id}/payments", status_code=201)
def record_payment(
    invoice_id: int,
    command: PaymentRecord,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.record_payment(db, invoice_id, command, user.id)


@router.post("/ledger/{event_id}/refunds", status_code=201)
def record_refund(
    event_id: int,
    command: RefundRecord,
    db: Session = Depends(get_db),
    user: User = Depends(AuthService.require_admin),
):
    return service.record_refund(db, event_id, command, user.id)


@router.get("/ledger")
def ledger(
    start: datetime = Query(
        default_factory=lambda: datetime.now(timezone.utc) - timedelta(days=30)
    ),
    end: datetime = Query(default_factory=lambda: datetime.now(timezone.utc)),
    vertical: str | None = None,
    tenant_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _: User = Depends(AuthService.require_admin),
):
    return service.list_ledger(
        db, start=start, end=end, vertical=vertical, tenant_id=tenant_id
    )
