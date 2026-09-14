"""Parent portal: one read with every approved child's campus signals."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import parent_portal as service
from app.services.auth_service import AuthService


router = APIRouter()


@router.get("/campus")
def campus_overview(db: Session = Depends(get_db), user=Depends(AuthService.get_current_active_user)):
    return service.overview(db, user)
