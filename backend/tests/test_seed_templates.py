"""Tests for the 5 production seed certificate templates (Learning
Experience plan Task 8, spec section C item 5 — v2, creative-director fix
round D-1..D-8).

Covers:
  - seeder idempotency: running `seed(db)` twice yields exactly 5 rows, no
    duplicates, matched by post_title
  - every design's elements_config passes `validate_elements_config`
    verbatim (the seeder itself already runs designs through this before
    saving, so this also guards against the seeder's own validation call
    ever being silently removed)
  - layout QUALITY GATES per the plan (hardened across the D-6/D-7 fix
    round and a subsequent re-review): no two non-decorative (z_index >=
    10) text/QR/image bounding boxes overlap; every element is fully
    inside the page with >=40px margin for text elements; non-decorative
    elements ALSO sit strictly inside every page-enclosing decorative
    FRAME rect's inner bounds with clearance (D-6); every QR is checked
    against ALL decorative elements regardless of z_index — any rect (with
    a real, non-transparent fill) or line that visibly paints over the
    QR's box requires an explicit light quiet-zone rect fully covering it
    (re-review item 3: a light PAGE background alone no longer excuses
    decoration directly behind the QR — that gap is exactly how the Tamil
    Heritage QR-on-lattice regression slipped through the D-6 gate);
    student_name is the visually largest text (font_size strictly greater
    than every other text element); QR >= 80px; foot elements
    (completion_date/certificate_id) have font_size <= 16px
  - fixture proofs (TestGateCatchesFrameCrossing) that the hardened gates
    actually FAIL on: the old (pre-fix) Ivory Classic QR position that
    crossed both border rules; a QR with no light background/quiet-zone at
    all; and the old (pre-re-review) Tamil Heritage QR position that
    crossed a gold rule and a lattice diamond despite a light page
    background — proves the gates have teeth
  - each design renders through `build_certificate_html` with sample values
    without raising, and the output contains the substituted student_name
  - every font used across all 5 designs is in CURATED_FONTS
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.models.certificate import Certificate  # noqa: E402
from app.routers.certificate_designer import validate_elements_config  # noqa: E402
from app.services.certificate_html_renderer import (  # noqa: E402
    CURATED_FONTS,
    build_certificate_html,
    sample_values,
)
from seed_designer_templates import DESIGNS, seed  # noqa: E402

EXPECTED_NAMES = {
    "Ivory Classic",
    "Midnight Gold",
    "Tamil Heritage",
    "Gradient Modern",
    "Minimal Mono",
}

# Mirrors the renderer's own text flow: a rendered text element's height is
# approximated as font_size * 1.35 (line-height) ONLY as a MINIMUM floor
# when the declared height is smaller than that (D-7) — otherwise the
# DECLARED width/height is used verbatim, since that's what actually paints
# (`_element_css` in certificate_html_renderer.py sets `width`/`height`
# directly from the element's own fields, never recomputing them from
# font_size).
LINE_HEIGHT_FACTOR = 1.35

_TEXT_TYPES = {
    "student_name", "course_name", "completion_date", "certificate_id",
    "instructor_name", "text",
}
_BOX_TYPES = _TEXT_TYPES | {"qr_code", "image", "signature_image"}

# D-6: a bordered decorative rect only functions as a page-enclosing FRAME
# (gating where other elements may sit) when it is unrotated and spans most
# of the page in both axes — a small/rotated corner ornament or accent
# shape is decoration, not a boundary. Mirrors the same threshold used
# while iterating the designs by hand before writing them into the seeder.
_FRAME_COVERAGE_MIN = 0.7
_FRAME_CLEARANCE = 16
_QUIET_ZONE_PADDING = 8


def _bbox(el: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """D-7: use the element's DECLARED width/height verbatim (what actually
    paints, per `_element_css`) — the font_size*1.35 line-height factor is
    only applied as a MINIMUM height floor when the declared height is
    smaller than that, never as an override of an explicit, larger
    declared height."""
    x = float(el.get("x", 0))
    y = float(el.get("y", 0))
    w = float(el.get("width", 100))
    h = float(el.get("height", 40))
    if el.get("type") in _TEXT_TYPES:
        floor = float(el.get("font_size", 24)) * LINE_HEIGHT_FACTOR
        h = max(h, floor)
    return x, y, x + w, y + h


def _overlaps(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


def _border_width(el: Dict[str, Any]) -> float:
    """Extract a decorative rect's border width from either the designer's
    native dict shape or the renderer's normalized '{w}px {style} {color}'
    string shape (validate_elements_config re-emits borders in the latter)."""
    border = el.get("border")
    if isinstance(border, dict):
        try:
            return float(border.get("width", 0) or 0)
        except (TypeError, ValueError):
            return 0.0
    if isinstance(border, str) and border.strip():
        parts = border.strip().split()
        if parts and parts[0].endswith("px"):
            try:
                return float(parts[0][:-2])
            except ValueError:
                return 0.0
    return 0.0


def _is_light_color(color: Optional[str]) -> bool:
    """Perceived-luminance check for a hex color — gates whether a page
    background or quiet-zone fill provides safe QR scanner contrast."""
    if not color or not isinstance(color, str):
        return False
    c = color.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) < 6:
        return False
    try:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        return False
    return (0.299 * r + 0.587 * g + 0.114 * b) >= 170


def _frame_rects(elements: List[Dict[str, Any]], page_width: int, page_height: int) -> List[Dict[str, Any]]:
    """D-6: decorative rects that function as a page-enclosing FRAME —
    unrotated, bordered, and spanning most of the page in both axes."""
    frames = []
    for el in elements:
        if el.get("type") != "rect" or float(el.get("z_index", 0)) >= 10:
            continue
        if _border_width(el) <= 0:
            continue
        if float(el.get("rotation", 0) or 0) != 0:
            continue  # rotated shapes are ornaments, not enclosing frames
        w = float(el.get("width", 0))
        h = float(el.get("height", 0))
        if w >= page_width * _FRAME_COVERAGE_MIN and h >= page_height * _FRAME_COVERAGE_MIN:
            frames.append(el)
    return frames


def _frame_inner_bounds(frame: Dict[str, Any]) -> Tuple[float, float, float, float]:
    bw = _border_width(frame)
    x1, y1, x2, y2 = _bbox(frame)
    return x1 + bw, y1 + bw, x2 - bw, y2 - bw


def _has_real_fill(el: Dict[str, Any]) -> bool:
    """True when a rect has an actual paintable fill — not None/empty and
    not the literal 'transparent' keyword. A border-only rect (e.g. a
    decorative double-rule frame with `background_color: 'transparent'`)
    does NOT visibly paint its full bounding box; only the thin border
    stroke along its edge is visible, so a QR sitting well inside such a
    frame's interior (as Ivory Classic's does, D-1) is not "behind"
    anything just because it falls within the frame's overall bbox."""
    fill = el.get("background_color") or el.get("fill")
    if not fill or not isinstance(fill, str):
        return False
    return fill.strip().lower() != "transparent"


