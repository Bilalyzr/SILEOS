"""
Coupon Management Router - Admin coupon CRUD and validation
"""
import re
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import get_db
from app.models.user import User
from app.models.coupon import Coupon, CouponCourseRestriction, CouponUsage, DiscountType, CouponApplicability
from app.models.course import Course
from app.models.cohort import Cohort
from app.services.auth_service import AuthService
from app.schemas.coupon import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponListResponse,
    CouponValidationRequest,
    CouponValidationResponse,
    ApplyCouponRequest,
    PaginatedCouponsResponse
)

router = APIRouter()

@router.post("/", response_model=CouponResponse)
async def create_coupon(
    coupon_data: CouponCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Create a new coupon (Admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create coupons"
        )

    # Normalize code (upper + strip) so Batch 1's ilike lookups never see drift
    normalized_code = (coupon_data.code or "").strip().upper()
    if not normalized_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon code is required",
        )

    # Check if coupon code already exists (case-insensitive)
    existing_coupon = db.query(Coupon).filter(Coupon.code.ilike(normalized_code)).first()
    if existing_coupon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coupon code '{normalized_code}' already exists"
        )

    # Validate course IDs if applicability is specific_courses
    if coupon_data.applicability == "specific_courses":
        if not coupon_data.course_ids or len(coupon_data.course_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course IDs are required for specific_courses applicability"
            )

        # Check if all courses exist
        courses = db.query(Course).filter(Course.id.in_(coupon_data.course_ids)).all()
        if len(courses) != len(coupon_data.course_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some course IDs are invalid"
            )

    # Validate cohort_id if provided
    if coupon_data.cohort_id:
        cohort = db.query(Cohort).filter(Cohort.id == coupon_data.cohort_id).first()
        if not cohort:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cohort with ID {coupon_data.cohort_id} not found"
            )

    # Create coupon
    new_coupon = Coupon(
        code=normalized_code,
        description=coupon_data.description,
        discount_type=coupon_data.discount_type,
        discount_value=Decimal(str(coupon_data.discount_value)),
        applicability=coupon_data.applicability,
        usage_limit=coupon_data.usage_limit,
        per_user_limit=coupon_data.per_user_limit,
        minimum_purchase_amount=Decimal(str(coupon_data.minimum_purchase_amount)),
        valid_from=coupon_data.valid_from or datetime.now(timezone.utc),
        valid_until=coupon_data.valid_until,
        is_active=coupon_data.is_active,
        cohort_id=coupon_data.cohort_id,
        created_by=current_user.id
    )

    try:
        db.add(new_coupon)
        db.flush()

        # Add course restrictions if applicability is specific_courses
        if coupon_data.applicability == "specific_courses" and coupon_data.course_ids:
            for course_id in coupon_data.course_ids:
                restriction = CouponCourseRestriction(
                    coupon_id=new_coupon.id,
                    course_id=course_id
                )
                db.add(restriction)

        db.commit()
        db.refresh(new_coupon)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create coupon: {e}")

    # Get course IDs for response
    course_ids = []
    if new_coupon.applicability == 'specific_courses':
        course_ids = [r.course_id for r in new_coupon.course_restrictions]

    return CouponResponse(
        id=new_coupon.id,
        code=new_coupon.code,
        description=new_coupon.description,
        discount_type=new_coupon.discount_type,
        discount_value=float(new_coupon.discount_value),
        applicability=new_coupon.applicability,
        usage_limit=new_coupon.usage_limit,
        usage_count=new_coupon.usage_count,
        per_user_limit=new_coupon.per_user_limit,
        minimum_purchase_amount=float(new_coupon.minimum_purchase_amount),
        valid_from=new_coupon.valid_from,
        valid_until=new_coupon.valid_until,
        is_active=new_coupon.is_active,
        created_by=new_coupon.created_by,
        created_at=new_coupon.created_at,
        updated_at=new_coupon.updated_at,
        course_ids=course_ids,
        cohort_id=new_coupon.cohort_id
    )

