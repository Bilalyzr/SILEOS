"""HTML and CSS challenges: check definitions and value comparison.

A web challenge's test case stores a *check* as JSON in `input_text`, for example
  {"kind": "css", "selector": "h1", "property": "color"}
and the expected value in `expected_output`. The judge worker renders the
learner's page in a headless browser (page scripts off, network blocked), reads
the value the check asks for, and returns it as the case's output. The backend
then compares it with the expected value like any other test.

Check kinds:
  exists  -> "true" or "false"
  count   -> number of elements matching the selector
  text    -> text of the first match, trimmed, inner whitespace collapsed
  attr    -> attribute value of the first match ("attribute" required)
  css     -> computed style of the first match ("property" required)
"""

from __future__ import annotations

import json
import re


WEB_LANGUAGES = frozenset({"html", "css"})
CHECK_KINDS = ("exists", "count", "text", "attr", "css")
MAX_SELECTOR = 500
_PROPERTY = re.compile(r"^-{0,2}[a-z][a-z0-9-]{0,63}$")
_ATTRIBUTE = re.compile(r"^[A-Za-z_:][A-Za-z0-9_.:-]{0,63}$")


def is_web(languages) -> bool:
    return bool(set(languages) & WEB_LANGUAGES)


def parse_check(text: str) -> dict:
    """Return a normalised check, or raise ValueError with a message an instructor can act on."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        raise ValueError("Each HTML/CSS test must be a check (kind and selector).") from None
    if not isinstance(data, dict):
        raise ValueError("Each HTML/CSS test must be a check (kind and selector).")
    kind = data.get("kind")
    if kind not in CHECK_KINDS:
        raise ValueError(f"Check kind must be one of: {', '.join(CHECK_KINDS)}.")
    selector = str(data.get("selector", "")).strip()
    if not selector or len(selector) > MAX_SELECTOR:
        raise ValueError("Each check needs a CSS selector (up to 500 characters).")
    check = {"kind": kind, "selector": selector}
    if kind == "css":
        prop = str(data.get("property", "")).strip().lower()
        if not _PROPERTY.match(prop):
            raise ValueError("A style check needs a CSS property name, for example color.")
        check["property"] = prop
    if kind == "attr":
        attribute = str(data.get("attribute", "")).strip()
        if not _ATTRIBUTE.match(attribute):
            raise ValueError("An attribute check needs an attribute name, for example href.")
        check["attribute"] = attribute
    return check


# Colours: browsers report computed colours as rgb()/rgba(), but instructors
# usually write hex or names. Both sides are converted before comparing.
_NAMED = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "lime": (0, 255, 0), "blue": (0, 0, 255),
    "yellow": (255, 255, 0), "orange": (255, 165, 0), "purple": (128, 0, 128),
    "rebeccapurple": (102, 51, 153), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "silver": (192, 192, 192), "navy": (0, 0, 128), "teal": (0, 128, 128),
    "maroon": (128, 0, 0), "olive": (128, 128, 0), "aqua": (0, 255, 255),
    "cyan": (0, 255, 255), "fuchsia": (255, 0, 255), "magenta": (255, 0, 255),
    "pink": (255, 192, 203), "brown": (165, 42, 42),
}
_HEX = re.compile(r"#([0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{4}|[0-9a-f]{3})\b")
_RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([0-9.]+)\s*)?\)")
_WORD = re.compile(r"\b[a-z]+\b")


def _rgb(r: int, g: int, b: int, alpha: float | None = None) -> str:
    if alpha is None or alpha >= 1:
        return f"rgb({r}, {g}, {b})"
    return f"rgba({r}, {g}, {b}, {round(alpha, 3):g})"


def _hex(match: re.Match) -> str:
    digits = match.group(1)
    if len(digits) in (3, 4):
        digits = "".join(ch * 2 for ch in digits)
    r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
    alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else None
    return _rgb(r, g, b, alpha)


def normalize_css_value(value: str) -> str:
    text = " ".join(value.strip().lower().split())
    if text == "transparent":
        return "rgba(0, 0, 0, 0)"
    text = _HEX.sub(_hex, text)
    text = _RGB.sub(lambda m: _rgb(int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4)) if m.group(4) else None), text)
    return _WORD.sub(lambda m: _rgb(*_NAMED[m.group(0)]) if m.group(0) in _NAMED else m.group(0), text)
