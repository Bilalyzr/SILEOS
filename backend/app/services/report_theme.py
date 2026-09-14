"""
Branded report styling for PDF exports.

Every generated report is built from the site's own identity — the Inter
typeface the frontend uses, the SashaInfinity orange/navy palette from
`tailwind.config.js`, and the logo — instead of reportlab's stock
Helvetica-on-blue defaults.

Each login gets a visually distinct report so a page can be identified at a
glance without reading it:

  * admin      — navy masthead band, orange rules, dense operational table
  * instructor — orange masthead band, navy rules, teaching-focused labels
  * student    — light masthead with a gradient rule, roomier rows
  * spoc       — deep teal masthead
  * company    — slate masthead

The palette and layout live here so the export router only decides *what* data
goes in the report, never how it looks.
"""
import os
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_FONT_DIR = os.path.join(_ASSETS_DIR, "fonts")

LOGO_PATH = os.path.join(_ASSETS_DIR, "sasha-logo.png")
# The logo is 440x299; keep that ratio wherever it is drawn.
LOGO_ASPECT = 299 / 440

BRAND = {
    "name": "SashaInfinity LMS",
    "website": "https://lms.sashainfinity.com",
    "legal": "SashaInfinity",
}

# Brand palette — mirrors tailwind.config.js (primary orange / secondary navy).
PALETTE = {
    "orange": "#f97316",
    "orange_dark": "#ea580c",
    "orange_soft": "#fff7ed",
    "navy": "#082a5e",
    "navy_soft": "#eef2f9",
    "teal": "#0f766e",
    "teal_soft": "#effcf9",
    "slate": "#334155",
    "slate_soft": "#f1f5f9",
    "ink": "#0f172a",
    "body": "#334155",
    "muted": "#64748b",
    "hairline": "#e2e8f0",
    "zebra": "#f8fafc",
}


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------

# Static Inter instances cut from the variable font the site ships. Resolved
# once per process; if the files are ever missing we degrade to Helvetica
# rather than failing the export.
_FONTS_REGISTERED: Optional[tuple] = None


def register_fonts() -> tuple:
    """Register Inter with reportlab. Returns (regular_name, bold_name)."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED is not None:
        return _FONTS_REGISTERED

    try:
        regular = os.path.join(_FONT_DIR, "Inter-Regular.ttf")
        bold = os.path.join(_FONT_DIR, "Inter-Bold.ttf")
        if not (os.path.exists(regular) and os.path.exists(bold)):
            raise FileNotFoundError(_FONT_DIR)

        pdfmetrics.registerFont(TTFont("Inter", regular))
        pdfmetrics.registerFont(TTFont("Inter-Bold", bold))
        # Lets <b> inside Paragraph markup resolve to the real bold cut.
        pdfmetrics.registerFontFamily(
            "Inter", normal="Inter", bold="Inter-Bold",
            italic="Inter", boldItalic="Inter-Bold",
        )
        _FONTS_REGISTERED = ("Inter", "Inter-Bold")
    except Exception:
        _FONTS_REGISTERED = ("Helvetica", "Helvetica-Bold")

    return _FONTS_REGISTERED


# --------------------------------------------------------------------------
# Per-role themes
# --------------------------------------------------------------------------

class ReportTheme:
    """Colours, copy and masthead layout for one login's reports."""

    def __init__(self, role: str, label: str, eyebrow: str, primary: str,
                 accent: str, tint: str, masthead: str,
                 header_text: str = "#ffffff", row_padding: int = 6,
                 body_size: int = 8):
        self.role = role
        self.label = label            # e.g. "Administrator Report"
        self.eyebrow = eyebrow        # small caps line above the title
        self.primary = colors.HexColor(primary)
        self.accent = colors.HexColor(accent)
        self.tint = colors.HexColor(tint)
        self.masthead = masthead      # "band" | "light"
        self.header_text = colors.HexColor(header_text)
        self.row_padding = row_padding
        self.body_size = body_size

    @property
    def table_header_bg(self):
        return self.primary

    @property
    def on_light(self):
        """Title colour when the masthead is a light background."""
        return self.primary


