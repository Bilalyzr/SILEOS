from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class PlanOut(BaseModel):
    id: int
    name: str
    description: str
    all_access: bool
    period: str
    interval: int
    price: float
    covered_courses: int


class SubscribeRequest(BaseModel):
    plan_id: int
    coupon_code: Optional[str] = None   # R7: coupon with a Razorpay Offer attached


class SubscribeResponse(BaseModel):
    subscription_id: str
    razorpay_key: str


class MembershipOut(BaseModel):
    plan_id: int
    plan_name: str
    status: str
    current_period_end: datetime | None
    grace_until: datetime | None
    cancel_at_period_end: bool


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    all_access: bool = False
    course_ids: list[int] = []
    period: str = Field(pattern=r"^(daily|weekly|monthly|yearly)$")
    interval: int = Field(default=1, ge=1, le=12)
    price: float = Field(gt=0)
    grace_days: int = Field(default=7, ge=0, le=90)


# Price and period are intentionally NOT updatable — Razorpay plans are
# immutable, so pricing changes mean creating a NEW tier (POST) and
# deactivating the old one (PATCH is_active=false).
class PlanUpdate(BaseModel):
    description: str | None = None
    is_active: bool | None = None
    course_ids: list[int] | None = None


class AdminPlanOut(PlanOut):
    grace_days: int
    razorpay_plan_id: str
    is_active: bool
    course_ids: list[int] = []


class AdminMembershipOut(BaseModel):
    id: int
    user_id: int
    user_email: str
    plan_name: str
    status: str
    current_period_end: datetime | None
