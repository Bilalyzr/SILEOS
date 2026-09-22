"""Unified read model for Sasha Infinity's three business pillars.

The existing product writes money through several proven flows (course orders,
tuition, digital resources, assessment papers, and internship vouchers).  This
service adapts those records into one reporting contract without creating a
second ledger or changing fulfillment.  New revenue models should add one
adapter here and keep their own operational source of truth.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.core.business_verticals import (
    REVENUE_STREAMS,
    VERTICAL_KEYS,
    VERTICALS,
    normalize_vertical,
)
from app.models.assignment import Assignment
from app.models.certificate import IssuedCertificate
from app.models.commercial import RevenueLedgerEvent
from app.models.content_library import VirtualLabCatalog
from app.models.course import Course
from app.models.ebook import Ebook
from app.models.enrollment import Enrollment
from app.models.exam_paper import ExamPaper
from app.models.geogebra import GeoGebraApplet
from app.models.institution import Institution
from app.models.internship import Internship, InternshipVoucher
from app.models.live_class import LiveClass
from app.models.payment import Order, OrderItem, Payment, PaymentStatus
from app.models.quiz import Quiz
from app.models.three_d import ThreeDModel
from app.models.tuition import TuitionPayment


ZERO = Decimal("0")
BUSINESS_TIMEZONE = ZoneInfo("Asia/Kolkata")

STREAM_LABELS = {
    "immersive_courses": "Immersive course sales",
    "asset_licensing": "3D asset licensing",
    "experience_subscription": "Experience subscriptions",
    "lab_deployment": "Lab deployment",
    "amc_support": "AMC and field support",
    "tuition_fees": "Tutoring and school fees",
    "institution_operations": "Institution operations",
    "digital_resources": "Books and notes",
    "paper_generation": "Assessment papers",
    "franchise_services": "Franchise services",
    "skill_courses": "Skill course sales",
    "assessment_services": "Assessment services",
    "credentials": "Premium credentials",
    "creator_commerce": "Creator commerce",
    "career_services": "Career and internship services",
    "unallocated": "Needs classification",
}

EXPECTED_STREAMS = REVENUE_STREAMS


VERTICAL_DB_VALUES = {
    "meiporul": ("meiporul", "ma1"),
    "seyappaduporul": ("seyappaduporul", "seyappadu-porul", "seyappadu porul", "seyappadu_porul", "ma2"),
    "utporul": ("utporul", "upporul", "ma3"),
}


def _stream_for(vertical: Optional[str]) -> str:
    return {
        "meiporul": "immersive_courses",
        "seyappaduporul": "tuition_fees",
        "utporul": "skill_courses",
    }.get(vertical, "unallocated")


def _course_vertical(db, course_id: Optional[int]) -> Optional[str]:
    if not course_id:
        return None
    course = db.get(Course, course_id)
    return normalize_vertical(course.course_type) if course else None


def business_today():
    return datetime.now(timezone.utc).astimezone(BUSINESS_TIMEZONE).date()


def reporting_window(start, end) -> tuple[datetime, datetime]:
    """Interpret report dates as India business days, then query in UTC."""
    local_after = datetime.combine(start, datetime.min.time(), tzinfo=BUSINESS_TIMEZONE)
    local_before = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=BUSINESS_TIMEZONE)
    return local_after.astimezone(timezone.utc), local_before.astimezone(timezone.utc)


def _order_parts(db, order: Order) -> list[tuple[Optional[str], str, Decimal]]:
    """Return weighted (vertical, stream, amount) parts for one order."""
    parts: list[tuple[Optional[str], str, Decimal]] = []
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in items:
        weight = Decimal(item.total or item.subtotal or 0)
        snapshot = item.product_data if isinstance(item.product_data, dict) else {}
        explicit_vertical = normalize_vertical(snapshot.get("business_vertical"))
        explicit_stream = str(snapshot.get("revenue_stream") or "").strip()
        if explicit_vertical and explicit_stream in EXPECTED_STREAMS[explicit_vertical]:
            parts.append((explicit_vertical, explicit_stream, weight))
            continue
        if item.course_id:
            vertical = _course_vertical(db, item.course_id)
            parts.append((vertical, _stream_for(vertical), weight))
            continue
        if item.ebook_id:
            # Digital books, notes, and guides are a Seyappaduporul product
            # even when they support a course delivered by another pillar.
            parts.append(("seyappaduporul", "digital_resources", weight))

    if parts:
        return parts

    # Some established checkouts create a source row and a payment/order but
    # no generic OrderItem.  Resolve those sources before reporting unknown.
    paper = db.query(ExamPaper).filter(ExamPaper.order_id == order.id).first()
    if paper:
        return [("seyappaduporul", "paper_generation", Decimal(order.total_amount or 1))]

    if order.ebook_id:
        return [("seyappaduporul", "digital_resources", Decimal(order.total_amount or 1))]

    if order.bundle_id:
        from app.models.bundle import BundleCourse

        course_ids = [row[0] for row in db.query(BundleCourse.course_id).filter(BundleCourse.bundle_id == order.bundle_id).all()]
        verticals = [_course_vertical(db, course_id) for course_id in course_ids]
        if verticals:
            return [(vertical, _stream_for(vertical), Decimal("1")) for vertical in verticals]

    return [(None, "unallocated", Decimal(order.total_amount or 1))]


def _allocated_parts(db, payment: Payment) -> list[tuple[Optional[str], str, Decimal]]:
    order = db.get(Order, payment.order_id)
    if not order:
        return [(None, "unallocated", Decimal(payment.amount or 0))]
    parts = _order_parts(db, order)
    positive = [(vertical, stream, max(ZERO, weight)) for vertical, stream, weight in parts]
    total_weight = sum((weight for _, _, weight in positive), ZERO)
    amount = Decimal(payment.amount or 0)
    if total_weight <= ZERO:
        equal = amount / Decimal(len(positive) or 1)
        return [(vertical, stream, equal) for vertical, stream, _ in positive]
    allocated: list[tuple[Optional[str], str, Decimal]] = []
    running = ZERO
    for index, (vertical, stream, weight) in enumerate(positive):
        share = amount - running if index == len(positive) - 1 else amount * weight / total_weight
        running += share
        allocated.append((vertical, stream, share))
    return allocated


def _empty_currency() -> dict[str, Decimal]:
    return {"captured": ZERO, "refunded": ZERO}


def _currency_rows(bucket: dict[str, dict[str, Decimal]]) -> list[dict]:
    return [
        {
            "currency": currency,
            "captured": float(values["captured"]),
            "refunded": float(values["refunded"]),
            "net_cash": float(values["captured"] - values["refunded"]),
        }
        for currency, values in sorted(bucket.items())
    ]


def _inventory(db, vertical: str) -> list[dict]:
    course_filter = func.lower(func.trim(Course.course_type)).in_(VERTICAL_DB_VALUES[vertical])
    courses = db.query(Course).filter(course_filter)
    shared = [
        {"key": "courses", "label": "Courses", "value": courses.count()},
        {"key": "published_courses", "label": "Published courses", "value": courses.filter(Course.post_status.in_(("publish", "published"))).count()},
        {
            "key": "learners",
            "label": "Learners reached",
            "value": db.query(func.count(func.distinct(Enrollment.user_id))).join(Course, Course.id == Enrollment.course_id).filter(course_filter).scalar() or 0,
        },
    ]
    if vertical == "meiporul":
        return shared + [
            {"key": "three_d_models", "label": "3D models", "value": db.query(ThreeDModel).count()},
            {"key": "published_labs", "label": "Published labs", "value": db.query(VirtualLabCatalog).filter(VirtualLabCatalog.is_published.is_(True)).count()},
            {"key": "geogebra_applets", "label": "GeoGebra interactives", "value": db.query(GeoGebraApplet).count()},
        ]
    if vertical == "seyappaduporul":
        return shared + [
            {"key": "institutions", "label": "Institutions", "value": db.query(Institution).count()},
            {"key": "live_classes", "label": "Live classes", "value": db.query(LiveClass).count()},
            {"key": "ebooks", "label": "Books and notes", "value": db.query(Ebook).count()},
            {"key": "exam_papers", "label": "Generated papers", "value": db.query(ExamPaper).count()},
        ]
    return shared + [
        {"key": "quizzes", "label": "Quizzes", "value": db.query(Quiz).join(Course, Course.id == Quiz.post_parent).filter(course_filter).count()},
        {"key": "assignments", "label": "Assignments", "value": db.query(Assignment).join(Course, Course.id == Assignment.course_id).filter(course_filter).count()},
        {"key": "certificates", "label": "Certificates issued", "value": db.query(IssuedCertificate).join(Course, Course.id == IssuedCertificate.course_id).filter(course_filter).count()},
        {"key": "internships", "label": "Internships", "value": db.query(Internship).count()},
    ]


def _unallocated_course_count(db) -> int:
    known = tuple(value for values in VERTICAL_DB_VALUES.values() for value in values)
    normalized = func.lower(func.trim(func.coalesce(Course.course_type, "")))
    return db.query(Course).filter(~normalized.in_(known)).count()


def _financial_snapshot(db, start, end):
    after, before = reporting_window(start, end)
    totals = {key: defaultdict(_empty_currency) for key in VERTICAL_KEYS}
    streams = {key: {stream: defaultdict(_empty_currency) for stream in EXPECTED_STREAMS[key]} for key in VERTICAL_KEYS}
    unallocated = defaultdict(_empty_currency)
    unallocated_payments: set[int] = set()

    def record(vertical: Optional[str], stream: str, currency: str, amount: Decimal, kind: str, source_id: Optional[int] = None) -> None:
        currency = (currency or "INR").upper()
        canonical = normalize_vertical(vertical)
        if canonical is None:
            unallocated[currency][kind] += amount
            if source_id is not None:
                unallocated_payments.add(source_id)
            return
        totals[canonical][currency][kind] += amount
        stream_bucket = streams[canonical].setdefault(stream, defaultdict(_empty_currency))
        stream_bucket[currency][kind] += amount

    captured = db.query(Payment).filter(
        Payment.payment_status.in_((PaymentStatus.COMPLETED, PaymentStatus.REFUNDED)),
        Payment.payment_date >= after,
        Payment.payment_date < before,
    ).all()
    for payment in captured:
        for vertical, stream, amount in _allocated_parts(db, payment):
            record(vertical, stream, payment.currency, amount, "captured", payment.id)

    refunded = db.query(Payment).filter(
        Payment.payment_status == PaymentStatus.REFUNDED,
        Payment.refund_processed_at >= after,
        Payment.refund_processed_at < before,
    ).all()
    for payment in refunded:
        for vertical, stream, amount in _allocated_parts(db, payment):
            record(vertical, stream, payment.currency, amount, "refunded", payment.id)

    tuition_rows = db.query(TuitionPayment).filter(
        TuitionPayment.status == "posted",
        TuitionPayment.paid_at >= after,
        TuitionPayment.paid_at < before,
    ).all()
    for row in tuition_rows:
        record("seyappaduporul", "tuition_fees", row.currency, Decimal(row.amount or 0), "captured")

    voucher_rows = db.query(InternshipVoucher).filter(
        InternshipVoucher.created_at >= after,
        InternshipVoucher.created_at < before,
        InternshipVoucher.amount_paid > 0,
    ).all()
    for row in voucher_rows:
        record("utporul", "career_services", "INR", Decimal(row.amount_paid or 0), "captured")

    ledger_rows = db.query(RevenueLedgerEvent).filter(
        RevenueLedgerEvent.status == "posted",
        RevenueLedgerEvent.event_type.in_(("capture", "refund")),
        RevenueLedgerEvent.occurred_at >= after,
        RevenueLedgerEvent.occurred_at < before,
    ).all()
    for row in ledger_rows:
        record(
            row.business_vertical,
            row.revenue_stream,
            row.currency,
            Decimal(row.gross_amount or 0),
            "refunded" if row.event_type == "refund" else "captured",
        )

    return totals, streams, unallocated, unallocated_payments


def consolidated_cash(db, start, end) -> list[dict]:
    """One currency total used by both admin revenue surfaces."""
    totals, _, unallocated, _ = _financial_snapshot(db, start, end)
    combined = defaultdict(_empty_currency)
    for vertical in VERTICAL_KEYS:
        for currency, values in totals[vertical].items():
            combined[currency]["captured"] += values["captured"]
            combined[currency]["refunded"] += values["refunded"]
    for currency, values in unallocated.items():
        combined[currency]["captured"] += values["captured"]
        combined[currency]["refunded"] += values["refunded"]
    return _currency_rows(combined)


def cash_timeseries(db, start, end, currency="INR") -> list[dict]:
    """Daily net cash by pillar using the same rules as ``portfolio``.

    The chart is deliberately derived from settlement events: captures land
    on payment/posted dates and refunds land on processing dates. This keeps
    every admin revenue surface reconcilable with the consolidated totals.
    """
    after, before = reporting_window(start, end)
    wanted_currency = currency.upper()
    buckets = {
        start + timedelta(days=offset): {key: ZERO for key in (*VERTICAL_KEYS, "unallocated")}
        for offset in range((end - start).days + 1)
    }

    def event_date(value):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(BUSINESS_TIMEZONE).date()

    def record(day, vertical, amount):
        canonical = normalize_vertical(vertical) or "unallocated"
        if day in buckets:
            buckets[day][canonical] += Decimal(amount or 0)

    captured = db.query(Payment).filter(
        Payment.payment_status.in_((PaymentStatus.COMPLETED, PaymentStatus.REFUNDED)),
        Payment.payment_date >= after,
        Payment.payment_date < before,
        func.upper(Payment.currency) == wanted_currency,
    ).all()
    for payment in captured:
        day = event_date(payment.payment_date)
        for vertical, _stream, amount in _allocated_parts(db, payment):
            record(day, vertical, amount)

    refunded = db.query(Payment).filter(
        Payment.payment_status == PaymentStatus.REFUNDED,
        Payment.refund_processed_at >= after,
        Payment.refund_processed_at < before,
        func.upper(Payment.currency) == wanted_currency,
    ).all()
    for payment in refunded:
        day = event_date(payment.refund_processed_at)
        for vertical, _stream, amount in _allocated_parts(db, payment):
            record(day, vertical, -amount)

    tuition_rows = db.query(TuitionPayment).filter(
        TuitionPayment.status == "posted",
        TuitionPayment.paid_at >= after,
        TuitionPayment.paid_at < before,
        func.upper(TuitionPayment.currency) == wanted_currency,
    ).all()
    for row in tuition_rows:
        record(event_date(row.paid_at), "seyappaduporul", row.amount)

    voucher_rows = db.query(InternshipVoucher).filter(
        InternshipVoucher.created_at >= after,
        InternshipVoucher.created_at < before,
        InternshipVoucher.amount_paid > 0,
    ).all()
    for row in voucher_rows:
        record(event_date(row.created_at), "utporul", row.amount_paid)

    ledger_rows = db.query(RevenueLedgerEvent).filter(
        RevenueLedgerEvent.status == "posted",
        RevenueLedgerEvent.event_type.in_(("capture", "refund")),
        RevenueLedgerEvent.occurred_at >= after,
        RevenueLedgerEvent.occurred_at < before,
        func.upper(RevenueLedgerEvent.currency) == wanted_currency,
    ).all()
    for row in ledger_rows:
        amount = Decimal(row.gross_amount or 0)
        if row.event_type == "refund":
            amount = -amount
        record(event_date(row.occurred_at), row.business_vertical, amount)

    rows = []
    for day, values in buckets.items():
        point = {key: float(values[key]) for key in (*VERTICAL_KEYS, "unallocated")}
        point["date"] = day.isoformat()
        point["label"] = day.strftime("%d %b")
        point["revenue"] = float(sum(values.values(), ZERO))
        rows.append(point)
    return rows


def portfolio(db, start, end) -> dict:
    totals, streams, unallocated, unallocated_payments = _financial_snapshot(db, start, end)

    vertical_rows = []
    for key in VERTICAL_KEYS:
        data = VERTICALS[key]
        stream_rows = [
            {
                "key": stream,
                "label": STREAM_LABELS[stream],
                "currencies": _currency_rows(streams[key][stream]),
            }
            for stream in EXPECTED_STREAMS[key]
        ]
        vertical_rows.append({
            **data,
            "key": key,
            "inventory": _inventory(db, key),
            "revenue": {
                "currencies": _currency_rows(totals[key]),
                "streams": stream_rows,
            },
        })

    currencies = sorted({currency for key in VERTICAL_KEYS for currency in totals[key]} | set(unallocated))
    resilience = []
    for currency in currencies:
        net = {
            key: totals[key][currency]["captured"] - totals[key][currency]["refunded"]
            for key in VERTICAL_KEYS
        }
        positive_total = sum((max(ZERO, amount) for amount in net.values()), ZERO)
        leader = max(VERTICAL_KEYS, key=lambda key: net[key]) if positive_total > ZERO else None
        leader_positive = max(ZERO, net[leader]) if leader else ZERO
        share = float(leader_positive * 100 / positive_total) if positive_total > ZERO else None
        resilience.append({
            "currency": currency,
            "leader": leader,
            "largest_share_percent": round(share, 1) if share is not None else None,
            "remaining_if_leader_pauses": float(positive_total - leader_positive),
            "status": "concentrated" if share is not None and share > 60 else "balanced_mix" if share is not None else "no_revenue",
        })

    return {
        "from": str(start),
        "to": str(end),
        "as_of": datetime.now(timezone.utc),
        "verticals": vertical_rows,
        "unallocated": {
            "currencies": _currency_rows(unallocated),
            "payment_count": len(unallocated_payments),
            "course_count": _unallocated_course_count(db),
        },
        "resilience": resilience,
        "reporting_contract": {
            "operating_sources": [
                "commerce payments",
                "tuition ledger",
                "internship vouchers",
                "commercial revenue ledger",
            ],
            "rule": "Each source remains authoritative; this endpoint is the consolidated reporting read model.",
        },
    }