def _border_stroke_bands(el: Dict[str, Any]) -> List[Tuple[float, float, float, float]]:
    """The up-to-4 thin rectangular bands a rect's border actually paints
    (top/bottom/left/right edges) — used to test whether a border-only
    rect's STROKE (not its whole bbox) overlaps something, since a
    transparent-fill bordered rect only paints along its edge."""
    bw = _border_width(el)
    if bw <= 0:
        return []
    x1, y1, x2, y2 = _bbox(el)
    return [
        (x1, y1, x2, y1 + bw),          # top
        (x1, y2 - bw, x2, y2),          # bottom
        (x1, y1, x1 + bw, y2),          # left
        (x2 - bw, y1, x2, y2),          # right
    ]


def _decoration_paints_over(el: Dict[str, Any], box: Tuple[float, float, float, float]) -> bool:
    """True when decorative element `el` (a rect or line) actually paints
    visible pixels that overlap `box` — a filled rect or a line always
    counts (a line has no meaningful 'unfilled interior'); a border-only
    rect (transparent/no fill) only counts if `box` intersects one of its
    thin border-stroke bands, not merely its overall bounding box."""
    if el.get("type") == "line":
        return _overlaps(_bbox(el), box)
    if el.get("type") != "rect":
        return False
    if _has_real_fill(el):
        return _overlaps(_bbox(el), box)
    # Border-only (or fill-less) rect: only its stroke bands paint.
    return any(_overlaps(band, box) for band in _border_stroke_bands(el))


