"""xAPI statement emitter (blueprint §3.5 event spine, xAPI-lite).

Call `emit_statement` AFTER the caller's own commit, best-effort: a failed
analytics write must never fail the learner action (same doctrine as the
gamification `award()` hook). Statements land in `xapi_statements` where
/at-risk and /mastery analytics read them.
"""
import logging

from app.core.database import SessionLocal
from app.models.sileos_pack import XapiStatement

logger = logging.getLogger(__name__)

BASE_REF = "https://sashainfinity.com/lms"


def build_ref(object_type: str, object_id) -> str:
    return f"{BASE_REF}/{object_type}/{object_id}"


def emit_statement(
    actor_user_id: int,
    verb: str,
    object_type: str,
    object_id,
    result: dict | None = None,
    context: dict | None = None,
) -> None:
    """Fire-and-forget statement write in its own short-lived session."""
    try:
        db = SessionLocal()
        try:
            db.add(XapiStatement(
                actor_user_id=actor_user_id,
                verb=verb,
                object_type=object_type,
                object_id=str(object_id),
                object_ref=build_ref(object_type, object_id),
                result=result or {},
                context=context or {},
            ))
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001 — analytics must never break the action
        logger.warning("xapi emit failed (verb=%s object=%s/%s): %s",
                       verb, object_type, object_id, exc)
