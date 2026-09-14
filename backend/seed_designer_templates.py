#!/usr/bin/env python3
"""Seed the 5 production seed certificate templates (Learning Experience
plan Task 8, spec section C item 5) as `elements_config`-based `Certificate`
rows — the modern designer/renderer path (`certificate_html_renderer.
build_certificate_html`), NOT the legacy `post_name`-slug file path that
`seed_certificate_templates.py` seeds.

Every design below is composed from the exact element schema validated by
`app.routers.certificate_designer.validate_elements_config` (this seeder
runs each design's elements_config through that function before saving, so
a design that doesn't validate fails the seed run loudly instead of landing
in the DB as a silently-broken template) and only uses fonts from
`certificate_html_renderer.CURATED_FONTS`.

Designs (all A4 landscape, 1123x794 px @ 96 DPI) — v2, revised in a
creative-director fix round (D-1..D-5) that hardened the layout gates and
required every non-QR-approved design to be recomposed against them:
  - Ivory Classic     — warm ivory ground, thin double-rule border, centered
                         classic symmetry, tightened vertical rhythm; QR
                         fully inside the inner rule. Cormorant Garamond +
                         Lora.
  - Midnight Gold     — deep navy ground, gold accents, commits to
                         asymmetry with an oversized ghosted rect accent on
                         the right, a widened text measure, and date/
                         certificate-id/QR seated as one aligned foot group
                         (quiet-zone rect behind the QR for contrast).
                         DM Serif Display + Inter.
  - Tamil Heritage     — maroon + turmeric gold + ivory palette, a real
                         kolam-inspired interlocking diamond lattice (two
                         offset rows weaving top and bottom) plus small
                         corner dot-grid accents at the four corners —
                         abstract geometry only, no clip-art or faked
                         scripts. QR anchored to the foot baseline with the
                         date/id as one centered group. Playfair Display +
                         Poppins.
  - Gradient Modern    — light ground, a 24-band stepped-hue color spine
                         (indigo -> violet -> magenta) along the left edge
                         giving a smooth-ramp illusion (the element schema
                         has no gradient primitive); content spans the full
                         remaining width; date/certificate-id/QR seated
                         together bottom-right as one foot group. Outfit +
                         Inter.
  - Minimal Mono       — near-white ground, Space Grotesk only, one hairline
                         rule, oversized student_name, tiny letter-spaced
                         caps labels, small QR bottom-right, disciplined
                         whitespace. Approved as-is in the fix round — untouched.

Idempotent: matches rows by `post_title`, updating `elements_config` (and
the other design columns) in place on re-run rather than inserting a
duplicate. All 5 rows are `is_global=True`, `post_status='publish'`, and
keep an EMPTY `post_name` — an empty slug is what makes
`CertificateService.template_uses_elements_config()` prefer this dynamic
elements_config render path over the legacy static-file path (see
certificate_service.py / resolve_template), instead of colliding with the
slug-based rows seed_certificate_templates.py manages.

Thumbnails: when a Chrome/Chromium binary is available, this seeder renders
a real PNG per template via the existing headless-Chrome pipeline
(CertificateService._render_local_html_png_via_chrome) and writes it to
certificates/thumbnails/designer-{id}.png (an existence-checked path — see
app.routers.certificate_designer._to_out and certificates.list_certificate_
templates, both of which now surface a `thumbnail` URL when that file is on
disk). TemplateGallery.tsx renders that thumbnail image when present and
falls back to its existing CSS-swatch placeholder otherwise, so nothing
breaks when Chrome is unavailable (the common case in dev/CI — see
tests/test_certificate_designer.py's own note that Chrome is "very likely
absent on this box"); this seeder then no-ops the render with a log line
rather than failing the seed.

Usage (inside the backend container, or anywhere the DB is reachable):

    docker-compose exec backend python seed_designer_templates.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.certificate import Certificate
from app.models.user import User
from app.routers.certificate_designer import validate_elements_config
from app.services.certificate_html_renderer import build_certificate_html, sample_values

# A4 landscape at 96 DPI — matches the renderer/schema convention used
# throughout this codebase (schemas/certificate.py TemplateDimensions).
CERT_WIDTH = 1123
CERT_HEIGHT = 794


def _ivory_classic_elements() -> List[Dict[str, Any]]:
    """Warm ivory ground, thin double-rule border, centered classic
    symmetry. Cormorant Garamond display + Lora body.

    v2 (creative-director fix round, D-1): the QR now sits fully inside the
    inner rule (bottom at 700, well under the required <=720, with >=16px
    clearance from both border rects) instead of overlapping them, and the
    foot row (date/cert-id/QR) was pulled up from y=690 to y=610-620 to
    close the ~200px dead band that used to sit between the instructor line
    (previously y=480) and the foot — the whole lower half of the
    composition is now tightened into one coherent vertical rhythm.
    """
    return [
        # Thin double-rule border built from two nested rects (decorative,
        # z_index < 10 -> exempt from the overlap gate, but IS a
        # page-enclosing frame per the hardened gate — every non-decorative
        # element below is asserted strictly inside its inner bounds).
        {"id": "border-outer", "type": "rect", "x": 46, "y": 46,
         "width": CERT_WIDTH - 92, "height": CERT_HEIGHT - 92, "z_index": 1,
         "background_color": "transparent",
         "border": {"width": 2, "style": "solid", "color": "#c9a86a"}},
        {"id": "border-inner", "type": "rect", "x": 58, "y": 58,
         "width": CERT_WIDTH - 116, "height": CERT_HEIGHT - 116, "z_index": 1,
         "background_color": "transparent",
         "border": {"width": 1, "style": "solid", "color": "#c9a86a"}},

        {"id": "eyebrow", "type": "text", "content": "CERTIFICATE OF COMPLETION",
         "x": 261.5, "y": 108, "width": 600, "height": 22,
         "font_family": "Lora", "font_size": 16, "font_color": "#9a7b2e",
         "font_weight": "600", "text_align": "center", "letter_spacing": 4, "z_index": 10},
        {"id": "presented", "type": "text", "content": "This certificate is proudly presented to",
         "x": 211.5, "y": 150, "width": 700, "height": 22,
         "font_family": "Lora", "font_size": 15, "font_color": "#6b6154",
         "font_weight": "normal", "text_align": "center", "z_index": 10},
        {"id": "name", "type": "student_name",
         "x": 111.5, "y": 216, "width": 900, "height": 88,
         "font_family": "Cormorant Garamond", "font_size": 62, "font_color": "#2c2416",
         "font_weight": "600", "text_align": "center", "z_index": 10},
        {"id": "for-completing", "type": "text", "content": "for successfully completing the course",
         "x": 211.5, "y": 322, "width": 700, "height": 20,
         "font_family": "Lora", "font_size": 14, "font_color": "#6b6154",
         "font_weight": "normal", "text_align": "center", "z_index": 10},
        {"id": "course", "type": "course_name",
         "x": 161.5, "y": 354, "width": 800, "height": 38,
         "font_family": "Lora", "font_size": 27, "font_color": "#3a2f1d",
         "font_weight": "600", "text_align": "center", "z_index": 10},
        {"id": "rule", "type": "line", "x": 461.5, "y": 408, "width": 200, "height": 2,
         "z_index": 2, "font_color": "#c9a86a", "line_thickness": 1},
        {"id": "instructor", "type": "instructor_name",
         "x": 161.5, "y": 428, "width": 800, "height": 24,
         "font_family": "Lora", "font_size": 15, "font_color": "#6b6154",
         "font_weight": "normal", "text_align": "center", "z_index": 10},

        # Tightened foot row: date/id sit directly under the instructor
        # line (y=620) instead of the old ~200px-lower y=690, and the QR
        # (bottom=700) is fully inside the inner rule (frame bottom=735)
        # with >=16px clearance on every side.
        {"id": "date", "type": "completion_date",
         "x": 100, "y": 620, "width": 300, "height": 18,
         "font_family": "Lora", "font_size": 13, "font_color": "#7a7060",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "cert-id", "type": "certificate_id",
         "x": 613, "y": 620, "width": 300, "height": 18,
         "font_family": "Lora", "font_size": 13, "font_color": "#7a7060",
         "font_weight": "normal", "text_align": "right", "z_index": 10},
        {"id": "qr", "type": "qr_code", "x": 923, "y": 610, "width": 90, "height": 90, "z_index": 10},
    ]


def _midnight_gold_elements() -> List[Dict[str, Any]]:
    """Deep navy ground, gold accents. Commits fully to an asymmetric
    left-aligned block: three staggered thin gold rules of decreasing
    length occupy the empty zone right of the text (between the instructor
    line and the foot group) as a deliberate architectural accent, the
    text measure is widened, and date/cert-id/QR are seated together as
    ONE aligned foot group on a shared baseline (quiet-zone + QR on the
    left, date/id stacked beside it) instead of scattered fragments.
    DM Serif Display + Inter.

    v2 (creative-director fix round, D-3): previously everything lived in
    x=88-490 with the right half of the navy canvas empty and the foot
    elements (instructor/date/id/QR) disconnected at different x anchors.

    v3 (creative-director re-review, item 2): the first attempt at a
    right-side accent was a 1px #2a3550 hairline rect on a #101726 ground
    (~1.5:1 contrast) — indistinguishable from a rendering artifact.
    Replaced with three staggered, clearly-visible gold rules (same
    #c9a227 the rest of the design already uses, 2px thick, decreasing
    length) seated in the empty zone between the instructor line
    (bottom=436) and the foot group (top=594) — reads as a deliberate
    architectural flourish, not a bug.
    """
    return [
        {"id": "bg-rule-top", "type": "line", "x": 90, "y": 90, "width": 260, "height": 2,
         "z_index": 1, "font_color": "#c9a227", "line_thickness": 2},
        {"id": "eyebrow", "type": "text", "content": "CERTIFICATE OF ACHIEVEMENT",
         "x": 90, "y": 112, "width": 700, "height": 20,
         "font_family": "Inter", "font_size": 14, "font_color": "#c9a227",
         "font_weight": "600", "text_align": "left", "letter_spacing": 3, "z_index": 10},
        {"id": "name", "type": "student_name",
         "x": 88, "y": 168, "width": 940, "height": 92,
         "font_family": "DM Serif Display", "font_size": 62, "font_color": "#e8c766",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "awarded", "type": "text", "content": "has successfully completed",
         "x": 90, "y": 278, "width": 700, "height": 22,
         "font_family": "Inter", "font_size": 16, "font_color": "#c7cede",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "course", "type": "course_name",
         "x": 90, "y": 308, "width": 920, "height": 40,
         "font_family": "DM Serif Display", "font_size": 28, "font_color": "#f5f0e0",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "rule2", "type": "line", "x": 90, "y": 368, "width": 200, "height": 2,
         "z_index": 1, "font_color": "#c9a227", "line_thickness": 1},
        {"id": "instructor-label", "type": "text", "content": "Instructor",
         "x": 90, "y": 392, "width": 300, "height": 16,
         "font_family": "Inter", "font_size": 11, "font_color": "#8b93a8",
         "font_weight": "600", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "instructor", "type": "instructor_name",
         "x": 90, "y": 410, "width": 400, "height": 26,
         "font_family": "Inter", "font_size": 17, "font_color": "#e8c766",
         "font_weight": "500", "text_align": "left", "z_index": 10},

        # Three staggered, decreasing-length gold rules seated in the empty
        # zone between the instructor line (bottom=436) and the foot group
        # (top=594) — the deliberate right-side architectural accent that
        # commits to the asymmetric layout, clearly visible (same #c9a227
        # gold used everywhere else in this design, 2px thick).
        {"id": "accent-rule-1", "type": "line", "x": 733, "y": 460, "width": 300, "height": 2,
         "z_index": 2, "font_color": "#c9a227", "line_thickness": 2},
        {"id": "accent-rule-2", "type": "line", "x": 813, "y": 500, "width": 220, "height": 2,
         "z_index": 2, "font_color": "#c9a227", "line_thickness": 2},
        {"id": "accent-rule-3", "type": "line", "x": 893, "y": 540, "width": 140, "height": 2,
         "z_index": 2, "font_color": "#c9a227", "line_thickness": 2},

        # ONE aligned foot group on a shared baseline (y=594-694): the
        # quiet-zone + QR sit at the group's left edge, date/id stacked
        # immediately beside it — reads as a single unit, not fragments.
        {"id": "qr-quiet-zone", "type": "rect", "x": 78, "y": 594, "width": 114, "height": 114,
         "z_index": 5, "background_color": "#faf7f0", "border_radius": 6},
        {"id": "qr", "type": "qr_code", "x": 90, "y": 606, "width": 90, "height": 90, "z_index": 10},
        {"id": "date-label", "type": "text", "content": "DATE",
         "x": 220, "y": 606, "width": 200, "height": 12,
         "font_family": "Inter", "font_size": 9, "font_color": "#6b7593",
         "font_weight": "600", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "date", "type": "completion_date",
         "x": 220, "y": 622, "width": 260, "height": 18,
         "font_family": "Inter", "font_size": 13, "font_color": "#c7cede",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "id-label", "type": "text", "content": "CERTIFICATE ID",
         "x": 220, "y": 660, "width": 260, "height": 12,
         "font_family": "Inter", "font_size": 9, "font_color": "#6b7593",
         "font_weight": "600", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "cert-id", "type": "certificate_id",
         "x": 220, "y": 676, "width": 260, "height": 18,
         "font_family": "Inter", "font_size": 13, "font_color": "#c7cede",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
    ]


def _tamil_heritage_elements() -> List[Dict[str, Any]]:
    """Maroon + turmeric gold + ivory palette, with a real kolam-inspired
    GEOMETRIC motif — abstract geometry only, no faked scripts, no
    clip-art. Playfair Display + Poppins, centered composition.

    v2 (creative-director fix round, D-4): the single row of 24 diamonds
    read as "bunting" — replaced with an actual interlocking lattice: two
    horizontally-offset rows of rotated squares whose points interlace into
    a continuous woven band (top + bottom), plus four small corner
    dot-grid accents (a compact 5-point plus-shaped diamond cluster, one
    per page corner) that stay tucked well inside the margin, clear of
    both the lattice band and the centered text/foot content. The QR is
    anchored to the foot baseline WITH the date/certificate-id as one
    aligned, centered group instead of sitting alone in a far corner.

    Element-count note: the lattice spacing (60px step) and corner-accent
    density (5 dots, not a full 3x3=9) were chosen specifically to keep the
    total element count comfortably under DESIGNER_MAX_ELEMENTS=100 — an
    earlier, denser draft of this same lattice idea (26px step, 3x3
    corners) landed at 190 elements and failed validate_elements_config's
    100-element cap outright.
    """
    elements: List[Dict[str, Any]] = []

    maroon = "#6d1a2d"
    gold = "#c9932e"
    diamond = 20
    step = 60           # horizontal step between diamond centers in a row
    row_gap = 14         # vertical offset between the two interlocking rows

    band_span = CERT_WIDTH - 2 * 90  # keep the lattice inset from the page edges
    count = int(band_span / step)
    start_x = (CERT_WIDTH - (count - 1) * step) / 2

    def _lattice_band(base_y: float, id_prefix: str) -> List[Dict[str, Any]]:
        band: List[Dict[str, Any]] = []
        for i in range(count):
            color = maroon if i % 2 == 0 else gold
            x = start_x + i * step
            # Row A (primary): full-size diamonds on the baseline.
            band.append({
                "id": f"{id_prefix}-a-{i}", "type": "rect", "x": x, "y": base_y,
                "width": diamond, "height": diamond, "z_index": 1,
                "background_color": color, "rotation": 45,
            })
            # Row B (interlocking): smaller diamonds offset half a step
            # horizontally and `row_gap` vertically so their points weave
            # between row A's diamonds — this is what makes the strip read
            # as a continuous woven lattice instead of a single dotted row.
            if i < count - 1:
                band.append({
                    "id": f"{id_prefix}-b-{i}", "type": "rect",
                    "x": x + step / 2, "y": base_y + row_gap,
                    "width": diamond * 0.55, "height": diamond * 0.55, "z_index": 1,
                    "background_color": gold if color == maroon else maroon, "rotation": 45,
                })
        return band

    elements += _lattice_band(28, "kolam-top")
    elements += _lattice_band(CERT_HEIGHT - 28 - diamond - row_gap, "kolam-bottom")

    elements += [
        {"id": "rule-top", "type": "line", "x": 60, "y": 72, "width": CERT_WIDTH - 120, "height": 1,
         "z_index": 1, "font_color": gold, "line_thickness": 1},
        {"id": "rule-bottom", "type": "line", "x": 60, "y": CERT_HEIGHT - 72, "width": CERT_WIDTH - 120, "height": 1,
         "z_index": 1, "font_color": gold, "line_thickness": 1},
    ]

    def _corner_dot_cluster(cx: float, cy: float, id_prefix: str) -> List[Dict[str, Any]]:
        """A compact 5-point plus-shaped diamond cluster (center + 4
        neighbors) centered at (cx, cy) — footprint ~24x24px, small enough
        to sit inside the page margin without ever competing with the
        centered text block or foot group."""
        dot = 6
        gap = 12
        offsets = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]
        dots: List[Dict[str, Any]] = []
        for i, (ox, oy) in enumerate(offsets):
            dots.append({
                "id": f"{id_prefix}-{i}", "type": "rect",
                "x": cx + ox * gap - dot / 2, "y": cy + oy * gap - dot / 2,
                "width": dot, "height": dot, "z_index": 1,
                "background_color": maroon if i % 2 == 0 else gold, "rotation": 45,
            })
        return dots

    elements += _corner_dot_cluster(78, 78, "corner-tl")
    elements += _corner_dot_cluster(CERT_WIDTH - 78, 78, "corner-tr")
    elements += _corner_dot_cluster(78, CERT_HEIGHT - 78, "corner-bl")
    elements += _corner_dot_cluster(CERT_WIDTH - 78, CERT_HEIGHT - 78, "corner-br")

    elements += [
        {"id": "eyebrow", "type": "text", "content": "CERTIFICATE OF COMPLETION",
         "x": 261.5, "y": 128, "width": 600, "height": 20,
         "font_family": "Poppins", "font_size": 15, "font_color": maroon,
         "font_weight": "600", "text_align": "center", "letter_spacing": 3, "z_index": 10},
        {"id": "presented", "type": "text", "content": "This certificate is proudly presented to",
         "x": 211.5, "y": 168, "width": 700, "height": 22,
         "font_family": "Poppins", "font_size": 14, "font_color": "#7a5b3f",
         "font_weight": "normal", "text_align": "center", "z_index": 10},
        {"id": "name", "type": "student_name",
         "x": 111.5, "y": 232, "width": 900, "height": 82,
         "font_family": "Playfair Display", "font_size": 56, "font_color": maroon,
         "font_weight": "700", "text_align": "center", "z_index": 10},
        {"id": "for-completing", "type": "text", "content": "for successfully completing the course",
         "x": 211.5, "y": 330, "width": 700, "height": 20,
         "font_family": "Poppins", "font_size": 14, "font_color": "#7a5b3f",
         "font_weight": "normal", "text_align": "center", "z_index": 10},
        {"id": "course", "type": "course_name",
         "x": 161.5, "y": 362, "width": 800, "height": 36,
         "font_family": "Playfair Display", "font_size": 26, "font_color": "#3d2418",
         "font_weight": "600", "text_align": "center", "z_index": 10},
        {"id": "instructor", "type": "instructor_name",
         "x": 161.5, "y": 440, "width": 800, "height": 22,
         "font_family": "Poppins", "font_size": 14, "font_color": "#7a5b3f",
         "font_weight": "normal", "text_align": "center", "z_index": 10},

        # QR anchored to the foot baseline WITH the date/certificate-id —
        # one aligned, centered group (QR at the group's right end, well
        # clear of the corner dot-grid accents).
        #
        # v3 (creative-director re-review, item 1): the whole foot group
        # was previously at y=700-706 with the QR at y=660-740 — its bottom
        # (740) crossed the gold rule-bottom (y=722) AND overlapped the
        # bottom lattice band (starts y=732), the exact same defect class
        # as the original Ivory Classic D-1 QR-through-border bug. The
        # entire group is pulled up so the QR's bottom sits at y=706 —
        # 16px clear of rule-bottom (722) and 26px clear of the lattice
        # (732), both comfortably over the required >=12px.
        {"id": "date", "type": "completion_date",
         "x": 300, "y": 658, "width": 170, "height": 16,
         "font_family": "Poppins", "font_size": 12, "font_color": "#8a7256",
         "font_weight": "normal", "text_align": "right", "z_index": 10},
        {"id": "id-sep", "type": "text", "content": "|",
         "x": 482, "y": 658, "width": 10, "height": 16,
         "font_family": "Poppins", "font_size": 12, "font_color": "#c9b79a",
         "font_weight": "normal", "text_align": "center", "z_index": 10},
        {"id": "cert-id", "type": "certificate_id",
         "x": 503, "y": 658, "width": 170, "height": 16,
         "font_family": "Poppins", "font_size": 12, "font_color": "#8a7256",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "qr", "type": "qr_code", "x": 693, "y": 626, "width": 80, "height": 80, "z_index": 10},
    ]
    return elements


def _lerp_hex(c1: str, c2: str, t: float) -> str:
    """Linear-interpolate between two hex colors — used to build a smooth
    many-stop ramp out of the rect primitive (the element schema has no
    gradient type)."""
    a, b = c1.lstrip("#"), c2.lstrip("#")
    r1, g1, b1 = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    r2, g2, b2 = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b_ = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b_:02x}"


def _gradient_modern_elements() -> List[Dict[str, Any]]:
    """Light ground with a smooth stepped-hue color-band spine (indigo ->
    violet -> magenta) along the left edge standing in for a gradient —
    element schema has no gradient primitive. Outfit + Inter, left-rail
    layout with content spread across the full remaining width, a foot row
    spanning the width with date/certificate-id/QR seated together
    bottom-right as one aligned group.

    v2 (creative-director fix round, D-2): previously only 5 hard 14px
    bands (visible seams, read as stripes) and the right half of the page
    (x>500, y~320-560) sat empty with the QR orphaned alone top-right.
    Now: 24 x 4px bands sampled from a 5-stop ramp give a smooth-ramp
    illusion; student_name is larger (64px) and the course/instructor block
    widens to use the full remaining width; a rule spans that width so the
    middle of the page reads as designed space, not dead space; and
    date/certificate-id/QR sit together in one foot row bottom-right.
    """
    stops = ["#312e81", "#4338ca", "#6d28d9", "#9333ea", "#c026d3"]
    n_bands = 24
    band_w = 4

    def _ramp_color(i: int, n: int) -> str:
        t = i / (n - 1) if n > 1 else 0
        seg_count = len(stops) - 1
        seg = min(int(t * seg_count), seg_count - 1)
        local_t = (t * seg_count) - seg
        return _lerp_hex(stops[seg], stops[seg + 1], local_t)

    elements: List[Dict[str, Any]] = [
        {"id": f"band-{i}", "type": "rect", "x": i * band_w, "y": 0,
         "width": band_w, "height": CERT_HEIGHT, "z_index": 1,
         "background_color": _ramp_color(i, n_bands)}
        for i in range(n_bands)
    ]
    spine_w = n_bands * band_w  # 96
    content_x = spine_w + 64  # 160

    elements += [
        {"id": "eyebrow", "type": "text", "content": "CERTIFICATE OF COMPLETION",
         "x": content_x, "y": 96, "width": 700, "height": 18,
         "font_family": "Inter", "font_size": 13, "font_color": "#6d28d9",
         "font_weight": "700", "text_align": "left", "letter_spacing": 3, "z_index": 10},
        {"id": "name", "type": "student_name",
         "x": content_x, "y": 150, "width": 900, "height": 92,
         "font_family": "Outfit", "font_size": 64, "font_color": "#1e1b2e",
         "font_weight": "700", "text_align": "left", "z_index": 10},
        {"id": "awarded", "type": "text", "content": "has successfully completed",
         "x": content_x, "y": 258, "width": 700, "height": 22,
         "font_family": "Inter", "font_size": 16, "font_color": "#5b5568",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "course", "type": "course_name",
         "x": content_x, "y": 288, "width": 900, "height": 40,
         "font_family": "Outfit", "font_size": 30, "font_color": "#312e81",
         "font_weight": "600", "text_align": "left", "z_index": 10},

        # A wide rule spanning the remaining width gives the middle of the
        # page a deliberate structural element instead of empty space.
        {"id": "rule", "type": "line", "x": content_x, "y": 400, "width": 900, "height": 1,
         "z_index": 1, "font_color": "#e4defa", "line_thickness": 1},

        {"id": "instructor-label", "type": "text", "content": "INSTRUCTOR",
         "x": content_x, "y": 440, "width": 300, "height": 14,
         "font_family": "Inter", "font_size": 10, "font_color": "#9333ea",
         "font_weight": "700", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "instructor", "type": "instructor_name",
         "x": content_x, "y": 458, "width": 500, "height": 26,
         "font_family": "Inter", "font_size": 18, "font_color": "#1e1b2e",
         "font_weight": "600", "text_align": "left", "z_index": 10},

        # Foot row spans the width; date/certificate-id/QR seated together
        # bottom-right as one aligned group on a shared baseline.
        {"id": "date-label", "type": "text", "content": "DATE",
         "x": content_x, "y": 706, "width": 200, "height": 12,
         "font_family": "Inter", "font_size": 9, "font_color": "#9b93ab",
         "font_weight": "600", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "date", "type": "completion_date",
         "x": content_x, "y": 722, "width": 260, "height": 16,
         "font_family": "Inter", "font_size": 12, "font_color": "#3f3a4d",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "id-label", "type": "text", "content": "CERTIFICATE ID",
         "x": 700, "y": 706, "width": 250, "height": 12,
         "font_family": "Inter", "font_size": 9, "font_color": "#9b93ab",
         "font_weight": "600", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "cert-id", "type": "certificate_id",
         "x": 700, "y": 722, "width": 250, "height": 16,
         "font_family": "Inter", "font_size": 12, "font_color": "#3f3a4d",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "qr", "type": "qr_code", "x": 973, "y": 664, "width": 90, "height": 90, "z_index": 10},
    ]
    return elements


def _minimal_mono_elements() -> List[Dict[str, Any]]:
    """Near-white ground, a single black type family (Space Grotesk), one
    hairline rule, an oversized student_name, tiny letter-spaced caps
    labels, a small QR bottom-right, and extreme whitespace discipline."""
    return [
        {"id": "eyebrow", "type": "text", "content": "CERTIFICATE OF COMPLETION",
         "x": 90, "y": 90, "width": 600, "height": 16,
         "font_family": "Space Grotesk", "font_size": 11, "font_color": "#8a8a8a",
         "font_weight": "500", "text_align": "left", "letter_spacing": 3, "z_index": 10},
        {"id": "name", "type": "student_name",
         "x": 88, "y": 300, "width": 950, "height": 116,
         "font_family": "Space Grotesk", "font_size": 84, "font_color": "#111111",
         "font_weight": "700", "text_align": "left", "z_index": 10},
        {"id": "rule", "type": "line", "x": 90, "y": 440, "width": 943, "height": 1,
         "z_index": 1, "font_color": "#d8d8d8", "line_thickness": 1},
        {"id": "course-label", "type": "text", "content": "COURSE",
         "x": 90, "y": 470, "width": 300, "height": 14,
         "font_family": "Space Grotesk", "font_size": 10, "font_color": "#a3a3a3",
         "font_weight": "500", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "course", "type": "course_name",
         "x": 90, "y": 490, "width": 700, "height": 30,
         "font_family": "Space Grotesk", "font_size": 20, "font_color": "#222222",
         "font_weight": "500", "text_align": "left", "z_index": 10},
        {"id": "instructor-label", "type": "text", "content": "INSTRUCTOR",
         "x": 90, "y": 700, "width": 300, "height": 14,
         "font_family": "Space Grotesk", "font_size": 10, "font_color": "#a3a3a3",
         "font_weight": "500", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "instructor", "type": "instructor_name",
         "x": 90, "y": 718, "width": 300, "height": 20,
         "font_family": "Space Grotesk", "font_size": 14, "font_color": "#222222",
         "font_weight": "500", "text_align": "left", "z_index": 10},
        {"id": "date-label", "type": "text", "content": "DATE",
         "x": 420, "y": 700, "width": 200, "height": 14,
         "font_family": "Space Grotesk", "font_size": 10, "font_color": "#a3a3a3",
         "font_weight": "500", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "date", "type": "completion_date",
         "x": 420, "y": 718, "width": 250, "height": 18,
         "font_family": "Space Grotesk", "font_size": 13, "font_color": "#222222",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "id-label", "type": "text", "content": "CERTIFICATE ID",
         "x": 690, "y": 700, "width": 250, "height": 14,
         "font_family": "Space Grotesk", "font_size": 10, "font_color": "#a3a3a3",
         "font_weight": "500", "text_align": "left", "letter_spacing": 2, "z_index": 10},
        {"id": "cert-id", "type": "certificate_id",
         "x": 690, "y": 718, "width": 250, "height": 18,
         "font_family": "Space Grotesk", "font_size": 13, "font_color": "#222222",
         "font_weight": "normal", "text_align": "left", "z_index": 10},
        {"id": "qr", "type": "qr_code", "x": 973, "y": 664, "width": 80, "height": 80, "z_index": 10},
    ]


# name -> (description, background_color, elements-builder)
DESIGNS = [
    (
        "Ivory Classic",
        "Warm ivory ground with a thin double-rule border and centered classic "
        "symmetry — Cormorant Garamond display over a Lora body.",
        "#faf7f0",
        _ivory_classic_elements,
    ),
    (
        "Midnight Gold",
        "Deep navy ground with gold accents in an elegant asymmetric "
        "left-aligned layout — DM Serif Display headline over Inter body text.",
        "#101726",
        _midnight_gold_elements,
    ),
    (
        "Tamil Heritage",
        "Maroon, turmeric gold and ivory palette with a kolam-inspired "
        "geometric diamond-lattice motif — Playfair Display over Poppins.",
        "#fdf8ee",
        _tamil_heritage_elements,
    ),
    (
        "Gradient Modern",
        "Light ground with an indigo-to-violet color-band spine along the "
        "left edge — a modern SaaS-style certificate in Outfit and Inter.",
        "#ffffff",
        _gradient_modern_elements,
    ),
    (
        "Minimal Mono",
        "Near-white ground, a single Space Grotesk type family, one "
        "hairline rule and an oversized student name — extreme restraint.",
        "#ffffff",
        _minimal_mono_elements,
    ),
]


def _resolve_author(db: Session) -> int:
    """post_author is a NOT NULL FK to users.id — pick an admin, else any user."""
    user = (
        db.query(User).filter(User.role.in_(("admin", "superadmin"))).order_by(User.id).first()
        or db.query(User).order_by(User.id).first()
    )
    if not user:
        raise SystemExit("No users exist yet — create an admin first (see create_admin.py).")
    return user.id


def seed(db: Session) -> List[Certificate]:
    """Idempotently create/update the 5 seed designer templates. Returns the
    5 Certificate rows (created or updated) in DESIGNS order."""
    author_id = _resolve_author(db)
    rows: List[Certificate] = []

    for name, description, bg_color, build_elements in DESIGNS:
        elements = validate_elements_config(build_elements())

        row = db.query(Certificate).filter(Certificate.post_title == name).first()
        if row:
            row.post_excerpt = description
            row.post_status = "publish"
            row.post_type = "tutor_certificates"
            row.post_name = ""  # empty slug -> dynamic elements_config render path
            row.certificate_orientation = "landscape"
            row.certificate_size = "A4"
            row.certificate_width = CERT_WIDTH
            row.certificate_height = CERT_HEIGHT
            row.background_color = bg_color
            row.background_image = ""
            row.elements_config = elements
            row.is_global = True
            print(f"  - updated '{name}' (id={row.id})")
        else:
            row = Certificate(
                post_author=author_id,
                post_title=name,
                post_name="",
                post_excerpt=description,
                post_status="publish",
                post_type="tutor_certificates",
                certificate_orientation="landscape",
                certificate_size="A4",
                certificate_width=CERT_WIDTH,
                certificate_height=CERT_HEIGHT,
                background_color=bg_color,
                background_image="",
                elements_config=elements,
                is_global=True,
                post_content="",
            )
            db.add(row)
            print(f"  + created '{name}'")
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def _make_thumbnails(db: Session, rows: List[Certificate]) -> None:
    """Best-effort real PNG thumbnail render via the existing headless-Chrome
    pipeline, saved to certificates/thumbnails/designer-{id}.png — the exact
    on-disk path `app.routers.certificate_designer._to_out` and
    `app.routers.certificates.list_certificate_templates` check for and
    surface as a `thumbnail` URL (served from the existing
    `/certificate-files` static mount, so no new backend endpoint/DB column
    is needed — this is a pure file-existence check at read time).
    TemplateGallery.tsx renders that thumbnail image when present and falls
    back to its existing CSS-swatch placeholder otherwise. No-ops with a
    log line when Chrome is unavailable, which is the normal case in
    dev/CI (see tests/test_certificate_designer.py's own note)."""
    import shutil

    from app.services.certificate_service import CertificateService

    has_chrome = bool(
        shutil.which("google-chrome-stable")
        or shutil.which("google-chrome")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if not has_chrome:
        print(
            "  (i) No Chrome/Chromium binary found on this machine — skipping "
            "thumbnail render. The designer gallery falls back to its CSS-swatch "
            "placeholder when no thumbnail file exists; run this script again "
            "on a box with Chrome installed to also produce real preview PNGs."
        )
        return

    out_dir = Path(__file__).parent / "certificates" / "thumbnails"
    out_dir.mkdir(parents=True, exist_ok=True)

    values = sample_values()
    for row in rows:
        try:
            html_doc = build_certificate_html(row, values)
            png_bytes = CertificateService._render_local_html_png_via_chrome(
                html_doc, row.certificate_width, row.certificate_height
            )
            out_path = out_dir / f"designer-{row.id}.png"
            out_path.write_bytes(png_bytes)
            print(f"  + thumbnail rendered: {out_path}")
        except Exception as exc:  # noqa: BLE001 — thumbnails are best-effort
            print(f"  (i) thumbnail render failed for '{row.post_title}': {exc}")


def main() -> None:
    db = SessionLocal()
    try:
        print("Seeding designer certificate templates…")
        rows = seed(db)
        print(f"Done — {len(rows)} template(s) available via GET /api/v1/certificates/designer/list")
        _make_thumbnails(db, rows)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