ROLE_THEMES = {
    "admin": ReportTheme(
        role="admin",
        label="Administrator Report",
        eyebrow="PLATFORM OPERATIONS",
        primary=PALETTE["navy"],
        accent=PALETTE["orange"],
        tint=PALETTE["navy_soft"],
        masthead="band",
    ),
    "instructor": ReportTheme(
        role="instructor",
        label="Instructor Report",
        eyebrow="TEACHING & COURSE PERFORMANCE",
        primary=PALETTE["orange"],
        accent=PALETTE["navy"],
        tint=PALETTE["orange_soft"],
        masthead="band",
    ),
    "student": ReportTheme(
        role="student",
        label="Learner Report",
        eyebrow="YOUR LEARNING JOURNEY",
        primary=PALETTE["orange_dark"],
        accent=PALETTE["navy"],
        tint=PALETTE["orange_soft"],
        masthead="light",
        # Students read their own report rather than scan it — give the rows air.
        row_padding=9,
        body_size=9,
    ),
    "spoc": ReportTheme(
        role="spoc",
        label="SPOC Report",
        eyebrow="COLLEGE PLACEMENT DESK",
        primary=PALETTE["teal"],
        accent=PALETTE["orange"],
        tint=PALETTE["teal_soft"],
        masthead="band",
    ),
    "company": ReportTheme(
        role="company",
        label="Company Report",
        eyebrow="INTERNSHIP PROGRAMME",
        primary=PALETTE["slate"],
        accent=PALETTE["orange"],
        tint=PALETTE["slate_soft"],
        masthead="band",
    ),
}


def get_theme(role: Optional[str]) -> ReportTheme:
    return ROLE_THEMES.get((role or "admin").lower(), ROLE_THEMES["admin"])


# --------------------------------------------------------------------------
# Page furniture
# --------------------------------------------------------------------------

def make_page_decorator(theme: ReportTheme, subtitle: str = ""):
    """Build the onPage callback that paints the masthead and footer.

    Drawn on the canvas rather than as flowables so it repeats on every page
    and never competes with the table for vertical space.
    """
    regular, bold = register_fonts()

    def decorate(canvas, doc):
        canvas.saveState()
        width, height = doc.pagesize

        band_h = 0.62 * inch

        if theme.masthead == "band":
            canvas.setFillColor(theme.primary)
            canvas.rect(0, height - band_h, width, band_h, stroke=0, fill=1)
            text_color = theme.header_text
        else:
            canvas.setFillColor(colors.white)
            canvas.rect(0, height - band_h, width, band_h, stroke=0, fill=1)
            text_color = theme.primary

        # Accent rule directly under the masthead — the one element that most
        # distinguishes the three report designs at a glance.
        canvas.setFillColor(theme.accent)
        canvas.rect(0, height - band_h - 3, width, 3, stroke=0, fill=1)

        # Logo, left.
        logo_h = 0.34 * inch
        logo_w = logo_h / LOGO_ASPECT
        if os.path.exists(LOGO_PATH):
            try:
                canvas.drawImage(
                    LOGO_PATH, 0.45 * inch, height - band_h + (band_h - logo_h) / 2,
                    width=logo_w, height=logo_h, mask="auto",
                    preserveAspectRatio=True, anchor="w",
                )
            except Exception:
                pass

        text_x = 0.45 * inch + logo_w + 0.18 * inch
        canvas.setFillColor(text_color)
        canvas.setFont(bold, 12)
        canvas.drawString(text_x, height - band_h + 0.30 * inch, BRAND["name"])
        canvas.setFont(regular, 8)
        canvas.drawString(text_x, height - band_h + 0.16 * inch, theme.label)

        # Right-hand slot: what this report covers.
        if subtitle:
            canvas.setFont(regular, 8)
            canvas.drawRightString(width - 0.45 * inch, height - band_h + 0.30 * inch, subtitle)

        # Footer.
        canvas.setFillColor(colors.HexColor(PALETTE["hairline"]))
        canvas.rect(0.45 * inch, 0.48 * inch, width - 0.9 * inch, 0.5, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor(PALETTE["muted"]))
        canvas.setFont(regular, 7.5)
        canvas.drawString(0.45 * inch, 0.33 * inch, f"{BRAND['legal']} · {BRAND['website']}")
        canvas.drawRightString(width - 0.45 * inch, 0.33 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    return decorate


def top_margin_for(theme: ReportTheme) -> float:
    """Space the masthead needs, so flowables start below it."""
    return 0.95 * inch
