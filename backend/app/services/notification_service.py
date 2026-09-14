"""
Notification service — one entry point to create an in-app notification and,
optionally, queue a best-effort email. Email never blocks or breaks the request.
"""
import logging
from app.models.notification import Notification

logger = logging.getLogger(__name__)


async def _send_notification_email(to_email: str, subject: str, body: str):
    """Best-effort email for a notification. Never raises (SMTP may be down)."""
    try:
        from app.utils.email import EmailService
        html = f"<p>{body}</p>" if body else f"<p>{subject}</p>"
        await EmailService().send_email(to_email, subject, html)
    except Exception as exc:  # pragma: no cover - email is best-effort
        logger.warning("notification email failed for %s: %s", to_email, exc)


def create_notification(db, *, user_id, type, title, message="",
                        link=None, related_id=None,
                        send_email=False, background_tasks=None) -> Notification:
    """Insert an in-app notification; optionally queue a best-effort email.

    The in-app row is the source of truth. Email is fire-and-forget on
    `background_tasks` so a dead SMTP never affects the caller.
    """
    n = Notification(
        user_id=user_id, type=type, title=title, message=message,
        link=link, related_id=related_id, is_read=False,
    )
    db.add(n)
    db.commit()
    db.refresh(n)

    if send_email and background_tasks is not None:
        try:
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.user_email:
                background_tasks.add_task(
                    _send_notification_email, user.user_email, title, message
                )
        except Exception as exc:  # pragma: no cover
            logger.warning("could not queue notification email for user %s: %s", user_id, exc)

    return n
