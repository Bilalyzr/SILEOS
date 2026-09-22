"""Read-only campus deployment checks. Never prints credentials or changes data.

Run with the deployed backend virtual environment from the repository root.
Exit 0 means local prerequisites passed, not that a production rollout is certified.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import inspect, text
from app.core.database import engine
from app.core.config import get_settings
from app.services.campus_billing import configured_plans
from app.services.campus_mail import mail_configured
from app.services.campus_whatsapp import configuration_status as whatsapp_status


def main():
    s = get_settings()
    results = []
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            names = set(inspect(conn).get_table_names())
            required = {
                "institutions",
                "institution_members",
                "institution_invites",
                "campus_terms",
                "campus_attendance",
                "campus_assessments",
                "campus_scores",
                "campus_resources",
                "campus_branding",
                "campus_mail_jobs",
                "parent_link_requests",
                "campus_subscriptions",
                "campus_learning_courses",
                "campus_lessons",
                "campus_lesson_progress",
                "campus_onboarding_states",
                "campus_events",
                "campus_announcements",
                "campus_notice_reads",
                "campus_goals",
                "campus_grade_policies",
                "campus_report_comments",
                "campus_whatsapp_contacts",
                "campus_whatsapp_campaigns",
                "campus_whatsapp_messages",
                "campus_whatsapp_webhook_events",
                "whatsapp_contacts",
                "whatsapp_campaigns",
                "whatsapp_messages",
                "whatsapp_status_receipts",
            }
            results.append(
                ("Campus and global communication tables", required <= names)
            )
            versions = (
                set(
                    conn.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalars()
                )
                if "alembic_version" in names
                else set()
            )
            results.append(("Alembic migration 0043", versions == {"0043"}))
    except Exception:
        results.append(("Database connectivity", False))
    results.extend(
        [
            ("PostgreSQL deployment", engine.dialect.name == "postgresql"),
            ("HTTPS frontend origin", s.FRONTEND_URL.startswith("https://")),
            ("SMTP configured", mail_configured()),
            ("HTTPS backend origin", s.BACKEND_URL.startswith("https://")),
            ("WhatsApp Cloud API configured", whatsapp_status()["configured"]),
            (
                "WhatsApp templates allow-listed",
                bool(whatsapp_status()["approved_templates"]),
            ),
            ("Subscription plan configured", any(configured_plans().values())),
            ("Payment webhook secret configured", bool(s.RAZORPAY_WEBHOOK_SECRET)),
            (
                "Payment credentials configured",
                bool(
                    (s.RAZORPAY_KEY or s.RAZORPAY_KEY_ID)
                    and (s.RAZORPAY_SECRET or s.RAZORPAY_KEY_SECRET)
                ),
            ),
        ]
    )
    for label, ok in results:
        print(f'{"PASS" if ok else "NEEDS SETUP"}: {label}')
    print(
        "Also verify backup restore, private-file access, provider test events and mail delivery in staging."
    )
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
