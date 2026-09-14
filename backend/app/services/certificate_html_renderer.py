"""Certificate HTML renderer — turns a `Certificate.elements_config` design
into a complete, self-contained HTML document that IS the production render
path for builder-designed certificates (Task 6 of the Learning Experience
plan, spec section C items 1/2/6).

This module is pure and DB-free: `build_certificate_html` takes a plain dict
snapshot of the template's design columns + a `values` dict and returns an
HTML string. It never touches the database, so it is fully unit-testable and
reusable from both the issuance/render path (certificate_service.py) and the
instructor designer preview endpoint (routers/certificate_designer.py).

Element types (schemas/certificate.py TemplateElementType extended by this
task): student_name, course_name, completion_date, certificate_id,
instructor_name, qr_code, signature_image, text, image, rect, line.

Every substituted value is HTML-escaped — the rendered page is served
publicly (verify-certificate) and can be printed via headless Chrome, so a
student/instructor display_name or course title must never be able to inject
markup (stored-XSS vector), matching the sentinel-substitution path's
existing `_esc()` discipline in routers/certificates.py.
"""
from __future__ import annotations

import base64
import html
import io
import logging
import posixpath
import re
import urllib.parse
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security allowlists (fix round: H-1/H-2/L-1/L-2).
#
# This module renders into a document that headless Chrome navigates to via
# `file://` with `--no-sandbox` (see certificate_service._render_local_html_
# pdf_via_chrome) — that combination grants the renderer filesystem access,
# so an unconstrained `src`/CSS value on an instructor-authored (or
# admin/global) template is a server-side SSRF/LFI primitive, not just a
# client-side concern. Every value below is validated at BOTH write time
# (routers/certificate_designer.validate_elements_config) and render time
# (this module — rows created before validation existed, or written by any
# other path, must not get a free pass).
# ---------------------------------------------------------------------------

# No configured external asset-host list exists yet, so the simplest safe
# policy is same-origin static paths + inline data URIs only. file://, blob:,
# and arbitrary http(s) are rejected outright.
_SAFE_PATH_PREFIXES = ("/uploads/", "/certificate-files/")
_DATA_URI_RE = re.compile(r"^data:image/(?:png|jpeg|jpg|gif|webp);base64,")

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_RGBA_COLOR_RE = re.compile(r"^rgba?\([\d.,\s%]+\)$")
_NAMED_COLOR_RE = re.compile(r"^[a-z]{2,20}$")
_FONT_WEIGHT_RE = re.compile(r"^(normal|bold|[1-9]00)$")
_BORDER_STYLE_RE = re.compile(r"^(solid|dashed|dotted)$")

_MAX_UNQUOTE_ROUNDS = 10  # loop-until-stable ceiling for percent-decoding


def _fully_unquote(value: str) -> Optional[str]:
    """Percent-decode `value` repeatedly until it stops changing (defeats
    double/triple encoding like %252e), or return None if it never
    stabilizes within `_MAX_UNQUOTE_ROUNDS` rounds — treated as unsafe rather
    than looping forever on adversarial input."""
    current = value
    for _ in range(_MAX_UNQUOTE_ROUNDS):
        decoded = urllib.parse.unquote(current)
        if decoded == current:
            return current
        current = decoded
    return None


def is_safe_asset_src(src: Optional[str]) -> bool:
    """True when `src` is safe to emit into an `src`/`url()` value: a
    same-origin static path (/uploads/..., /certificate-files/...) or an
    inline `data:image/...;base64,` URI. Rejects file://, blob://, and any
    http(s) (external) URL outright — see the module-level note above.

    Path-type sources (fix round NEW-1) are normalized and RE-ASSERTED
    before being trusted — a prefix-anchored regex alone is not enough,
    since "/uploads/../../../../etc/passwd" starts with "/uploads/" but
    resolves outside it once the OS/browser walks the ".." segments (proven:
    both the file:// document base Chrome renders from, and ReportLab's
    os.path.join in _load_image_reader, would happily walk out of the
    uploads dir). The steps below close that:
      1. reject backslashes outright (never part of a legitimate URL path,
         and some parsers treat them as path separators)
      2. percent-decode repeatedly until stable (defeats %2e%2e, %252e, a
         literal ".." mixed with an encoded one, etc.) — decoding to
         something that still contains a raw "%" (never fully decodes) is
         rejected rather than guessed at
      3. reject any ".." path segment in the decoded form, belt-and-braces
         before normalization even runs
      4. posixpath.normpath the decoded path and re-check it STILL starts
         with an allowed prefix — normalization alone can't be trusted
         either (it doesn't know the string was a URL vs a filesystem path),
         so both the segment check and the post-normalize prefix check apply
    The data:image/... branch is unchanged — it carries no path to traverse.
    """
    if not src or not isinstance(src, str):
        return False
    s = src.strip()

    if _DATA_URI_RE.match(s):
        return True

    if not s.startswith(_SAFE_PATH_PREFIXES):
        return False

    if "\\" in s:
        return False

    decoded = _fully_unquote(s)
    if decoded is None or "%" in decoded:
        return False

    if ".." in decoded.split("/"):
        return False

    normalized = posixpath.normpath(decoded)
    # normpath collapses "/uploads/x/../y" to "/uploads/y" for a segment
    # that stays inside, but "/uploads/../etc" collapses to "/etc" — the
    # prefix re-check below is what actually catches an escape; the segment
    # check above is defense in depth for exotic inputs normpath might
    # handle differently (e.g. it does NOT strip a leading "..").
    if not normalized.startswith(_SAFE_PATH_PREFIXES):
        return False

    return True


