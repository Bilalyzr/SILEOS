import asyncio
import logging
from sqlalchemy import text

from app.core.database import SessionLocal, engine
from app.services.campus_mail import deliver_pending
from app.services.campus_billing import reconcile
from app.services.campus_whatsapp import deliver_pending as deliver_whatsapp_pending
from app.services.tuition_reminders import run_all as run_tuition_reminders

logger = logging.getLogger(__name__)
CAMPUS_ADVISORY_LOCK_KEY = 931843

def tick():
    """Run one campus maintenance pass at most once across web replicas.

    The production image currently starts multiple Uvicorn workers. Each
    process imports this loop, so a Postgres session advisory lock is required
    to keep mail, WhatsApp and billing work from running concurrently. SQLite
    remains single-process in development and tests.
    """

    lock_conn = None
    if engine.dialect.name == "postgresql":
        lock_conn = engine.connect()
        try:
            acquired = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": CAMPUS_ADVISORY_LOCK_KEY},
            ).scalar()
        except Exception:
            lock_conn.close()
            raise
        if not acquired:
            lock_conn.close()
            return False
    try:
        deliver_pending()
        deliver_whatsapp_pending()
        run_tuition_reminders()
        with SessionLocal() as db:
            reconcile(db)
        from app.services.operations_service import heartbeat

        heartbeat("campus_maintenance", "ok")
        return True
    finally:
        if lock_conn is not None:
            try:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": CAMPUS_ADVISORY_LOCK_KEY},
                )
            finally:
                lock_conn.close()


async def campus_loop():
    while True:
        try:
            await asyncio.to_thread(tick)
        except Exception:
            logger.exception("Campus maintenance failed")
            from app.services.operations_service import heartbeat

            heartbeat("campus_maintenance", "error")
        await asyncio.sleep(60)