def assert_layout_gates(
    elements: List[Dict[str, Any]],
    width: int,
    height: int,
    *,
    page_bg_color: str = "#ffffff",
    text_margin: int = 40,
) -> None:
    """The Task 8 layout quality gates (hardened D-6/D-7), asserted against
    a normalized elements_config list. Decorative elements (z_index < 10)
    are exempt from the overlap check — rects/lines used as intentional
    layered decoration (borders, rules, color bands, quiet-zones, kolam
    motifs)."""
    boxed = [el for el in elements if el.get("type") in _BOX_TYPES]
    frames = _frame_rects(elements, width, height)

    # Bounds + margin + D-6 frame containment.
    for el in boxed:
        x1, y1, x2, y2 = _bbox(el)
        assert x1 >= 0 and y1 >= 0 and x2 <= width and y2 <= height, (
            f"{el.get('type')}/{el.get('id')} out of page bounds: {(x1, y1, x2, y2)} vs {width}x{height}"
        )
        if el.get("type") in _TEXT_TYPES:
            assert x1 >= text_margin, f"{el.get('id')} left margin < {text_margin}px"
            assert y1 >= text_margin, f"{el.get('id')} top margin < {text_margin}px"
            assert (width - x2) >= text_margin, f"{el.get('id')} right margin < {text_margin}px"
            assert (height - y2) >= text_margin, f"{el.get('id')} bottom margin < {text_margin}px"

        # D-6: every non-decorative box must sit strictly inside any
        # page-enclosing frame's inner bounds, with clearance.
        for frame in frames:
            fx1, fy1, fx2, fy2 = _frame_inner_bounds(frame)
            inside = (
                x1 >= fx1 + _FRAME_CLEARANCE and y1 >= fy1 + _FRAME_CLEARANCE
                and x2 <= fx2 - _FRAME_CLEARANCE and y2 <= fy2 - _FRAME_CLEARANCE
            )
            assert inside, (
                f"{el.get('type')}/{el.get('id')} not inside frame '{frame.get('id')}' inner bounds "
                f"{(fx1, fy1, fx2, fy2)} (clearance {_FRAME_CLEARANCE}px): elbox={(x1, y1, x2, y2)}"
            )

    # No overlap among non-decorative (z_index >= 10) elements.
    non_decor = [el for el in boxed if float(el.get("z_index", 0)) >= 10]
    for i in range(len(non_decor)):
        for j in range(i + 1, len(non_decor)):
            a, b = non_decor[i], non_decor[j]
            assert not _overlaps(_bbox(a), _bbox(b)), (
                f"overlap between '{a.get('id')}' and '{b.get('id')}': {_bbox(a)} vs {_bbox(b)}"
            )

    # student_name is the strictly largest text element.
    texts = [el for el in elements if el.get("type") in _TEXT_TYPES]
    name_el = next((el for el in texts if el.get("type") == "student_name"), None)
    assert name_el is not None, "design has no student_name element"
    name_fs = float(name_el.get("font_size", 0))
    for el in texts:
        if el is name_el:
            continue
        assert float(el.get("font_size", 0)) < name_fs, (
            f"student_name (fs={name_fs}) is not strictly largest — "
            f"'{el.get('id')}' has fs={el.get('font_size')}"
        )

    # QR >= 80px, and deliberately placed (D-6, hardened per re-review
    # item 3). The check is now two-part and does NOT short-circuit on a
    # light page background alone — a light page color says nothing about
    # whether a decorative rect/line sits directly behind (or overlapping)
    # the QR (this is exactly how the Tamil Heritage QR-on-lattice bug got
    # past the earlier version of this gate: page_bg_color was light, so
    # the whole check was skipped even though the gold rule and lattice
    # diamonds visibly crossed the QR):
    #   1. If ANY decorative element (rect or line, ANY z_index — not just
    #      z_index < 10; a rule/lattice piece a designer forgot to mark
    #      decorative should still be caught) VISIBLY PAINTS OVER the QR's
    #      box, that is only acceptable when an explicit light quiet-zone
    #      rect (light fill, z strictly between the decoration and the QR,
    #      fully covering the QR with >=8px padding) is also present. "Paints
    #      over" is deliberately narrower than "bounding boxes overlap": a
    #      line, or a rect with a real (non-transparent) fill, always
    #      counts; a border-only rect (e.g. a double-rule frame with
    #      background_color: 'transparent', like Ivory Classic's) only
    #      counts if the QR intersects its thin BORDER STROKE band, not
    #      merely its overall bbox — a QR sitting well inside such a
    #      frame's open interior is not "behind" anything.
    #   2. If NO decorative element overlaps the QR at all, a light page
    #      background is sufficient on its own (nothing to give contrast
    #      trouble) — this preserves the earlier, correct behavior for a
    #      QR sitting on plain light ground with no ornament behind it.
    qr_elements = [el for el in elements if el.get("type") == "qr_code"]
    assert qr_elements, "design has no qr_code element"
    for qr in qr_elements:
        w = float(qr.get("width", 0))
        h = float(qr.get("height", 0))
        assert w >= 80, f"QR width < 80px: {w}"
        assert h >= 80, f"QR height < 80px: {h}"

        qx1, qy1, qx2, qy2 = _bbox(qr)
        qr_z = float(qr.get("z_index", 0))

        def _covers_qr_as_quiet_zone(el: Dict[str, Any]) -> bool:
            if el.get("type") != "rect":
                return False
            fill = el.get("background_color") or el.get("fill")
            if not _is_light_color(fill):
                return False
            if not (float(el.get("z_index", 0)) < qr_z):
                return False
            rx1, ry1, rx2, ry2 = _bbox(el)
            return (
                rx1 <= qx1 - _QUIET_ZONE_PADDING and ry1 <= qy1 - _QUIET_ZONE_PADDING
                and rx2 >= qx2 + _QUIET_ZONE_PADDING and ry2 >= qy2 + _QUIET_ZONE_PADDING
            )

        has_quiet_zone = any(_covers_qr_as_quiet_zone(el) for el in elements)

        decorations_behind_qr = [
            el for el in elements
            if el is not qr
            and el.get("type") in ("rect", "line")
            and not _covers_qr_as_quiet_zone(el)  # the quiet-zone rect itself doesn't count as "decoration in the way"
            and _decoration_paints_over(el, (qx1, qy1, qx2, qy2))
        ]

        if decorations_behind_qr:
            assert has_quiet_zone, (
                f"QR '{qr.get('id')}' overlaps decorative element(s) "
                f"{[d.get('id') for d in decorations_behind_qr]} with no explicit light "
                "quiet-zone rect (light fill, z below the QR, >=8px padding) covering it — "
                "a light page background alone does not excuse decoration directly behind the QR"
            )
        elif not _is_light_color(page_bg_color):
            assert has_quiet_zone, (
                f"QR '{qr.get('id')}' has no light page background (bg={page_bg_color!r}) and no "
                "quiet-zone rect behind it with >=8px padding"
            )

    # Foot elements (date/id) <= 16px font.
    for el in elements:
        if el.get("type") in ("completion_date", "certificate_id"):
            assert float(el.get("font_size", 0)) <= 16, (
                f"foot element '{el.get('id')}' font_size {el.get('font_size')} > 16px"
            )


