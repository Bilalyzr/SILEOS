"""
Coupon schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class CouponCourseRestriction(BaseModel):
    """Schema for course restriction"""
    course_id: int

class CouponCreate(BaseModel):
    """Schema for creating a coupon"""
    code: str = Field(..., min_length=3, max_length=50, description="Unique coupon code")
    description: Optional[str] = ""
    discount_type: str = Field(..., description="'percentage' or 'fixed'")
    discount_value: float = Field(..., gt=0, description="Discount value (percentage 0-100 or fixed amount)")
    applicability: str = Field(default="all_courses", description="'all_courses' or 'specific_courses'")
    course_ids: Optional[List[int]] = Field(default=[], description="List of course IDs if applicability is 'specific_courses'")
    usage_limit: Optional[int] = Field(default=None, ge=1, description="Total usage limit, NULL for unlimited")
    per_user_limit: int = Field(default=1, ge=1, description="How many times one user can use it")
    minimum_purchase_amount: float = Field(default=0, ge=0, description="Minimum purchase amount required")
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    cohort_id: Optional[int] = Field(None, description="Cohort ID for SPOC referral tracking")

    @validator('cohort_id')
    def validate_cohort_exists(cls, v):
        # Skip if None
        if v is None:
            return v
        # Import here to avoid circular dependency
        # Actual cohort existence will be validated in router
        return v

    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        if values.get('discount_type') == 'percentage' and (v <= 0 or v > 100):
            raise ValueError('Percentage discount must be between 0 and 100')
        return v

    @validator('code')
    def validate_code(cls, v):
        # Convert to uppercase and remove spaces
        return v.upper().replace(' ', '')

    @validator('applicability')
    def validate_applicability(cls, v):
        if v not in ['all_courses', 'specific_courses']:
            raise ValueError("Applicability must be 'all_courses' or 'specific_courses'")
        return v

    @validator('discount_type')
    def validate_discount_type(cls, v):
        if v not in ['percentage', 'fixed']:
            raise ValueError("Discount type must be 'percentage' or 'fixed'")
        return v

class CouponUpdate(BaseModel):
    """Schema for updating a coupon"""
    description: Optional[str] = None
    discount_type: Optional[str] = Field(None, description="'percentage' or 'fixed'")
    discount_value: Optional[float] = Field(None, gt=0)
    applicability: Optional[str] = None
    course_ids: Optional[List[int]] = None
    usage_limit: Optional[int] = Field(None, ge=1)
    per_user_limit: Optional[int] = Field(None, ge=1)
    minimum_purchase_amount: Optional[float] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None
    cohort_id: Optional[int] = None

    @validator('discount_type')
    def validate_discount_type(cls, v):
        # Optional on update: only cross-check when the payload carries one.
        if v is not None and v not in ['percentage', 'fixed']:
            raise ValueError("Discount type must be 'percentage' or 'fixed'")
        return v

    @validator('discount_value')
    def validate_discount_value(cls, v, values):
        # Cross-checkable when discount_type rides along in the same
        # payload. discount_value ALONE cannot know the stored type at the
        # schema layer — the PUT /coupons/{id} router cross-checks that
        # case against the STORED coupon.discount_type (422 on violation).
        if (
            v is not None
            and values.get('discount_type') == 'percentage'
            and (v <= 0 or v > 100)
        ):
            raise ValueError('Percentage discount must be between 0 and 100')
        return v

class CouponResponse(BaseModel):
    """Schema for coupon response"""
    id: int
    code: str
    description: str
    discount_type: str
    discount_value: float
    applicability: str
    usage_limit: Optional[int]
    usage_count: int
    per_user_limit: int
    minimum_purchase_amount: float
    valid_from: datetime
    valid_until: Optional[datetime]
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    course_ids: List[int] = []
    cohort_id: Optional[int] = None

    # Legacy rows written by bulk seeds could carry NULL; one NULL used to
    # fail validation for the whole list response. Coerce instead.
    @field_validator('usage_count', mode='before')
    @classmethod
    def _usage_count_none_to_zero(cls, v):
        return 0 if v is None else v

    class Config:
        from_attributes = True

class CouponListResponse(BaseModel):
    """Schema for coupon list item"""
    id: int
    code: str
    description: str
    discount_type: str
    discount_value: float
    applicability: str
    usage_count: int

    @field_validator('usage_count', mode='before')
    @classmethod
    def _usage_count_none_to_zero(cls, v):
        return 0 if v is None else v

    usage_limit: Optional[int]
    is_active: bool
    valid_until: Optional[datetime]
    created_at: datetime

class CouponValidationRequest(BaseModel):
    """Schema for validating a coupon"""
    code: str
    course_ids: List[int]
    total_amount: float

class CouponValidationResponse(BaseModel):
    """Schema for coupon validation response"""
    valid: bool
    message: str
    discount_amount: float = 0
    final_amount: float = 0
    coupon_id: Optional[int] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None

class ApplyCouponRequest(BaseModel):
    """Schema for applying a coupon"""
    code: str
    course_ids: List[int]

class PaginatedCouponsResponse(BaseModel):
    """Schema for paginated coupons response"""
    coupons: List[CouponListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
