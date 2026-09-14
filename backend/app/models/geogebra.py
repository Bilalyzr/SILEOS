"""GeoGebra applet models (owner-approved integration, 2026-09-04).

⚠️ LICENCE NOTE (blueprint §8.3 / sasha-geogebra skill): GeoGebra Apps are
free for NON-COMMERCIAL use; commercial embedding requires an agreement
with GeoGebra GmbH. The owner has approved building the integration on
this basis for preview/development. Before PAID production launch, obtain
the written licence or swap the embed layer.

`GeoGebraApplet` is one interactive applet an instructor can attach to a
lesson of a FREE course (business rule enforced in courses.py's content
resolver, not just the UI). Two authoring modes, mirroring blueprint §8.3:
  - `material_id` set: embeds an existing GeoGebra Materials resource
    (instructor pastes the materials URL/ID).
  - `material_id` null: a blank app of the chosen `app_type` the instructor
    builds live in the authoring canvas (persists via ggbBase64 later).
`config` JSON carries deployggb.js applet parameters (perspective,
showToolBar, width/height overrides) — never free-form HTML.
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base

# deployggb.js appName values (GeoGebra Apps API).
GEOGEBRA_APP_TYPES = ("graphing", "geometry", "classic", "3d", "cas")
GEOGEBRA_ELEMENT_ID = "sileos-geogebra-{id}"


class GeoGebraApplet(Base):
    """One reusable GeoGebra applet owned by an instructor."""
    __tablename__ = "geogebra_applets"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    app_type = Column(String(20), nullable=False, default="graphing")
    # GeoGebra Materials id (from a shared materials URL) — null = blank app.
    material_id = Column(String(100), nullable=True)
    # Saved construction (base64 .ggb) for blank-app authoring; set later by
    # the editor's saveState — never trusted, only replayed into the applet.
    ggb_base64 = Column(Text, nullable=True)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())

    def embed_params(self) -> dict:
        """The deployggb.js appletParameters payload for this row."""
        params = {
            "appName": self.app_type,
            "width": int(self.config.get("width", 800)) if self.config else 800,
            "height": int(self.config.get("height", 500)) if self.config else 500,
            "showToolBar": bool(self.config.get("showToolBar", True)) if self.config else True,
            "showAlgebraInput": bool(self.config.get("showAlgebraInput", True)) if self.config else True,
            "enableShiftDragZoom": True,
            "showResetIcon": True,
            "language": "en",
        }
        if self.material_id:
            params["material_id"] = self.material_id
        elif self.ggb_base64:
            params["ggbBase64"] = self.ggb_base64
        return params
