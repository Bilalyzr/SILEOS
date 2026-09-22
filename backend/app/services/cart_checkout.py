"""Immutable Razorpay cart snapshots shared by all fulfillment paths.

Razorpay order notes are the durable hand-off between create-order, browser
verification, the webhook inbox and the reconciliation sweeper.  A compact
``course_id:price_paise`` snapshot prevents a later catalogue price change
from either blocking access after capture or changing the revenue allocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


MAX_CART_COURSES = 10
MAX_SNAPSHOT_LENGTH = 240


class CartSnapshotError(ValueError):
    """Raised when a request or gateway-note cart snapshot is unusable."""


@dataclass(frozen=True)
class CartSnapshot:
    line_prices_paise: dict[int, int]
    subtotal_paise: int
    discount_paise: int
    total_paise: int
    coupon_id: int | None = None
    coupon_code: str | None = None

    @property
    def course_ids(self) -> list[int]:
        return list(self.line_prices_paise)

    def to_notes(self, *, user_id: int) -> dict[str, str]:
        notes = {
            "checkout_type": "cart",
            "user_id": str(user_id),
            "cart_lines": encode_cart_lines(self.line_prices_paise),
            "cart_subtotal_paise": str(self.subtotal_paise),
            "cart_discount_paise": str(self.discount_paise),
            "cart_total_paise": str(self.total_paise),
        }
        if self.coupon_id is not None:
            notes["coupon_id"] = str(self.coupon_id)
        if self.coupon_code:
            notes["coupon_code"] = self.coupon_code
        return notes


def canonical_course_ids(course_ids: Iterable[int]) -> list[int]:
    """Validate and canonicalize a cart course set.

    Duplicates are rejected instead of silently changing what the buyer sent;
    stable sorting makes the gateway snapshot and later exact-set comparison
    deterministic.
    """
    try:
        values = [int(value) for value in course_ids]
    except (TypeError, ValueError):
        raise CartSnapshotError("Course IDs must be integers")
    if not values:
        raise CartSnapshotError("Select at least one course")
    if len(values) > MAX_CART_COURSES:
        raise CartSnapshotError(
            f"A single checkout can contain at most {MAX_CART_COURSES} courses"
        )
    if any(value <= 0 for value in values):
        raise CartSnapshotError("Course IDs must be positive")
    if len(set(values)) != len(values):
        raise CartSnapshotError("A course can appear only once in a cart")
    return sorted(values)


def encode_cart_lines(line_prices_paise: Mapping[int, int]) -> str:
    ids = canonical_course_ids(line_prices_paise)
    parts: list[str] = []
    for course_id in ids:
        price = int(line_prices_paise[course_id])
        if price < 0:
            raise CartSnapshotError("Cart line prices cannot be negative")
        parts.append(f"{course_id}:{price}")
    encoded = ",".join(parts)
    if len(encoded) > MAX_SNAPSHOT_LENGTH:
        raise CartSnapshotError("Cart is too large for one secure checkout")
    return encoded


def build_cart_snapshot(
    line_prices_paise: Mapping[int, int],
    *,
    discount_paise: int = 0,
    coupon_id: int | None = None,
    coupon_code: str | None = None,
) -> CartSnapshot:
    encoded = encode_cart_lines(line_prices_paise)
    # Decode once to guarantee identical normalization to the recovery paths.
    normalized: dict[int, int] = {}
    for part in encoded.split(","):
        raw_id, raw_price = part.split(":", 1)
        normalized[int(raw_id)] = int(raw_price)
    subtotal = sum(normalized.values())
    discount = int(discount_paise)
    if subtotal < 100:
        raise CartSnapshotError(
            "Cart total must be at least Rs.1 for gateway checkout"
        )
    if discount < 0 or discount > subtotal:
        raise CartSnapshotError("Cart discount is outside the valid range")
    total = subtotal - discount
    if total <= 0:
        raise CartSnapshotError(
            "This cart is fully discounted; complete it as a free order"
        )
    # Razorpay's minimum order is Rs.1. Reduce the recorded discount by the
    # sub-rupee difference so accounting always equals the amount captured.
    if total < 100:
        total = 100
        discount = subtotal - total
    return CartSnapshot(
        line_prices_paise=normalized,
        subtotal_paise=subtotal,
        discount_paise=discount,
        total_paise=total,
        coupon_id=int(coupon_id) if coupon_id is not None else None,
        coupon_code=(coupon_code or "").strip().upper() or None,
    )


def parse_cart_notes(notes: Mapping[str, object] | None) -> CartSnapshot:
    notes = notes or {}
    if notes.get("checkout_type") != "cart":
        raise CartSnapshotError("Gateway order is not a cart checkout")
    encoded = str(notes.get("cart_lines") or "")
    if not encoded or len(encoded) > MAX_SNAPSHOT_LENGTH:
        raise CartSnapshotError("Gateway order has no usable cart lines")

    line_prices: dict[int, int] = {}
    try:
        for part in encoded.split(","):
            raw_id, raw_price = part.split(":", 1)
            course_id, price = int(raw_id), int(raw_price)
            if course_id <= 0 or price < 0 or course_id in line_prices:
                raise ValueError
            line_prices[course_id] = price
        canonical_course_ids(line_prices)
        subtotal = int(notes.get("cart_subtotal_paise"))
        discount = int(notes.get("cart_discount_paise"))
        total = int(notes.get("cart_total_paise"))
    except (TypeError, ValueError, CartSnapshotError):
        raise CartSnapshotError("Gateway order contains a malformed cart snapshot")

    if subtotal != sum(line_prices.values()):
        raise CartSnapshotError("Gateway cart subtotal does not match its lines")
    if discount < 0 or discount > subtotal or total < 100:
        raise CartSnapshotError("Gateway cart totals are outside the valid range")
    if subtotal - discount != total:
        raise CartSnapshotError("Gateway cart total does not reconcile")

    coupon_id = None
    if notes.get("coupon_id") not in (None, ""):
        try:
            coupon_id = int(notes.get("coupon_id"))
        except (TypeError, ValueError):
            raise CartSnapshotError("Gateway cart coupon is malformed")
    coupon_code = str(notes.get("coupon_code") or "").strip().upper() or None
    if bool(coupon_id) != bool(coupon_code):
        raise CartSnapshotError("Gateway cart coupon snapshot is incomplete")

    return CartSnapshot(
        line_prices_paise=dict(sorted(line_prices.items())),
        subtotal_paise=subtotal,
        discount_paise=discount,
        total_paise=total,
        coupon_id=coupon_id,
        coupon_code=coupon_code,
    )
