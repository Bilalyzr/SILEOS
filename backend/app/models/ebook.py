"""Digital Library models (spec 2026-09-03-digital-library §1).

`Ebook` is one sellable digital product (PDF/EPUB). Store metadata is public
once published; `file_path` is PRIVATE — a path relative to backend/ebooks/
(NOT uploads/, which nginx serves publicly) that only the authenticated
download endpoint may resolve, and it must NEVER appear in an API response.
Prices are whole RUPEES (`price_inr`), matching the unit courses/bundles use
— paise exist only at the Razorpay boundary (max(int(round(p * 100)), 100)).

`EbookGrant` is one user's access to one ebook. UNIQUE(ebook_id, user_id)
backs the idempotent get-or-create in fulfillment_service.grant_ebook: a
purchase, a free claim, and an admin/owner grant all converge on one row.
Grants are for students — owner/admin read their own ebooks without grants.
Unpublishing hides an ebook from the store but NEVER touches grants
(spec §4: already-granted students keep download access), and deletion is
blocked with 409 while any grant exists (sold content is never deleted).
"""
from sqlalchemy import (JSON, Column, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.sql import func

from app.core.database import Base

# Enforced at the API layer (VARCHAR(16), no DB CHECK) — same precedent as
# Game.template / lesson_content_type. Displayed as Books / Guides /
# Lecture Notes tabs in the store.
EBOOK_CATEGORIES = ("book", "guide", "lecture_notes")


def effective_price_inr(ebook: "Ebook") -> int:
    """The rupee amount a buyer actually pays: the discount price when set
    (validated < price at the API layer), else the list price. Lives here so
    payments/fulfillment can import it without touching the library router
    (no import cycles). effective 0 == free == claimable, never orderable."""
    if ebook.discount_price_inr is not None:
        return int(ebook.discount_price_inr)
    return int(ebook.price_inr or 0)


def snapshot_prices_from_notes(notes, ebook: "Ebook | None" = None):
    """(charged_inr, list_inr) for one ebook capture, from the order notes
    written by `_create_ebook_order`.

    The single price authority for the ebook side of the payment stack — the
    /verify branch, the webhook processor and the reconciliation sweeper all
    call this so they cannot drift on what a capture was supposed to cost
    (the ebook analogue of `pricing.resolve_expected_purchase`, which owns
    the far more involved course case).

    `ebook_price_inr` is the checkout-time snapshot and is AUTHORITATIVE: a
    price edit between checkout and fulfillment must never orphan a real
    capture or rewrite the deal. The live row is consulted only as a fallback
    for a hand-built order carrying no snapshot. Returns (None, None) when
    neither is available — callers must refuse to price such a capture rather
    than guess.
    """
    notes = notes or {}
    charged = None
    try:
        value = notes.get("ebook_price_inr")
        if value is not None and str(value).strip() != "":
            charged = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        charged = None
    if charged is None or charged <= 0:
        # Hand-built order (or corrupt note): fall back to the live price.
        charged = effective_price_inr(ebook) if ebook is not None else None

    listed = None
    try:
        value = (notes or {}).get("ebook_list_price_inr")
        if value is not None and str(value).strip() != "":
            listed = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        listed = None
    if listed is None:
        listed = int(ebook.price_inr or 0) if ebook is not None else charged

    return charged, listed


class Ebook(Base):
    __tablename__ = "ebooks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    category = Column(String(16), nullable=False)  # book | guide | lecture_notes

    price_inr = Column(Integer, nullable=False, default=0)  # whole rupees
    discount_price_inr = Column(Integer, nullable=True)     # < price_inr when set

    cover_image = Column(String(500), default="")    # public uploads flow — images are fine public
    file_path = Column(String(500), nullable=True)   # PRIVATE; relative to backend/ebooks/
    file_size_bytes = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=True)
    sample_path = Column(String(500), nullable=True)  # grant-free preview PDF (semi-public)

    concept_tags = Column(JSON, nullable=False, default=list)  # <=10 strings, each <=50 chars
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)

    status = Column(String(16), nullable=False, default="draft")  # draft | published

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Ebook(id={self.id}, slug={self.slug}, status={self.status})>"


class EbookGrant(Base):
    """One user's access to one ebook. order_id NULL = free claim or
    admin/owner hand-grant; set = paid purchase (the money trail)."""
    __tablename__ = "ebook_grants"
    __table_args__ = (
        UniqueConstraint("ebook_id", "user_id", name="uq_ebook_grants_ebook_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ebook_id = Column(Integer, ForeignKey("ebooks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    source = Column(String(16), nullable=False, default="purchase")  # purchase | admin | owner
    granted_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EbookGrant(ebook_id={self.ebook_id}, user_id={self.user_id}, source={self.source})>"