def validate_color(value: Optional[str]) -> Optional[str]:
    """Return `value` unchanged if it's a safe CSS color (hex / rgb(a) /
    a short lowercase keyword), else None. Never returns anything that could
    carry a CSS injection (`;`, `url(`, `expression(`, etc.) — the allowlist
    makes those categorically impossible rather than trying to blocklist them."""
    if not value or not isinstance(value, str):
        return None
    v = value.strip()
    if _HEX_COLOR_RE.match(v) or _RGBA_COLOR_RE.match(v) or _NAMED_COLOR_RE.match(v.lower()):
        return v
    return None


def validate_font_weight(value: Optional[str]) -> str:
    """Normalize to 'normal' | 'bold' | a CSS numeric weight (100-900), or
    fall back to 'normal' for anything else."""
    if not value or not isinstance(value, str):
        return "normal"
    v = value.strip().lower()
    return v if _FONT_WEIGHT_RE.match(v) else "normal"


def validate_letter_spacing(value: Any) -> Optional[str]:
    """Emit a numeric letter-spacing as `{x}px`, or None for anything that
    doesn't parse as a plain finite number (never echo the raw string into
    CSS). `float("inf")`/`float("nan")` parse without raising but are not
    valid CSS lengths — rejected explicitly rather than formatted as
    "infpx"/"nanpx" (mirrors validate_border's NEW-2 finite check)."""
    if value in (None, ""):
        return None
    try:
        import math

        spacing = float(value)
        if not math.isfinite(spacing):
            return None
        return f"{spacing}px"
    except (TypeError, ValueError, OverflowError):
        return None


def validate_border(value: Any) -> Optional[str]:
    """Decompose a border spec into `{width}px {style} {color}` from
    validated parts, or return None if it doesn't parse into that shape.

    Accepts either a dict `{width, style, color}` (the designer's native
    shape) or a plain string "Npx solid #hex" (legacy shape) — in both cases
    every component is re-validated and re-emitted from scratch; the raw
    string is never echoed back into the stylesheet.
    """
    width = style = color = None
    if isinstance(value, dict):
        width = value.get("width")
        style = value.get("style")
        color = value.get("color")
    elif isinstance(value, str):
        parts = value.strip().split()
        for part in parts:
            if part.endswith("px"):
                width = part[:-2]
            elif part.lower() in ("solid", "dashed", "dotted"):
                style = part.lower()
            else:
                maybe_color = validate_color(part)
                if maybe_color:
                    color = maybe_color
    else:
        return None

    try:
        import math

        width_f = float(width)
        if not math.isfinite(width_f):
            # "infpx" / "-infpx" / "nanpx" parse fine as float() but blow up
            # int() with OverflowError ("nan"/"inf" -> int) or produce a
            # meaningless value — reject before it ever reaches int().
            return None
        width_i = int(width_f)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (0 <= width_i <= 20):
        return None

    style_v = (style or "solid").strip().lower() if isinstance(style, str) else "solid"
    if not _BORDER_STYLE_RE.match(style_v):
        return None

    color_v = validate_color(color) or "#000000"

    return f"{width_i}px {style_v} {color_v}"

