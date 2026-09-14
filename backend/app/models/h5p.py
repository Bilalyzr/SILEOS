"""H5P interactive-content models (plan Task 4, spec B4/B5/B8).

`H5PContent` is the metadata row for one uploaded-and-extracted `.h5p`
package (see app/services/h5p_service.py for the validation/extraction
pipeline). `public_id` is an opaque `secrets.token_hex(16)` string generated
server-side at upload time (h5p_service.generate_public_id) — never derived
from the owner/course id, matching the repo's existing opaque-token
convention (see live_class_service.generate_room_name,
certificate_service._generate_certificate_id).

`H5PResult` records a per-user, per-content advisory result (score/
completion) reported by the sandboxed client-side H5P runtime via
POST /api/v1/h5p/{public_id}/result. Per spec B6/B8 this is advisory
engagement data (feeds gamification), NOT gradebook truth — the H5P JS
executing inside the player iframe is instructor-supplied, untrusted code
and its self-reported score cannot be treated as an authoritative grade.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class H5PContent(Base):
    """One uploaded + validated + extracted H5P package."""
    __tablename__ = "h5p_contents"

    id = Column(Integer, primary_key=True, index=True)
    # Opaque public identifier used in URLs (/uploads/h5p/{public_id}/,
    # /api/v1/h5p/{public_id}) — random hex, unique, never the integer PK.
    public_id = Column(String(32), unique=True, nullable=False, index=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    # h5p.json's mainLibrary, e.g. "H5P.InteractiveVideo 1.22" — populated
    # once extraction succeeds; blank while status="uploaded"/"failed".
    library = Column(String(120), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)

    # uploaded (package received, not yet validated) -> ready (validated +
    # extracted, playable) -> failed (validation/extraction rejected it;
    # nothing was extracted to disk, see h5p_service.validate_and_extract).
    status = Column(String(20), nullable=False, default="uploaded")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<H5PContent(id={self.id}, public_id={self.public_id}, status={self.status})>"


class H5PResult(Base):
    """Per-user advisory result for one H5P content item. Upserted by
    POST /api/v1/h5p/{public_id}/result."""
    __tablename__ = "h5p_results"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("h5p_contents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    completed = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("content_id", "user_id", name="uq_h5p_result_content_user"),
    )

    def __repr__(self):
        return f"<H5PResult(content_id={self.content_id}, user_id={self.user_id}, completed={self.completed})>"