@router.get("/", response_model=PaginatedCouponsResponse)
async def get_coupons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get list of coupons with pagination (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view coupons"
        )

    query = db.query(Coupon)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Coupon.code.ilike(f"%{search}%"),
                Coupon.description.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(Coupon.is_active == is_active)

    # Get total count
    total = query.count()

    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    # Get coupons
    coupons = query.order_by(Coupon.created_at.desc()).offset(skip).limit(page_size).all()

    coupons_data = [
        CouponListResponse(
            id=coupon.id,
            code=coupon.code,
            description=coupon.description,
            discount_type=coupon.discount_type,
            discount_value=float(coupon.discount_value),
            applicability=coupon.applicability,
            usage_count=coupon.usage_count,
            usage_limit=coupon.usage_limit,
            is_active=coupon.is_active,
            valid_until=coupon.valid_until,
            created_at=coupon.created_at
        )
        for coupon in coupons
    ]

    return PaginatedCouponsResponse(
        coupons=coupons_data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Get coupon details (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view coupons"
        )

    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Get course IDs for response
    course_ids = []
    if coupon.applicability == 'specific_courses':
        course_ids = [r.course_id for r in coupon.course_restrictions]

    return CouponResponse(
        id=coupon.id,
        code=coupon.code,
        description=coupon.description,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value),
        applicability=coupon.applicability,
        usage_limit=coupon.usage_limit,
        usage_count=coupon.usage_count,
        per_user_limit=coupon.per_user_limit,
        minimum_purchase_amount=float(coupon.minimum_purchase_amount),
        valid_from=coupon.valid_from,
        valid_until=coupon.valid_until,
        is_active=coupon.is_active,
        created_by=coupon.created_by,
        created_at=coupon.created_at,
        updated_at=coupon.updated_at,
        course_ids=course_ids,
        cohort_id=coupon.cohort_id
    )

@router.put("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int,
    coupon_data: CouponUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Update coupon (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update coupons"
        )

    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    # Stored-type cross-check: when discount_value arrives WITHOUT a
    # discount_type, the schema validator cannot range-check it (it only
    # sees the payload). Validate against the EFFECTIVE type — the new one
    # if the payload changes it, otherwise the STORED one — so a
    # percentage coupon can never silently absorb a value like 150.
    effective_discount_type = coupon_data.discount_type or coupon.discount_type
    if (
        coupon_data.discount_value is not None
        and effective_discount_type == 'percentage'
        and (coupon_data.discount_value <= 0 or coupon_data.discount_value > 100)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Percentage discount must be between 0 and 100'
        )

    # Update fields
    if coupon_data.description is not None:
        coupon.description = coupon_data.description
    if coupon_data.discount_type is not None:
        coupon.discount_type = coupon_data.discount_type
    if coupon_data.discount_value is not None:
        coupon.discount_value = Decimal(str(coupon_data.discount_value))
    if coupon_data.applicability is not None:
        coupon.applicability = coupon_data.applicability
    if coupon_data.usage_limit is not None:
        coupon.usage_limit = coupon_data.usage_limit
    if coupon_data.per_user_limit is not None:
        coupon.per_user_limit = coupon_data.per_user_limit
    if coupon_data.minimum_purchase_amount is not None:
        coupon.minimum_purchase_amount = Decimal(str(coupon_data.minimum_purchase_amount))
    if coupon_data.valid_from is not None:
        coupon.valid_from = coupon_data.valid_from
    if coupon_data.valid_until is not None:
        coupon.valid_until = coupon_data.valid_until
    if coupon_data.is_active is not None:
        coupon.is_active = coupon_data.is_active
    if coupon_data.cohort_id is not None:
        # Validate cohort exists
        if coupon_data.cohort_id:
            cohort = db.query(Cohort).filter(Cohort.id == coupon_data.cohort_id).first()
            if not cohort:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cohort with ID {coupon_data.cohort_id} not found"
                )
        coupon.cohort_id = coupon_data.cohort_id

    try:
        # Update course restrictions if provided
        if coupon_data.course_ids is not None:
            # Delete existing restrictions
            db.query(CouponCourseRestriction).filter(
                CouponCourseRestriction.coupon_id == coupon_id
            ).delete()

            # Add new restrictions
            for course_id in coupon_data.course_ids:
                restriction = CouponCourseRestriction(
                    coupon_id=coupon_id,
                    course_id=course_id
                )
                db.add(restriction)

        db.commit()
        db.refresh(coupon)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update coupon: {e}")

    # Get course IDs for response
    course_ids = []
    if coupon.applicability == 'specific_courses':
        course_ids = [r.course_id for r in coupon.course_restrictions]

    return CouponResponse(
        id=coupon.id,
        code=coupon.code,
        description=coupon.description,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value),
        applicability=coupon.applicability,
        usage_limit=coupon.usage_limit,
        usage_count=coupon.usage_count,
        per_user_limit=coupon.per_user_limit,
        minimum_purchase_amount=float(coupon.minimum_purchase_amount),
        valid_from=coupon.valid_from,
        valid_until=coupon.valid_until,
        is_active=coupon.is_active,
        created_by=coupon.created_by,
        created_at=coupon.created_at,
        updated_at=coupon.updated_at,
        course_ids=course_ids,
        cohort_id=coupon.cohort_id
    )