# ---------------------------------------------------------------------------
# Seeder idempotency
# ---------------------------------------------------------------------------


class TestSeederIdempotency:
    def test_seed_creates_five_global_rows(self, db, make_user):
        make_user(role="admin")
        rows = seed(db)
        assert len(rows) == 5
        assert {r.post_title for r in rows} == EXPECTED_NAMES
        for r in rows:
            assert r.is_global is True
            assert r.post_status == "publish"
            assert r.post_name == ""
            assert r.certificate_width == 1123
            assert r.certificate_height == 794
            assert isinstance(r.elements_config, list) and len(r.elements_config) > 0

        total = db.query(Certificate).filter(Certificate.post_title.in_(EXPECTED_NAMES)).count()
        assert total == 5

    def test_seed_twice_is_idempotent(self, db, make_user):
        make_user(role="admin")
        seed(db)
        seed(db)
        total = db.query(Certificate).filter(Certificate.post_title.in_(EXPECTED_NAMES)).count()
        assert total == 5, "re-running the seeder must update in place, not duplicate rows"

    def test_seed_updates_elements_config_on_rerun(self, db, make_user):
        make_user(role="admin")
        rows1 = seed(db)
        ids_by_name = {r.post_title: r.id for r in rows1}
        rows2 = seed(db)
        for r in rows2:
            assert r.id == ids_by_name[r.post_title], "re-seeding must update the SAME row, not insert a new one"


