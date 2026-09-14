"""Sale display rule (Batch 2, item 14): checkout.py:49, course_service.py:207,
courses.py:185 and courses.py:347 must show a course as "on sale" only when
`0 < sale_price < price` — inline placeholder for the pricing authority's
`is_on_sale()` until the sale-price-fix branch merges. The old loose
`sale_price > 0` check would show a sale badge (and imply a discount) even
when sale_price >= list price, which would still charge list price.

Covers all four serializer/display sites:
  - GET /api/v1/checkout/course-info      (checkout.py:49)
  - GET /api/v1/courses/{course_ref}      (course_service.py:207)
  - GET /api/v1/courses/                  (courses.py:185, listing)
  - GET /api/v1/courses/checkout-info     (courses.py:347)
"""
import pytest
from app.models.course import Course
from app.models.user import User


def _make_instructor(db, make_user, email):
    return make_user(role="instructor", email=email)


def _make_course(db, instructor, price, sale_price, published=True):
    c = Course(
        post_author=instructor.id,
        post_title=f"Course @ {price}/{sale_price}",
        course_price_type="paid",
        course_price=price,
        course_sale_price=sale_price,
        post_status="publish" if published else "draft",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


BOUNDARY_CASES = [
    # (price, sale_price, expect_on_sale)
    (100.0, 80.0, True),    # 0 < sale < price -> ON SALE
    (100.0, 100.0, False),  # sale == price -> NOT on sale
    (100.0, 0.0, False),    # sale == 0 -> NOT on sale
    (100.0, None, False),   # sale is None -> NOT on sale
    (100.0, 150.0, False),  # sale > price -> NOT on sale
]


class TestCheckoutCourseInfoSaleRule:
    @pytest.mark.parametrize("price,sale_price,expect_on_sale", BOUNDARY_CASES)
    def test_boundary(self, client, db, make_user, price, sale_price, expect_on_sale):
        instructor = _make_instructor(db, make_user, f"instr_chk_{price}_{sale_price}@example.com")
        course = _make_course(db, instructor, price, sale_price)

        r = client.get(f"/api/v1/checkout/course-info?course_id={course.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        if expect_on_sale:
            assert body["sale_price"] == sale_price
        else:
            assert body["sale_price"] is None


class TestCourseDetailSaleRule:
    @pytest.mark.parametrize("price,sale_price,expect_on_sale", BOUNDARY_CASES)
    def test_boundary(self, client, db, make_user, price, sale_price, expect_on_sale):
        instructor = _make_instructor(db, make_user, f"instr_det_{price}_{sale_price}@example.com")
        course = _make_course(db, instructor, price, sale_price)

        r = client.get(f"/api/v1/courses/{course.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        if expect_on_sale:
            assert body["sale_price"] == sale_price
        else:
            assert body["sale_price"] is None


class TestCourseListingSaleRule:
    @pytest.mark.parametrize("price,sale_price,expect_on_sale", BOUNDARY_CASES)
    def test_boundary(self, client, db, make_user, price, sale_price, expect_on_sale):
        instructor = _make_instructor(db, make_user, f"instr_list_{price}_{sale_price}@example.com")
        course = _make_course(db, instructor, price, sale_price)

        r = client.get("/api/v1/courses/")
        assert r.status_code == 200, r.text
        body = r.json()
        items = body.get("items") or body.get("courses") or body
        match = next((c for c in items if c["id"] == course.id), None)
        assert match is not None, f"course {course.id} not found in listing response: {body}"
        if expect_on_sale:
            assert match["sale_price"] == sale_price
        else:
            assert match["sale_price"] is None


class TestCoursesCheckoutInfoSaleRule:
    @pytest.mark.parametrize("price,sale_price,expect_on_sale", BOUNDARY_CASES)
    def test_boundary(self, client, db, make_user, price, sale_price, expect_on_sale):
        instructor = _make_instructor(db, make_user, f"instr_cci_{price}_{sale_price}@example.com")
        course = _make_course(db, instructor, price, sale_price)

        r = client.get(f"/api/v1/courses/checkout-info?course_id={course.id}")
        assert r.status_code == 200, r.text
        body = r.json()
        if expect_on_sale:
            assert body["sale_price"] == sale_price
        else:
            assert body["sale_price"] is None
