"""Fee collection API: cash verification, cash desk, receipts and invoices as
PDF, and Razorpay online orders. Mount at ``/api/v1/institutions``."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campus_operations import CampusBranding
from app.schemas.tuition import (
    InvoiceCreate,
    OnlineOrderCreate,
    OnlineVerify,
    PaymentVerify,
    TuitionPaymentOut,
)
from app.services.auth_service import AuthService
from app.services import tuition_collection as service
from app.services.campus_report_pdf import build_fee_invoice_pdf, build_fee_receipt_pdf


router = APIRouter()
CurrentUser = Depends(AuthService.get_current_active_user)


def _pdf(content: bytes, filename: str):
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{service._safe_filename(filename)}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ------------------------------------------------------------ verification


@router.post("/{institution_id}/fees/payments/{payment_id}/verify", response_model=TuitionPaymentOut)
def verify_payment(
    institution_id: int,
    payment_id: int,
    data: PaymentVerify,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.verify_payment(db, institution_id, payment_id, user, data.note)


@router.get("/{institution_id}/fees/cash")
def cash_desk(
    institution_id: int,
    day: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.cash_desk(db, institution_id, user, day)


@router.get("/{institution_id}/fees/cash/csv")
def cash_desk_csv(
    institution_id: int,
    day: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    filename, text = service.cash_desk_csv(db, institution_id, user, day)
    return Response(
        text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


# --------------------------------------------------------------- documents


@router.get("/{institution_id}/fees/receipts/{receipt_id}/pdf")
def receipt_pdf(
    institution_id: int,
    receipt_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    document = service.receipt_document(db, institution_id, receipt_id, user)
    branding = db.get(CampusBranding, institution_id)
    return _pdf(build_fee_receipt_pdf(document, branding), f"receipt-{document['receipt_number']}.pdf")


@router.post(
    "/{institution_id}/fees/assignments/{assignment_id}/invoices",
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    institution_id: int,
    assignment_id: int,
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.create_invoice(db, institution_id, assignment_id, user, data.installment_id)


@router.get("/{institution_id}/fees/assignments/{assignment_id}/invoices")
def list_invoices(
    institution_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.list_invoices(db, institution_id, assignment_id, user)


@router.get("/{institution_id}/fees/invoices/{invoice_id}")
def invoice_detail(
    institution_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.invoice_detail(db, institution_id, invoice_id, user)


@router.get("/{institution_id}/fees/invoices/{invoice_id}/pdf")
def invoice_pdf(
    institution_id: int,
    invoice_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    document = service.invoice_detail(db, institution_id, invoice_id, user)
    branding = db.get(CampusBranding, institution_id)
    return _pdf(build_fee_invoice_pdf(document, branding), f"invoice-{document['invoice_number']}.pdf")


# ----------------------------------------------------------- online orders


@router.get("/{institution_id}/fees/online/status")
def online_status(institution_id: int, user=CurrentUser):
    return {"ready": service.online_ready()}


@router.post(
    "/{institution_id}/fees/assignments/{assignment_id}/online-orders",
    status_code=status.HTTP_201_CREATED,
)
def create_online_order(
    institution_id: int,
    assignment_id: int,
    data: OnlineOrderCreate,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.create_online_order(
        db, institution_id, assignment_id, user, data.installment_id, data.amount
    )


@router.post("/{institution_id}/fees/online-orders/{order_id}/verify")
def verify_online_order(
    institution_id: int,
    order_id: int,
    data: OnlineVerify,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.verify_online_order(db, institution_id, order_id, user, data)


@router.post("/{institution_id}/fees/online-orders/{order_id}/reconcile")
def reconcile_online_order(
    institution_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    user=CurrentUser,
):
    return service.reconcile_online_order(db, institution_id, order_id, user)