# ---------------------------------------------------------------------------
# validate_elements_config verbatim
# ---------------------------------------------------------------------------


class TestValidatesAgainstDesignerSchema:
    @pytest.mark.parametrize("name,_desc,_bg,build", DESIGNS, ids=lambda v: v if isinstance(v, str) else "")
    def test_design_passes_validate_elements_config(self, name, _desc, _bg, build):
        raw = build()
        normalized = validate_elements_config(raw)
        assert len(normalized) == len(raw)
        # validate_elements_config never drops/rejects a well-formed element
        # from these designs — every type must round-trip.
        for el in normalized:
            assert el.get("type") in {
                "student_name", "course_name", "completion_date", "certificate_id",
                "instructor_name", "qr_code", "signature_image", "text", "image",
                "rect", "line",
            }


# ---------------------------------------------------------------------------
# Layout quality gates
# ---------------------------------------------------------------------------


class TestLayoutQualityGates:
    # DESIGNS tuples are (name, description, bg_color, build) — bg_color is
    # the template's page background_color, needed for the QR
    # light-background-OR-quiet-zone check.
    @pytest.mark.parametrize("name,_desc,bg_color,build", DESIGNS, ids=lambda v: v if isinstance(v, str) else "")
    def test_gates(self, name, _desc, bg_color, build):
        elements = validate_elements_config(build())
        assert_layout_gates(elements, width=1123, height=794, page_bg_color=bg_color)


# ---------------------------------------------------------------------------
# D-6 proof: the hardened frame-containment gate must FAIL on the OLD
# (pre-fix-round) Ivory Classic QR position, which punched through both
# border rules. This is a fixture reproducing that exact geometry — not a
# regression test on the current seeder — so it proves the gate helper
# itself has teeth, independent of whatever the current design happens to
# be.
# ---------------------------------------------------------------------------


