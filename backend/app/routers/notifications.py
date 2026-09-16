from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.notification import Notification

router = APIRouter()


@router.get("/")
async def list_notifications(
    limit: int = Query(30, le=100),
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = (db.query(Notification)
            .filter(Notification.user_id == current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(limit).all())
    unread = (db.query(Notification)
              .filter(Notification.user_id == current_user.id,
                      Notification.is_read == False)  # noqa: E712
              .count())
    return {
        "unread_count": unread,
        "notifications": [
            {
                "id": n.id, "type": n.type, "title": n.title, "message": n.message,
                "link": n.link, "related_id": n.related_id, "is_read": n.is_read,
                "created_at": n.created_at,
            }
            for n in rows
        ],
    }


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"message": "marked read"}


@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).update({Notification.is_read: True})
    db.commit()
    return {"message": "all marked read"}
