"""Keep recent upstream fixes when packaging the restructured local application."""
from datetime import timedelta
from pathlib import Path
import ast
import pytest
from pydantic import ValidationError
from app.schemas.course import CourseUpdate, CourseCreate
from app.schemas.company_invoice import InvoiceCreate, InvoiceUpdate


@pytest.mark.parametrize("field", ["price", "sale_price"])
@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
def test_course_prices_are_validated_for_create_and_update(field, value):
    with pytest.raises(ValidationError):
        CourseUpdate(**{field: value})
    with pytest.raises(ValidationError):
        CourseCreate(title="Demo", description="Demo", category="science", **{field: value})


def test_invoice_date_input_is_accepted_as_utc():
    row = InvoiceCreate(company_id=1, due_date="2026-09-20", items=[{"description": "Demo", "quantity": 1, "unit_price": 100}])
    assert row.due_date.utcoffset() == timedelta(0)
    assert InvoiceUpdate(due_date="2026-09-20").due_date == row.due_date


@pytest.mark.parametrize("orientation,dimensions", [("portrait", (1080, 1400)), ("landscape", (1400, 1080))])
def test_legacy_certificate_dimensions(db, make_user, orientation, dimensions):
    from app.models.certificate import Certificate
    from app.routers.certificate_designer import _to_out
    from app.schemas.certificate import DesignerTemplateOut
    owner = make_user(role="admin")
    row = Certificate(post_author=owner.id, post_title="Legacy", certificate_orientation=orientation, elements_config=[])
    db.add(row); db.flush()
    row.certificate_width = row.certificate_height = None
    output = DesignerTemplateOut.model_validate(_to_out(row, owner))
    assert (output.certificate_width, output.certificate_height) == dimensions


def test_non_enrolled_progress_has_explicit_empty_state(client, make_user, as_user):
    as_user(make_user(role="student"))
    response = client.get("/api/v1/courses/12345/progress")
    assert response.status_code == 200
    assert response.json()["enrolled"] is False
    assert response.json()["completed_lesson_ids"] == []


def test_company_export_does_not_shadow_its_model(db):
    from app.routers.export_import import get_section_query
    assert get_section_query(db, "companies") == []


def test_revenue_export_defaults_to_captured_payments(db, make_user):
    from app.models.payment import Order, Payment, PaymentStatus
    from app.routers.export_import import get_section_query, serialize_item
    user = make_user()
    order = Order(user_id=user.id, order_key="DEMO-UPSTREAM-REVENUE", total_amount=100)
    db.add(order); db.flush()
    paid = Payment(user_id=user.id, order_id=order.id, payment_method="demo", amount=100, payment_status=PaymentStatus.COMPLETED)
    pending = Payment(user_id=user.id, order_id=order.id, payment_method="demo", amount=100, payment_status=PaymentStatus.PENDING)
    db.add_all([paid, pending]); db.commit()
    rows = get_section_query(db, "revenue")
    assert [r.id for r in rows] == [paid.id]
    assert serialize_item(paid, "revenue", db)["amount_inr"] == "100.00"


def test_ids_does_not_ban_normal_navigation_permission_failures():
    path = Path(__file__).resolve().parents[2] / "scripts/ids_watch.py"
    # Test the pure policy without importing the Linux-only fcntl watcher.
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "auth_failure_kind")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
    policy = namespace["auth_failure_kind"]
    assert policy("/api/v1/admin/operations", "403", "GET") is None
    assert policy("/api/v1/analytics/track", "429", "POST") is None
    assert policy("/api/v1/auth/login", "401", "POST") == "auth"
