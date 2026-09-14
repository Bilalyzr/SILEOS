from pydantic import BaseModel, Field

# Razorpay caps `notes` values at 256 chars, and the bundle_course_ids
# snapshot (order notes at purchase time) overflows around ~85 courses.
# 20 is a comfortable margin under that ceiling and a sane product cap.
MAX_BUNDLE_COURSES = 20


class BundleCourseOut(BaseModel):
    id: int
    title: str
    price: float


class BundleOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    bundle_price: float
    combined_price: float
    courses: list[BundleCourseOut]


class BundleDetailOut(BundleOut):
    owned_course_ids: list[int] = []


class BundleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    description: str = ""
    bundle_price: float = Field(gt=0)
    course_ids: list[int] = Field(min_length=2, max_length=MAX_BUNDLE_COURSES)


class BundleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    bundle_price: float | None = Field(default=None, gt=0)
    course_ids: list[int] | None = Field(default=None, min_length=2, max_length=MAX_BUNDLE_COURSES)
    is_active: bool | None = None


class AdminBundleOut(BundleOut):
    is_active: bool
    sales_count: int