# ---------------------------------------------------------------------------
# Curated font list (plan Task 6 binding — "tasteful pairs").
#
# Every font here is loaded from Google Fonts via a single <link> in the
# rendered document. `_GOOGLE_FONTS_FAMILIES` is the exact query-string
# fragment; `CURATED_FONTS` is the public list the designer API validates
# against (routers/certificate_designer.py) and the frontend font picker can
# consume. Falls back to a safe system font stack when a template names a
# font outside this list, rather than silently loading an arbitrary
# attacker-controlled Google Fonts family name.
# ---------------------------------------------------------------------------
CURATED_FONTS: Dict[str, Dict[str, str]] = {
    "Playfair Display": {"category": "serif", "weights": "400;500;600;700;800;900"},
    "Cormorant Garamond": {"category": "serif", "weights": "400;500;600;700"},
    "Great Vibes": {"category": "script", "weights": "400"},
    "Space Grotesk": {"category": "sans-serif", "weights": "400;500;600;700"},
    "Sora": {"category": "sans-serif", "weights": "400;500;600;700;800"},
    "Poppins": {"category": "sans-serif", "weights": "400;500;600;700;800"},
    "Inter": {"category": "sans-serif", "weights": "400;500;600;700;800"},
    "Lora": {"category": "serif", "weights": "400;500;600;700"},
    "Montserrat": {"category": "sans-serif", "weights": "400;500;600;700;800"},
    "DM Serif Display": {"category": "serif", "weights": "400"},
    "Crimson Pro": {"category": "serif", "weights": "400;500;600;700"},
    "Outfit": {"category": "sans-serif", "weights": "400;500;600;700;800"},
}

# The font every element falls back to when its declared font_family is not
# in the curated list (e.g. legacy "Arial"/"Helvetica" rows, or a value the
# designer API rejected but which still needs SOME render). System stack —
# no Google Fonts request, always available.
_FALLBACK_FONT_FAMILY = "Inter"
_FALLBACK_FONT_STACK = (
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)

_ELEMENT_TYPES = {
    "student_name",
    "course_name",
    "completion_date",
    "certificate_id",
    "instructor_name",
    "qr_code",
    "signature_image",
    "text",
    "image",
    "rect",
    "line",
}

MAX_ELEMENTS = 100


def sample_values(secure_certificate_id: str = "PREVIEW-0000000000") -> Dict[str, str]:
    """Sample token values for a designer preview — never real student data.

    `verify_url` is a placeholder that still LOOKS like a real verify link so
    the QR code paints something representative in the preview.
    """
    return {
        "student_name": "Jordan Alexis Rivera",
        "course_name": "Full-Stack Web Development Mastery",
        "completion_date": "September 2, 2026",
        "certificate_id": secure_certificate_id,
        "instructor_name": "Dr. Elena Whitfield",
        "verify_url": f"https://lms.sashainfinity.com/verify-certificate/{secure_certificate_id}",
    }


def _esc(value: Optional[str]) -> str:
    """HTML-escape a value before it lands in the rendered page.

    Mirrors routers/certificates.py's `_esc()` — quote=True so values are
    also safe inside HTML attributes, not just text nodes.
    """
    return html.escape(value if value is not None else "", quote=True)


def _font_family_css(family: Optional[str]) -> str:
    """CSS font-family value for an element, with the curated-list fallback."""
    fam = (family or "").strip()
    if fam in CURATED_FONTS:
        return f"'{fam}', {_fallback_stack_for(fam)}"
    return _FALLBACK_FONT_STACK


def _fallback_stack_for(family: str) -> str:
    category = CURATED_FONTS.get(family, {}).get("category", "sans-serif")
    if category == "serif":
        return "Georgia, 'Times New Roman', serif"
    if category == "script":
        return "cursive"
    return "Helvetica, Arial, sans-serif"


def _google_fonts_link_href(families: Optional[List[str]] = None) -> str:
    """Build the Google Fonts stylesheet URL for the curated families
    actually used (or all curated fonts when `families` is None — used by
    the designer's live font picker so every font is available to preview)."""
    chosen = families if families is not None else list(CURATED_FONTS.keys())
    parts = []
    for fam in chosen:
        spec = CURATED_FONTS.get(fam)
        if not spec:
            continue
        name = fam.replace(" ", "+")
        parts.append(f"family={name}:wght@{spec['weights']}")
    if not parts:
        return ""
    return "https://fonts.googleapis.com/css2?" + "&".join(parts) + "&display=swap"


def _generate_qr_data_uri(data: str, box_size: int = 8, border: int = 2) -> Optional[str]:
    """Render a QR code of `data` and return it as an embedded PNG data URI.

    Returns None (rather than raising) if the qrcode/PIL libs are missing or
    generation fails for any reason — a broken QR must never take down the
    whole certificate render.
    """
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        logger.warning("certificate_html_renderer: QR generation failed", exc_info=True)
        return None


