"""
Wall of Fame router - editable staff showcase.

Public endpoint:
  GET /                 -> published members, ordered by sort_order

Admin CRUD (gated by AuthService.require_admin -> covers admin + superadmin):
  GET /admin            -> all members (incl. unpublished)
  POST /                -> create
  PUT /{id}             -> update
  DELETE /{id}          -> delete
  PUT /reorder          -> bulk-update sort_order

Mirrors the blog.py pattern: inline Pydantic schemas, per-endpoint auth.
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.hall_of_fame import HallOfFameMember
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["HallOfFame"])


# ---------------------------------------------------------------------------
# Pydantic schemas (inline, like blog.py)
# ---------------------------------------------------------------------------
class MemberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=200)
    photo: Optional[str] = Field(default=None, max_length=500)
    tenure: str = Field(default="", max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    linkedin: Optional[str] = Field(default=None, max_length=500)
    blurb: Optional[str] = None
    highlight: Optional[str] = Field(default=None, max_length=100)
    sort_order: int = 0
    is_published: bool = True


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, max_length=200)
    company: Optional[str] = Field(default=None, max_length=200)
    photo: Optional[str] = Field(default=None, max_length=500)
    tenure: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    linkedin: Optional[str] = Field(default=None, max_length=500)
    blurb: Optional[str] = None
    highlight: Optional[str] = Field(default=None, max_length=100)
    sort_order: Optional[int] = None
    is_published: Optional[bool] = None


class MemberResponse(MemberBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderRequest(BaseModel):
    items: List[ReorderItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _member_to_dict(m: HallOfFameMember) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "role": m.role or "",
        "company": m.company or "",
        "photo": m.photo,
        "tenure": m.tenure or "",
        "location": m.location,
        "linkedin": m.linkedin,
        "blurb": m.blurb,
        "highlight": m.highlight,
        "sort_order": m.sort_order,
        "is_published": m.is_published,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Public endpoint
# ---------------------------------------------------------------------------
@router.get("")
@router.get("/")
async def list_published_members(db: Session = Depends(get_db)):
    """Public: published Wall of Fame members, ordered by sort_order then name."""
    members = (
        db.query(HallOfFameMember)
        .filter(HallOfFameMember.is_published.is_(True))
        .order_by(HallOfFameMember.sort_order.asc(), HallOfFameMember.name.asc())
        .all()
    )
    return [_member_to_dict(m) for m in members]


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------
@router.get("/admin")
async def list_all_members(
    current_user=Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin: all members (including unpublished), ordered by sort_order."""
    members = (
        db.query(HallOfFameMember)
        .order_by(HallOfFameMember.sort_order.asc(), HallOfFameMember.name.asc())
        .all()
    )
    return [_member_to_dict(m) for m in members]


@router.post("")
@router.post("/")
async def create_member(
    payload: MemberCreate,
    current_user=Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin: create a new Wall of Fame member."""
    member = HallOfFameMember(
        name=payload.name,
        role=payload.role,
        company=payload.company,
        photo=payload.photo,
        tenure=payload.tenure,
        location=payload.location,
        linkedin=payload.linkedin,
        blurb=payload.blurb,
        highlight=payload.highlight,
        sort_order=payload.sort_order,
        is_published=payload.is_published,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    logger.info("Wall of Fame member created (id=%s, name=%s) by user_id=%s", member.id, member.name, current_user.id)
    return _member_to_dict(member)


@router.put("/reorder")
async def reorder_members(
    payload: ReorderRequest,
    current_user=Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin: bulk-update sort_order for multiple members at once.
    Accepts { items: [{ id, sort_order }, ...] }.

    IMPORTANT: this route MUST be declared before PUT /{member_id}, otherwise
    FastAPI matches '/reorder' against the parametrised member_id route and
    tries (and fails) to parse 'reorder' as an integer -> 422.
    """
    ids = [item.id for item in payload.items]
    if not ids:
        return {"ok": True, "updated": 0}

    members = db.query(HallOfFameMember).filter(HallOfFameMember.id.in_(ids)).all()
    order_map = {item.id: item.sort_order for item in payload.items}
    updated = 0
    for m in members:
        if m.id in order_map:
            m.sort_order = order_map[m.id]
            updated += 1
    db.commit()
    logger.info("Wall of Fame reordered (%d members) by user_id=%s", updated, current_user.id)
    return {"ok": True, "updated": updated}


@router.put("/{member_id}")
async def update_member(
    member_id: int,
    payload: MemberUpdate,
    current_user=Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin: update an existing member. Only set fields are updated."""
    member = db.query(HallOfFameMember).filter(HallOfFameMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wall of Fame member not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)

    db.commit()
    db.refresh(member)
    logger.info("Wall of Fame member updated (id=%s) by user_id=%s", member_id, current_user.id)
    return _member_to_dict(member)


@router.delete("/{member_id}")
async def delete_member(
    member_id: int,
    current_user=Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    """Admin: delete a member."""
    member = db.query(HallOfFameMember).filter(HallOfFameMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wall of Fame member not found")

    db.delete(member)
    db.commit()
    logger.info("Wall of Fame member deleted (id=%s, name=%s) by user_id=%s", member_id, member.name, current_user.id)
    return {"ok": True, "id": member_id}