class TestGateCatchesFrameCrossing:
    def test_old_ivory_classic_qr_position_fails_the_frame_gate(self):
        width, height = 1123, 794
        # Reproduces the exact pre-fix Ivory Classic border rects + QR
        # position: QR at (973, 664)-(1063, 754) crossed both the inner
        # rule (bottom=735) and the outer rule (bottom=746).
        elements = [
            {"id": "border-outer", "type": "rect", "x": 46, "y": 46,
             "width": width - 92, "height": height - 92, "z_index": 1,
             "background_color": None,
             "border": {"width": 2, "style": "solid", "color": "#c9a86a"}},
            {"id": "border-inner", "type": "rect", "x": 58, "y": 58,
             "width": width - 116, "height": height - 116, "z_index": 1,
             "background_color": None,
             "border": {"width": 1, "style": "solid", "color": "#c9a86a"}},
            {"id": "name", "type": "student_name", "x": 111.5, "y": 244,
             "width": 900, "height": 92, "font_size": 64},
            {"id": "qr", "type": "qr_code", "x": 973, "y": 664, "width": 90, "height": 90, "z_index": 10},
        ]
        with pytest.raises(AssertionError, match="not inside frame"):
            assert_layout_gates(elements, width=width, height=height, page_bg_color="#faf7f0")

    def test_qr_without_light_background_or_quiet_zone_fails(self):
        """A second, independent proof: a QR on a dark page background with
        no quiet-zone rect behind it must fail the contrast gate."""
        width, height = 1123, 794
        elements = [
            {"id": "name", "type": "student_name", "x": 100, "y": 100,
             "width": 900, "height": 92, "font_size": 64},
            {"id": "qr", "type": "qr_code", "x": 900, "y": 600, "width": 90, "height": 90, "z_index": 10},
        ]
        with pytest.raises(AssertionError, match="no light page background"):
            assert_layout_gates(elements, width=width, height=height, page_bg_color="#101726")

    def test_old_tamil_heritage_qr_on_lattice_fails_despite_light_page_bg(self):
        """Re-review proof (item 3): reproduces the exact pre-fix Tamil
        Heritage geometry — a light page background (#fdf8ee) that used to
        make the QR-contrast check short-circuit via `continue` BEFORE any
        decoration-overlap check ran, even though the QR's old position
        (y=660-740) visibly crossed the gold rule-bottom (y=722) and the
        bottom lattice band (starts y=732). The hardened gate must catch
        this: a light page background no longer excuses decoration
        directly behind/overlapping the QR."""
        width, height = 1123, 794
        elements = [
            {"id": "name", "type": "student_name", "x": 111.5, "y": 232,
             "width": 900, "height": 82, "font_size": 56},
            {"id": "rule-bottom", "type": "line", "x": 60, "y": height - 72,
             "width": width - 120, "height": 1, "z_index": 1, "font_color": "#c9932e"},
            {"id": "kolam-bottom-a-0", "type": "rect", "x": 700, "y": height - 28 - 20 - 14,
             "width": 20, "height": 20, "z_index": 1, "background_color": "#6d1a2d", "rotation": 45},
            # Old (buggy) QR position: y=660, bottom=740 — crosses both the
            # rule (y=722) and the lattice (starts y=732).
            {"id": "qr", "type": "qr_code", "x": 693, "y": 660, "width": 80, "height": 80, "z_index": 10},
        ]
        with pytest.raises(AssertionError, match="overlaps decorative element"):
            assert_layout_gates(elements, width=width, height=height, page_bg_color="#fdf8ee")


# ---------------------------------------------------------------------------
# Renders through build_certificate_html
# ---------------------------------------------------------------------------


class TestRendersToHtml:
    @pytest.mark.parametrize("name,_desc,bg,build", DESIGNS, ids=lambda v: v if isinstance(v, str) else "")
    def test_renders_without_raising_and_substitutes_name(self, name, _desc, bg, build):
        template = {
            "certificate_width": 1123,
            "certificate_height": 794,
            "background_color": bg,
            "background_image": "",
            "elements_config": validate_elements_config(build()),
        }
        values = sample_values()
        html_doc = build_certificate_html(template, values)
        assert "<html" in html_doc
        assert values["student_name"] in html_doc
        assert values["course_name"] in html_doc

    def test_all_five_designs_render_via_seeded_rows(self, db, make_user):
        make_user(role="admin")
        rows = seed(db)
        values = sample_values()
        for row in rows:
            html_doc = build_certificate_html(row, values)
            assert values["student_name"] in html_doc


# ---------------------------------------------------------------------------
# Fonts used are all curated
# ---------------------------------------------------------------------------


class TestFontsAreCurated:
    def test_every_font_family_is_curated(self):
        used_fonts = set()
        for _name, _desc, _bg, build in DESIGNS:
            for el in build():
                fam = (el.get("font_family") or "").strip()
                if fam:
                    used_fonts.add(fam)
        assert used_fonts, "no fonts found across designs"
        assert used_fonts.issubset(set(CURATED_FONTS.keys())), (
            f"non-curated fonts used: {used_fonts - set(CURATED_FONTS.keys())}"
        )

    def test_expected_font_pairings(self):
        elements_by_name = {name: build() for name, _desc, _bg, build in DESIGNS}

        def fonts_in(name):
            return {
                (el.get("font_family") or "").strip()
                for el in elements_by_name[name]
                if el.get("font_family")
            }

        assert fonts_in("Ivory Classic") == {"Cormorant Garamond", "Lora"}
        assert fonts_in("Midnight Gold") == {"DM Serif Display", "Inter"}
        assert fonts_in("Tamil Heritage") == {"Playfair Display", "Poppins"}
        assert fonts_in("Gradient Modern") == {"Outfit", "Inter"}
        assert fonts_in("Minimal Mono") == {"Space Grotesk"}