@router.delete("/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Delete coupon (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete coupons"
        )

    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found"
        )

    try:
        db.delete(coupon)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to delete coupon: {e}")

    return {"message": "Coupon deleted successfully"}

@router.post("/validate", response_model=CouponValidationResponse)
async def validate_coupon(
    validation_data: CouponValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Validate a coupon OR voucher code for given courses and amount.

    Issue 7: the Apply button used to reject voucher codes (INTR-...)
    because this endpoint only looked in the coupons table. Vouchers are
    now resolved first — a valid, unredeemed voucher owned by the current
    user gives a 100% discount — then we fall through to the coupon path.
    """
    from app.models.internship import InternshipVoucher

    raw_code = (validation_data.code or "").strip()

    # 0) Voucher lookup (case-insensitive). Vouchers imply a 100% discount
    # the coupon table can't express, and their code-space (INTR-...) is
    # distinct, so they take priority.
    voucher = (
        db.query(InternshipVoucher)
        .filter(InternshipVoucher.code.ilike(raw_code))
        .first()
    )
    if voucher:
        if voucher.buyer_user_id != current_user.id:
            return CouponValidationResponse(
                valid=False, message="This voucher belongs to a different account"
            )
        if voucher.status != "issued":
            return CouponValidationResponse(
                valid=False, message="This voucher has already been redeemed"
            )
        total = float(validation_data.total_amount or 0)
        return CouponValidationResponse(
            valid=True,
            message="Voucher applied successfully — full discount",
            discount_amount=total,
            final_amount=0,
            discount_type="fixed",
            discount_value=total,
        )

    # Find coupon by code
    coupon = db.query(Coupon).filter(
        Coupon.code == validation_data.code.upper()
    ).first()

    if not coupon:
        return CouponValidationResponse(
            valid=False,
            message="Invalid coupon code"
        )

    # Delegate the remaining checks and the discount math to
    # validate_and_compute — the SAME code path the apply / checkout flows
    # use — so validate can never promise a discount the purchase flow
    # would reject (or compute a different amount). This also fixes
    # per_user_limit: the service treats NULL as 1 instead of crashing on
    # `count >= None`.
    from app.services.coupon_service import CouponError, validate_and_compute

    try:
        result = validate_and_compute(
            db,
            code=coupon.code,
            user_id=current_user.id,
            course_ids=validation_data.course_ids or [],
            total_amount=float(validation_data.total_amount or 0),
        )
    except CouponError as exc:
        return CouponValidationResponse(valid=False, message=exc.message)

    return CouponValidationResponse(
        valid=True,
        message="Coupon applied successfully",
        discount_amount=float(result.discount_amount),
        final_amount=float(result.final_amount),
        coupon_id=coupon.id,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value)
    )


class _OfferIn(BaseModel):
    razorpay_offer_id: Optional[str] = None


@router.patch("/{coupon_id}/membership-offer")
async def set_membership_offer(coupon_id: int, body: _OfferIn, db: Session = Depends(get_db),
                               current_user: User = Depends(AuthService.require_admin)):
    """R7: link a Razorpay Offer (offer_…) so the coupon works on membership
    subscriptions. Blank removes the link. The offer itself is created in the
    Razorpay dashboard (owner-owned); we only pass its id at subscribe time."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    oid = (body.razorpay_offer_id or "").strip()
    if oid and not re.match(r"^offer_[A-Za-z0-9]{6,}$", oid):
        raise HTTPException(status_code=422, detail="Razorpay offer ids look like offer_XXXXXXXXXXXXXX")
    coupon.razorpay_offer_id = oid or None
    db.commit()
    return {"id": coupon.id, "code": coupon.code, "razorpay_offer_id": coupon.razorpay_offer_id}
