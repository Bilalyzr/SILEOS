"""Role-aware Today dashboard endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import campus_action_center as service
from app.services.auth_service import AuthService


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


class ActionCreate(BaseModel):
    kind: str = Field(default="task", min_length=2, max_length=30)
    title: str = Field(min_length=2, max_length=180)
    detail: str = Field(default="", max_length=3000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    assigned_member_id: int | None = None
    due_at: datetime | None = None
    href: str = Field(default="", max_length=500)


class ActionUpdate(BaseModel):
    status: Literal["open", "done", "snoozed"]


@router.get("/{institution_id}/today")
def today(institution_id: int, db: Session = Depends(get_db), user=Current):
    return service.today(db, institution_id, user)


@router.post("/{institution_id}/today/actions", status_code=status.HTTP_201_CREATED)
def create_action(
    institution_id: int,
    data: ActionCreate,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.create_action(db, institution_id, user, data)


@router.patch("/{institution_id}/today/actions/{action_id}")
def update_action(
    institution_id: int,
    action_id: str,
    data: ActionUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.update_action(db, institution_id, action_id, user, data.status)

