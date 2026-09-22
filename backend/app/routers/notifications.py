from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.communication_automation import CommunicationTopicPreference
from app.models.user import User
from app.models.notification import Notification

router = APIRouter()

TOPICS = {
    "business_offers": {
        "label": "Business offers",
        "description": "Reviewed SashaInfinity service offers. Optional and off by default.",
        "in_app_enabled": False, "email_enabled": False,
        "push_enabled": False, "whatsapp_enabled": False,
    },
    "learning_interventions": {
        "label": "Learning interventions",
        "description": "Instructor support notes, review tasks and understanding checks.",
        "in_app_enabled": True,
        "email_enabled": True,
        "push_enabled": False,
        "whatsapp_enabled": False,
    },
    "course_activity": {
        "label": "Course activity",
        "description": "Course updates, assignment activity and learning reminders.",
        "in_app_enabled": True,
        "email_enabled": False,
        "push_enabled": False,
        "whatsapp_enabled": False,
    },
    "campus_updates": {
        "label": "Campus and account updates",
        "description": "Operational updates from SashaInfinity workspaces.",
        "in_app_enabled": True,
        "email_enabled": False,
        "push_enabled": False,
        "whatsapp_enabled": False,
    },
}


class TopicPreferencePatch(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    whatsapp_enabled: bool | None = None


def _topic_dict(row: CommunicationTopicPreference | None, topic: str):
    defaults = TOPICS[topic]
    return {
        "topic": topic,
        "label": defaults["label"],
        "description": defaults["description"],
        "in_app_enabled": row.in_app_enabled if row else defaults["in_app_enabled"],
        "email_enabled": row.email_enabled if row else defaults["email_enabled"],
        "push_enabled": row.push_enabled if row else defaults["push_enabled"],
        "whatsapp_enabled": row.whatsapp_enabled if row else defaults["whatsapp_enabled"],
    }


@router.get("/preferences")
async def list_preferences(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = {
        row.topic: row
        for row in db.query(CommunicationTopicPreference)
        .filter(CommunicationTopicPreference.user_id == current_user.id)
        .all()
    }
    return {"topics": [_topic_dict(rows.get(topic), topic) for topic in TOPICS]}


@router.patch("/preferences/{topic}")
async def update_preference(
    topic: str,
    body: TopicPreferencePatch,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    if topic not in TOPICS:
        raise HTTPException(status_code=404, detail="Preference topic not found")
    row = db.query(CommunicationTopicPreference).filter_by(
        user_id=current_user.id, topic=topic
    ).first()
    if not row:
        defaults = TOPICS[topic]
        row = CommunicationTopicPreference(
            user_id=current_user.id,
            topic=topic,
            in_app_enabled=defaults["in_app_enabled"],
            email_enabled=defaults["email_enabled"],
            push_enabled=defaults["push_enabled"],
            whatsapp_enabled=defaults["whatsapp_enabled"],
        )
        db.add(row)
    for field in (
        "in_app_enabled",
        "email_enabled",
        "push_enabled",
        "whatsapp_enabled",
    ):
        value = getattr(body, field)
        if value is not None:
            setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _topic_dict(row, topic)


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
