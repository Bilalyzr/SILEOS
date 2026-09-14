"""Native virtual-lab config validation (2026-09-05).

Two templates ship, both graded by PARAMETERS (never gestures — sasha-ilo-
authoring doctrine), so a student on a phone (tier T4) can earn the same
marks as one with WebGL:

  reaction_lab — balance chemical equations. Config stores each reaction's
      species and the minimal balanced coefficient set. Validation PROVES the
      stored key is element-balanced (formula parser below) and in lowest
      terms, so an instructor cannot publish a wrong answer key.
  identify_lab — click the named structure on a labelled diagram (built-in
      'cell' / 'skeleton' SVGs, or any https image). Hotspots are percent
      coordinates (0-100) of the diagram box; success = hotspot id equality.

Same posture as app/schemas/game_config.py: extra="forbid" everywhere,
64KB serialized cap, per-string caps, max_score DERIVED never stored.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, StrictInt, validator

from app.schemas.concept_lab import ConceptLabConfig

LAB_TEMPLATES = {"reaction_lab", "identify_lab", "concept_lab"}
LAB_PROVIDERS = {"phet", "embed", "native"}
BUILTIN_DIAGRAMS = {"cell", "skeleton"}
MAX_LAB_CONFIG_BYTES = 64 * 1024
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,49}$")
HTTPS_RE = re.compile(r"^https://[^\s]+$")


class LabConfigError(ValueError):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class _Strict(BaseModel):
    class Config:
        extra = "forbid"


def _nonempty(v: str) -> str:
    s = v.strip()
    if not s:
        raise ValueError("must not be empty")
    return s


# ---- chemistry helpers ------------------------------------------------------

_ELEMENT_RE = re.compile(r"([A-Z][a-z]?)(\d*)")


def parse_formula(formula: str) -> Dict[str, int]:
    """'Ca(OH)2' -> {'Ca': 1, 'O': 2, 'H': 2}. Supports nested parentheses."""
    stack: List[Counter] = [Counter()]
    i = 0
    n = len(formula)
    while i < n:
        c = formula[i]
        if c == "(":
            stack.append(Counter())
            i += 1
        elif c == ")":
            if len(stack) == 1:
                raise ValueError(f"unbalanced ')' in {formula!r}")
            i += 1
            m = re.match(r"\d+", formula[i:])
            mult = int(m.group()) if m else 1
            i += len(m.group()) if m else 0
            top = stack.pop()
            for el, cnt in top.items():
                stack[-1][el] += cnt * mult
        else:
            m = _ELEMENT_RE.match(formula, i)
            if not m:
                raise ValueError(f"cannot parse {formula!r} at position {i}")
            el, num = m.group(1), m.group(2)
            stack[-1][el] += int(num) if num else 1
            i = m.end()
    if len(stack) != 1:
        raise ValueError(f"unbalanced '(' in {formula!r}")
    if not stack[0]:
        raise ValueError("empty formula")
    return dict(stack[0])


def element_totals(species: List["ReactionSpecies"], coefficients: List[int]) -> Dict[str, int]:
    totals: Counter = Counter()
    for sp, coef in zip(species, coefficients):
        for el, cnt in parse_formula(sp.formula).items():
            totals[el] += cnt * coef
    return dict(totals)


class ReactionSpecies(_Strict):
    formula: str = Field(..., min_length=1, max_length=40)
    name: str = Field(..., min_length=1, max_length=80)

    @validator("formula")
    def _formula_parses(cls, v):
        v = _nonempty(v)
        parse_formula(v)  # raises ValueError with a readable message
        return v

    @validator("name")
    def _name(cls, v):
        return _nonempty(v)


class Reaction(_Strict):
    reactants: List[ReactionSpecies] = Field(..., min_items=1, max_items=4)
    products: List[ReactionSpecies] = Field(..., min_items=1, max_items=4)
    # The minimal balanced coefficient set, reactants first then products.
    coefficients: List[StrictInt] = Field(..., min_items=2, max_items=8)
    hint: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=300)

    @validator("coefficients")
    def _balanced_and_lowest_terms(cls, v, values):
        reactants = values.get("reactants") or []
        products = values.get("products") or []
        if len(v) != len(reactants) + len(products):
            raise ValueError("coefficients must have one entry per species (reactants then products)")
        if any(c < 1 or c > 20 for c in v):
            raise ValueError("each coefficient must be between 1 and 20")
        left = element_totals(reactants, v[: len(reactants)])
        right = element_totals(products, v[len(reactants):])
        if left != right:
            raise ValueError(f"coefficients do not balance the equation (left {left}, right {right})")
        g = 0
        for c in v:
            g = math.gcd(g, c)
        if g != 1:
            raise ValueError("coefficients must be in lowest terms")
        return v


class ReactionLabConfig(_Strict):
    reactions: List[Reaction] = Field(..., min_items=1, max_items=20)
    intro: Optional[str] = Field(None, max_length=500)


class Hotspot(_Strict):
    id: str = Field(..., min_length=1, max_length=40)
    label: str = Field(..., min_length=1, max_length=80)
    x: float = Field(..., ge=0, le=100)
    y: float = Field(..., ge=0, le=100)
    description: Optional[str] = Field(None, max_length=300)

    @validator("id")
    def _id_slug(cls, v):
        v = _nonempty(v)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", v):
            raise ValueError("hotspot id must be lowercase letters, digits and dashes")
        return v

    @validator("label")
    def _label(cls, v):
        return _nonempty(v)


class IdentifyLabConfig(_Strict):
    # A built-in diagram key ('cell', 'skeleton') or an https image URL.
    diagram: str = Field(..., min_length=1, max_length=1000)
    hotspots: List[Hotspot] = Field(..., min_items=3, max_items=40)
    intro: Optional[str] = Field(None, max_length=500)

    @validator("diagram")
    def _diagram(cls, v):
        v = _nonempty(v)
        if v in BUILTIN_DIAGRAMS or HTTPS_RE.match(v):
            return v
        raise ValueError(f"diagram must be one of {sorted(BUILTIN_DIAGRAMS)} or an https image URL")

    @validator("hotspots")
    def _unique_ids(cls, v):
        ids = [h.id for h in v]
        if len(ids) != len(set(ids)):
            raise ValueError("hotspot ids must be unique")
        return v


TEMPLATE_SCHEMAS = {
    "concept_lab": ConceptLabConfig,
    "reaction_lab": ReactionLabConfig,
    "identify_lab": IdentifyLabConfig,
}


def validate_lab_config(template: str, config) -> dict:
    """Validate + normalize a native lab config. Raises LabConfigError."""
    if template not in LAB_TEMPLATES:
        raise LabConfigError(f"Unknown lab template '{template}'. Allowed: {sorted(LAB_TEMPLATES)}")
    if not isinstance(config, dict):
        raise LabConfigError("config must be a JSON object")
    try:
        serialized = json.dumps(config)
    except (TypeError, ValueError):
        raise LabConfigError("config is not JSON-serializable")
    if len(serialized.encode("utf-8")) > MAX_LAB_CONFIG_BYTES:
        raise LabConfigError(f"config exceeds the {MAX_LAB_CONFIG_BYTES} byte cap")
    try:
        parsed = TEMPLATE_SCHEMAS[template](**config)
    except ValueError as exc:  # pydantic ValidationError subclasses ValueError
        errors = getattr(exc, "errors", None)
        if callable(errors):
            first = errors()[0]
            loc = ".".join(str(p) for p in first["loc"])
            raise LabConfigError(f"Invalid config: {loc}: {first['msg']}")
        raise LabConfigError(f"Invalid config: {exc}")
    except TypeError:
        raise LabConfigError("Invalid config structure")
    return parsed.dict()


def derive_lab_max_score(template: str, config: dict) -> int:
    if template == 'concept_lab':
        return sum(s.get('points',0) for s in config.get('guided_steps',[])) if config.get('assessment_enabled') else 0
    """10 points per gradeable unit, derived — never stored."""
    if template == "reaction_lab":
        return 10 * len((config or {}).get("reactions") or [])
    if template == "identify_lab":
        return 10 * len((config or {}).get("hotspots") or [])
    return 0


# ---- catalog entry (admin create / import) -----------------------------------

class LabCatalogEntryIn(_Strict):
    slug: str
    title: str = Field(..., min_length=1, max_length=200)
    subject: str = Field("general", min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    provider: str = "embed"
    embed_url: Optional[str] = Field(None, max_length=1000)
    native_template: Optional[str] = None
    config: Optional[dict] = None
    attribution: Optional[str] = Field(None, max_length=300)
    thumbnail_url: Optional[str] = Field(None, max_length=1000)
    is_published: bool = True

    @validator("slug")
    def _slug(cls, v):
        v = v.strip().lower()
        if not SLUG_RE.match(v):
            raise ValueError("slug must be 2-50 chars of lowercase letters, digits and dashes")
        return v

    @validator("title", "subject")
    def _strip(cls, v):
        return _nonempty(v)

    @validator("provider")
    def _provider(cls, v):
        if v not in LAB_PROVIDERS:
            raise ValueError(f"provider must be one of {sorted(LAB_PROVIDERS)}")
        return v

    @validator("thumbnail_url")
    def _thumb(cls, v):
        if v is not None and not HTTPS_RE.match(v):
            raise ValueError("thumbnail_url must be https")
        return v

    def normalized(self) -> dict:
        """Cross-field rules + config validation. Returns a dict ready for
        the model. Raises LabConfigError."""
        d = self.dict()
        if d["provider"] == "native":
            if not d["native_template"]:
                raise LabConfigError("native labs need native_template")
            d["config"] = validate_lab_config(d["native_template"], d["config"])
            d["embed_url"] = None
        else:
            if d["provider"] == "phet" and not d["embed_url"]:
                d["embed_url"] = f"https://phet.colorado.edu/sims/html/{d['slug']}/latest/{d['slug']}_en.html"
            if not d["embed_url"] or not HTTPS_RE.match(d["embed_url"]):
                raise LabConfigError("embed labs need an https embed_url")
            d["native_template"] = None
            d["config"] = None
            if d["provider"] == "phet" and not d["attribution"]:
                d["attribution"] = "PhET Interactive Simulations, University of Colorado Boulder (CC-BY)"
        return d