def _resolve_text(el: Dict[str, Any], values: Dict[str, str]) -> str:
    etype = el.get("type")
    if etype == "student_name":
        return values.get("student_name", "")
    if etype == "course_name":
        return values.get("course_name", "")
    if etype == "completion_date":
        return values.get("completion_date", "")
    if etype == "certificate_id":
        return values.get("certificate_id", "")
    if etype == "instructor_name":
        return values.get("instructor_name", "")
    if etype == "text":
        return el.get("content") or ""
    return ""


def _num(el: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(el.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _element_css(el: Dict[str, Any]) -> str:
    """Absolute-positioning + rotation CSS shared by every element type."""
    x = _num(el, "x")
    y = _num(el, "y")
    w = _num(el, "width", 100)
    h = _num(el, "height", 40)
    rotation = _num(el, "rotation", 0)
    z = int(_num(el, "z_index", 0))

    transform = f" transform: rotate({rotation}deg);" if rotation else ""
    return (
        f"position:absolute; left:{x}px; top:{y}px; width:{w}px; height:{h}px; "
        f"z-index:{z};{transform}"
    )


def _render_text_element(el: Dict[str, Any], values: Dict[str, str]) -> str:
    text = _resolve_text(el, values)
    if not text and el.get("type") not in ("text",):
        # Typed token with nothing to show (e.g. missing value) — render
        # nothing rather than a stray empty positioned div.
        return ""

    font_family_css = _font_family_css(el.get("font_family"))
    font_size = _num(el, "font_size", 24)
    color = validate_color(el.get("font_color")) or "#000000"
    weight = validate_font_weight(el.get("font_weight"))
    align = (el.get("text_align") or "left").lower()
    if align not in ("left", "center", "right"):
        align = "left"
    letter_spacing = validate_letter_spacing(el.get("letter_spacing"))
    ls_css = f" letter-spacing:{letter_spacing};" if letter_spacing else ""
    bg = validate_color(el.get("background_color"))
    bg_css = f" background-color:{bg};" if bg else ""
    border = validate_border(el.get("border"))
    border_css = f" border:{border};" if border else ""

    justify = {"left": "flex-start", "center": "center", "right": "flex-end"}.get(align, "flex-start")

    style = (
        _element_css(el)
        + f" display:flex; align-items:center; justify-content:{justify}; "
        f"font-family:{font_family_css}; font-size:{font_size}px; color:{color}; "
        f"font-weight:{weight}; text-align:{align};{ls_css}{bg_css}{border_css} "
        "white-space:pre-wrap; overflow-wrap:break-word;"
    )
    return f'<div class="cert-el cert-el-text" style="{style}">{_esc(text)}</div>'


def _render_image_element(el: Dict[str, Any]) -> str:
    src = el.get("image_url") or el.get("src") or ""
    if not is_safe_asset_src(src):
        # H-1: file://, blob:, and external http(s) sources are dropped —
        # render continues without this element rather than emitting an
        # unsafe src (a Chrome navigation to file:// with --no-sandbox has
        # filesystem access; an external URL is an SSRF/beacon primitive).
        if src:
            logger.warning("certificate_html_renderer: dropped image element with unsafe src")
        return ""
    style = _element_css(el) + " object-fit:contain;"
    return f'<img class="cert-el cert-el-image" src="{_esc(src)}" style="{style}" alt="" />'


def _render_signature_element(el: Dict[str, Any]) -> str:
    src = el.get("image_url") or el.get("src") or ""
    if not is_safe_asset_src(src):
        if src:
            logger.warning("certificate_html_renderer: dropped signature element with unsafe src")
        return ""
    style = _element_css(el) + " object-fit:contain;"
    return f'<img class="cert-el cert-el-signature" src="{_esc(src)}" style="{style}" alt="Signature" />'


def _render_rect_element(el: Dict[str, Any]) -> str:
    fill = validate_color(el.get("background_color")) or validate_color(el.get("fill")) or "transparent"
    border = validate_border(el.get("border"))
    radius = _num(el, "border_radius", 0)
    if not (0 <= radius <= 1000):
        radius = 0
    border_css = f" border:{border};" if border else ""
    style = (
        _element_css(el)
        + f" background-color:{fill};{border_css} border-radius:{radius}px;"
    )
    return f'<div class="cert-el cert-el-rect" style="{style}"></div>'


def _render_line_element(el: Dict[str, Any]) -> str:
    color = validate_color(el.get("font_color")) or validate_color(el.get("line_color")) or "#000000"
    thickness = _num(el, "line_thickness", 2) or 2
    if not (0 <= thickness <= 100):
        thickness = 2
    style = _element_css(el) + f" border-top:{thickness}px solid {color};"
    return f'<div class="cert-el cert-el-line" style="{style}"></div>'


def _render_qr_element(el: Dict[str, Any], values: Dict[str, str]) -> str:
    verify_url = values.get("verify_url") or ""
    if not verify_url:
        return ""
    w = _num(el, "width", 120)
    box_size = max(2, min(12, int(w // 25) or 8))
    data_uri = _generate_qr_data_uri(verify_url, box_size=box_size)
    if not data_uri:
        return ""
    style = _element_css(el)
    return f'<img class="cert-el cert-el-qr" src="{data_uri}" style="{style}" alt="Verification QR code" />'


def _render_element(el: Dict[str, Any], values: Dict[str, str]) -> str:
    etype = el.get("type")
    if etype in ("student_name", "course_name", "completion_date", "certificate_id", "instructor_name", "text"):
        return _render_text_element(el, values)
    if etype == "image":
        return _render_image_element(el)
    if etype == "signature_image":
        return _render_signature_element(el)
    if etype == "rect":
        return _render_rect_element(el)
    if etype == "line":
        return _render_line_element(el)
    if etype == "qr_code":
        return _render_qr_element(el, values)
    return ""


def build_certificate_html(
    template: Any,
    values: Dict[str, str],
    *,
    font_families_hint: Optional[List[str]] = None,
) -> str:
    """Build a complete, self-contained HTML document for a certificate.

    `template` may be a `Certificate` ORM row or any object/dict exposing the
    same attributes: certificate_width, certificate_height, background_color,
    background_image, elements_config.

    `values` supplies the typed-token substitutions:
      student_name, course_name, completion_date, certificate_id,
      instructor_name, verify_url (used for the qr_code element).
    Use `sample_values()` for a designer preview.

    Every element is absolute-positioned inside a fixed-size page div sized
    from certificate_width/height, with print CSS pinning the PDF page to
    those exact dimensions (so headless Chrome's print-to-PDF reproduces the
    canvas 1:1, matching the designer's on-screen layout).
    """

    def _get(name: str, default=None):
        if isinstance(template, dict):
            return template.get(name, default)
        return getattr(template, name, default)

    width = int(_get("certificate_width", 1400) or 1400)
    height = int(_get("certificate_height", 1080) or 1080)
    bg_color = _get("background_color", "#ffffff") or "#ffffff"
    bg_image = _get("background_image", "") or ""
    elements = _get("elements_config", []) or []
    if not isinstance(elements, list):
        elements = []

    used_fonts = set()
    for el in elements:
        if not isinstance(el, dict):
            continue
        fam = (el.get("font_family") or "").strip()
        if fam in CURATED_FONTS:
            used_fonts.add(fam)
    if font_families_hint:
        used_fonts.update(f for f in font_families_hint if f in CURATED_FONTS)
    if not used_fonts:
        used_fonts.add(_FALLBACK_FONT_FAMILY)

    fonts_href = _google_fonts_link_href(sorted(used_fonts))
    fonts_link = (
        f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="{_esc(fonts_href)}" rel="stylesheet">\n'
        if fonts_href
        else ""
    )

    safe_bg_color = validate_color(bg_color) or "#ffffff"
    bg_style = f"background-color:{safe_bg_color};"
    if bg_image and is_safe_asset_src(bg_image):
        bg_style += (
            f" background-image:url('{_esc(bg_image)}'); background-size:cover; "
            "background-position:center; background-repeat:no-repeat;"
        )
    elif bg_image:
        logger.warning("certificate_html_renderer: dropped background_image with unsafe src")

    # Sort by z-index so paint order matches the designer's layers panel.
    ordered = sorted(
        [el for el in elements if isinstance(el, dict) and el.get("type") in _ELEMENT_TYPES],
        key=lambda e: _num(e, "z_index", 0),
    )
    elements_html = "\n".join(_render_element(el, values) for el in ordered)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Certificate</title>
{fonts_link}<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ background: #f0f0f0; }}
  #cert-page {{
    position: relative;
    width: {width}px;
    height: {height}px;
    overflow: hidden;
    {bg_style}
    margin: 0 auto;
  }}
  .cert-el {{ box-sizing: border-box; }}
  @page {{
    size: {width}px {height}px;
    margin: 0;
  }}
  @media print {{
    html, body {{
      background: #ffffff;
      margin: 0;
      padding: 0;
      width: {width}px;
      height: {height}px;
    }}
    #cert-page {{
      margin: 0;
      box-shadow: none;
    }}
    * {{
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      color-adjust: exact !important;
    }}
  }}
</style>
</head>
<body>
  <div id="cert-page">
{elements_html}
  </div>
</body>
</html>"""
