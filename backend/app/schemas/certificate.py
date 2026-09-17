"""
Certificate Schemas - Pydantic models for certificate endpoints
"""

from pydantic import BaseModel, validator, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class CertificateResponse(BaseModel):
    id: int
    course_id: int
    course_title: str
    student_name: str
    instructor_name: str
    completion_date: datetime
    certificate_url: str
    verification_code: str
    issued_at: datetime
    # Issue 4: public verification/share URL keyed by the certificate's
    # unique secure ID + hash. Empty for legacy rows that predate secure IDs.
    public_url: Optional[str] = None
    secure_certificate_id: Optional[str] = None


class CertificateTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    template_data: Dict[str, Any]

    @validator('name')
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError('Template name must be at least 3 characters')
        return v

    @validator('template_data')
    def validate_template_data(cls, v):
        # template_data should contain 'content' field (HTML/template content)
        # Other optional fields: background, elements, dimensions for advanced builder
        if not isinstance(v, dict):
            raise ValueError('Template data must be a dictionary')
        # Allow empty dict for backwards compatibility, but if 'content' exists it must be string
        if 'content' in v and not isinstance(v.get('content'), str):
            raise ValueError('Template content must be a string')
        return v


class CertificateTemplateResponse(BaseModel):
    id: int
    name: str
    description: str
    template_data: Dict[str, Any]
    is_default: bool
    created_by: int
    created_at: datetime


# Certificate Template Management Schemas

class TemplateElementType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    SIGNATURE = "signature"
    LOGO = "logo"
    DATE = "date"
    COURSE_NAME = "course_name"
    STUDENT_NAME = "student_name"
    # Task 6 (certificate designer unification) additions — typed tokens +
    # QR/shape elements the elements_config -> HTML renderer understands
    # (app/services/certificate_html_renderer.py).
    COMPLETION_DATE = "completion_date"
    CERTIFICATE_ID = "certificate_id"
    INSTRUCTOR_NAME = "instructor_name"
    QR_CODE = "qr_code"
    SIGNATURE_IMAGE = "signature_image"
    RECT = "rect"
    LINE = "line"


class TemplateElement(BaseModel):
    id: str
    type: TemplateElementType
    x: int
    y: int
    width: int
    height: int
    content: Optional[str] = None
    font_size: Optional[int] = 16
    font_family: Optional[str] = "Arial"
    font_color: Optional[str] = "#000000"
    font_weight: Optional[str] = "normal"
    text_align: Optional[str] = "left"
    background_color: Optional[str] = None
    border: Optional[str] = None
    z_index: int = 0
    image_url: Optional[str] = None
    rotation: Optional[float] = 0


class TemplateDimensions(BaseModel):
    width: int = 1123  # A4 landscape in pixels at 96 DPI
    height: int = 794


class TemplateBackground(BaseModel):
    type: str = "color"  # color, image, gradient
    value: str = "#ffffff"
    image_url: Optional[str] = None


class CertificateTemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field("", max_length=500)
    template_type: str = Field("builder", pattern="^(upload|builder)$")
    background: TemplateBackground
    dimensions: TemplateDimensions
    elements: List[TemplateElement] = []
    orientation: str = Field("landscape", pattern="^(landscape|portrait)$")
    is_default: bool = False


class CertificateTemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    background: Optional[TemplateBackground] = None
    dimensions: Optional[TemplateDimensions] = None
    elements: Optional[List[TemplateElement]] = None
    orientation: Optional[str] = Field(None, pattern="^(landscape|portrait)$")
    is_default: Optional[bool] = None


class UploadedTemplateCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field("", max_length=500)
    file_url: str
    file_type: str = Field("image", pattern="^(image|pdf)$")
    orientation: str = Field("landscape", pattern="^(landscape|portrait)$")


class CertificateTemplateListItem(BaseModel):
    id: int
    name: str
    description: str
    template_type: str
    orientation: str
    preview_url: Optional[str] = None
    is_default: bool
    created_by: int
    created_at: datetime
    usage_count: int = 0


class CertificateTemplateDetail(BaseModel):
    id: int
    name: str
    description: str
    template_type: str
    orientation: str
    background: Dict[str, Any]
    dimensions: Dict[str, int]
    elements: List[Dict[str, Any]]
    preview_url: Optional[str] = None
    is_default: bool
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Instructor certificate designer (Task 6, spec section C item 3)
# ---------------------------------------------------------------------------

DESIGNER_ELEMENT_TYPES = {
    "student_name", "course_name", "completion_date", "certificate_id",
    "instructor_name", "qr_code", "signature_image", "text", "image",
    "rect", "line",
}

DESIGNER_MAX_ELEMENTS = 100


class DesignerTemplateCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field("", max_length=500)
    orientation: str = Field("landscape", pattern="^(landscape|portrait)$")
    certificate_width: int = Field(1400, ge=200, le=6000)
    certificate_height: int = Field(1080, ge=200, le=6000)
    background_color: str = Field("#ffffff", max_length=7)
    background_image: Optional[str] = Field("", max_length=500)
    elements_config: List[Dict[str, Any]] = Field(default_factory=list)


class DesignerTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    orientation: Optional[str] = Field(None, pattern="^(landscape|portrait)$")
    certificate_width: Optional[int] = Field(None, ge=200, le=6000)
    certificate_height: Optional[int] = Field(None, ge=200, le=6000)
    background_color: Optional[str] = Field(None, max_length=7)
    background_image: Optional[str] = Field(None, max_length=500)
    elements_config: Optional[List[Dict[str, Any]]] = None
    is_global: Optional[bool] = None


class DesignerTemplateOut(BaseModel):
    id: int
    name: str
    description: str
    orientation: str
    certificate_width: int
    certificate_height: int
    background_color: str
    background_image: str
    elements_config: List[Dict[str, Any]]
    is_global: bool
    is_own: bool
    post_author: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Task 8 fix round (D-8): a real Chrome-rendered PNG URL when
    # seed_designer_templates.py (or any future thumbnail render) produced
    # one on disk; None otherwise — the frontend gallery falls back to its
    # CSS-swatch placeholder.
    thumbnail: Optional[str] = None


class DesignerPreviewRequest(BaseModel):
    values: Optional[Dict[str, str]] = None