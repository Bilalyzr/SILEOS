from datetime import datetime, timezone
from decimal import Decimal

from app.main import app
from app.models.enrollment import Enrollment
from app.models.page_view import PageView
from app.models.payment import Order, OrderStatus
from app.services.auth_service import AuthService


def test_overview_groups_daily_metrics_on_sqlite(
    client, db, make_user, student_user, course
):
    assert db.get_bind().dialect.name == "sqlite"

    superadmin = make_user(role="superadmin")
    app.dependency_overrides[AuthService.require_superadmin] = lambda: superadmin

    observed_at = datetime.now(timezone.utc).replace(microsecond=0)
    day = observed_at.date().isoformat()
    db.add_all(
        [
            Order(
                user_id=student_user.id,
                order_key="overview-sqlite-order",
                order_status=OrderStatus.COMPLETED,
                total_amount=Decimal("125.50"),
                date_created=observed_at,
            ),
            Enrollment(
                user_id=student_user.id,
                course_id=course.id,
                enrollment_date=observed_at,
            ),
            PageView(
                path="/courses",
                ip_hash="overview-sqlite-visitor",
                created_at=observed_at,
            ),
        ]
    )
    db.commit()

    response = client.get("/api/v1/superadmin/overview?days=30")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["revenue_trend"] == [{"day": day, "revenue": 125.5, "orders": 1}]
    assert payload["activity_trend"] == [
        {
            "day": day,
            "revenue": 125.5,
            "orders": 1,
            "enrollments": 1,
            "active_users": 1,
        }
    ]
