"""Virtual labs — catalog + native lab results (2026-09-05 content libraries).

The catalog is the union of BUILTIN_LABS (constants below: PhET sims plus
the native labs we ship) and admin-curated rows in `virtual_lab_catalog`
(see app/routers/content_library_admin.py). A DB row with the same slug as
a built-in OVERRIDES it, so admins can retitle/unpublish shipped labs.

Instructors attach a lab by slug (lesson content type 'virtual_lab',
`lessons.virtual_lab_sim`); the courses.py resolver calls is_valid_lab_slug().

Providers: 'phet' / 'embed' render as iframes in the player; 'native' labs
(reaction_lab, identify_lab) are rendered by our own engines and POST an
advisory score here — same doctrine as games: client-graded, XP best-effort,
never gradebook truth.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.content_library import VirtualLabCatalog, VirtualLabResult
from app.schemas.lab_config import derive_lab_max_score
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()

PHET_BASE = "https://phet.colorado.edu/sims/html/{sim}/latest/{sim}_en.html"
PHET_ATTRIBUTION = "PhET Interactive Simulations, University of Colorado Boulder (CC-BY)"
SASHA_ATTRIBUTION = "SashaInfinity native lab"


def lab_embed_url(sim: str) -> str:
    return PHET_BASE.format(sim=sim)


def _phet(slug: str, title: str, subject: str, description: str = "") -> dict:
    return {
        "slug": slug, "title": title, "subject": subject, "provider": "phet",
        "embed_url": lab_embed_url(slug), "attribution": PHET_ATTRIBUTION,
        "description": description, "native_template": None, "config": None,
    }


# ---- native lab configs (single source of truth for hotspot coordinates;
# the frontend diagrams are drawn on a 0-100 x 0-100 viewBox to match) ----

REACTION_LAB_BASICS = {
    "intro": "Balance each equation by choosing the smallest whole-number coefficients. "
             "Atoms are never created or destroyed — count each element on both sides.",
    "reactions": [
        {"reactants": [{"formula": "H2", "name": "hydrogen"}, {"formula": "O2", "name": "oxygen"}],
         "products": [{"formula": "H2O", "name": "water"}],
         "coefficients": [2, 1, 2], "hint": "Count oxygen atoms first.",
         "description": "Synthesis of water — the classic first equation."},
        {"reactants": [{"formula": "CH4", "name": "methane"}, {"formula": "O2", "name": "oxygen"}],
         "products": [{"formula": "CO2", "name": "carbon dioxide"}, {"formula": "H2O", "name": "water"}],
         "coefficients": [1, 2, 1, 2], "hint": "Balance carbon, then hydrogen, then oxygen.",
         "description": "Complete combustion of methane (cooking gas)."},
        {"reactants": [{"formula": "Fe", "name": "iron"}, {"formula": "O2", "name": "oxygen"}],
         "products": [{"formula": "Fe2O3", "name": "iron(III) oxide"}],
         "coefficients": [4, 3, 2], "hint": "Oxygen comes in pairs; the oxide needs three.",
         "description": "Rusting of iron."},
        {"reactants": [{"formula": "N2", "name": "nitrogen"}, {"formula": "H2", "name": "hydrogen"}],
         "products": [{"formula": "NH3", "name": "ammonia"}],
         "coefficients": [1, 3, 2], "hint": "Two ammonia molecules use up one N2.",
         "description": "The Haber process — fertiliser for the world."},
        {"reactants": [{"formula": "Na", "name": "sodium"}, {"formula": "Cl2", "name": "chlorine"}],
         "products": [{"formula": "NaCl", "name": "sodium chloride"}],
         "coefficients": [2, 1, 2], "hint": "Chlorine gas is diatomic.",
         "description": "Formation of table salt."},
        {"reactants": [{"formula": "C3H8", "name": "propane"}, {"formula": "O2", "name": "oxygen"}],
         "products": [{"formula": "CO2", "name": "carbon dioxide"}, {"formula": "H2O", "name": "water"}],
         "coefficients": [1, 5, 3, 4], "hint": "Three carbons, eight hydrogens — do oxygen last.",
         "description": "Combustion of propane (LPG)."},
        {"reactants": [{"formula": "Mg", "name": "magnesium"}, {"formula": "HCl", "name": "hydrochloric acid"}],
         "products": [{"formula": "MgCl2", "name": "magnesium chloride"}, {"formula": "H2", "name": "hydrogen"}],
         "coefficients": [1, 2, 1, 1], "hint": "The salt needs two chlorides.",
         "description": "Metal + acid → salt + hydrogen."},
        {"reactants": [{"formula": "Al", "name": "aluminium"}, {"formula": "O2", "name": "oxygen"}],
         "products": [{"formula": "Al2O3", "name": "aluminium oxide"}],
         "coefficients": [4, 3, 2], "hint": "Same pattern as rusting iron.",
         "description": "Aluminium forms a protective oxide layer."},
        {"reactants": [{"formula": "CaCO3", "name": "calcium carbonate"}],
         "products": [{"formula": "CaO", "name": "calcium oxide"}, {"formula": "CO2", "name": "carbon dioxide"}],
         "coefficients": [1, 1, 1], "hint": "Already balanced? Check every element.",
         "description": "Thermal decomposition of limestone."},
        {"reactants": [{"formula": "KClO3", "name": "potassium chlorate"}],
         "products": [{"formula": "KCl", "name": "potassium chloride"}, {"formula": "O2", "name": "oxygen"}],
         "coefficients": [2, 2, 3], "hint": "Six oxygens on the right means three O2.",
         "description": "A lab source of oxygen gas."},
    ],
}

CELL_IDENTIFY = {
    "diagram": "cell",
    "intro": "Find each organelle on the animal cell. Click the structure named in the prompt.",
    "hotspots": [
        {"id": "cell-membrane", "label": "Cell membrane", "x": 50, "y": 14,
         "description": "Selectively permeable boundary that controls what enters and leaves."},
        {"id": "cytoplasm", "label": "Cytoplasm", "x": 52, "y": 29,
         "description": "Jelly-like fluid where most chemical reactions happen."},
        {"id": "nucleus", "label": "Nucleus", "x": 54, "y": 57,
         "description": "Control centre holding the DNA."},
        {"id": "nucleolus", "label": "Nucleolus", "x": 63, "y": 47,
         "description": "Dense region inside the nucleus that makes ribosomes."},
        {"id": "mitochondrion", "label": "Mitochondrion", "x": 26, "y": 42,
         "description": "Powerhouse — releases energy by respiration."},
        {"id": "ribosome", "label": "Ribosome", "x": 44, "y": 72,
         "description": "Tiny factories that build proteins."},
        {"id": "rough-er", "label": "Rough endoplasmic reticulum", "x": 81, "y": 52,
         "description": "Membrane network studded with ribosomes; folds and transports proteins."},
        {"id": "golgi", "label": "Golgi apparatus", "x": 26, "y": 64,
         "description": "Packages and ships proteins in vesicles."},
        {"id": "lysosome", "label": "Lysosome", "x": 70, "y": 28,
         "description": "Digestive enzymes that recycle worn-out parts."},
        {"id": "vacuole", "label": "Vacuole", "x": 22, "y": 56,
         "description": "Storage sac for water, nutrients and waste."},
        {"id": "centrioles", "label": "Centrioles", "x": 38, "y": 30,
         "description": "Organise the spindle during cell division."},
    ],
}

SKELETON_IDENTIFY = {
    "diagram": "skeleton",
    "intro": "Identify the bones of the human skeleton. Click the bone named in the prompt.",
    "hotspots": [
        {"id": "skull", "label": "Skull (cranium)", "x": 50, "y": 8, "description": "Protects the brain."},
        {"id": "mandible", "label": "Mandible", "x": 50, "y": 16, "description": "The lower jaw — the only movable skull bone."},
        {"id": "clavicle", "label": "Clavicle", "x": 41, "y": 21, "description": "Collarbone linking the arm to the trunk."},
        {"id": "sternum", "label": "Sternum", "x": 50, "y": 31, "description": "Breastbone anchoring the ribs in front."},
        {"id": "rib-cage", "label": "Rib cage", "x": 41, "y": 36, "description": "Twelve pairs of ribs protecting heart and lungs."},
        {"id": "vertebral-column", "label": "Vertebral column", "x": 50, "y": 46, "description": "The spine — 33 vertebrae."},
        {"id": "humerus", "label": "Humerus", "x": 33, "y": 34, "description": "Upper arm bone."},
        {"id": "radius", "label": "Radius", "x": 29, "y": 50, "description": "Forearm bone on the thumb side."},
        {"id": "ulna", "label": "Ulna", "x": 71, "y": 50, "description": "Forearm bone on the little-finger side."},
        {"id": "pelvis", "label": "Pelvis", "x": 43, "y": 55, "description": "Hip girdle carrying the body's weight."},
        {"id": "femur", "label": "Femur", "x": 45, "y": 67, "description": "Thigh bone — the longest bone in the body."},
        {"id": "patella", "label": "Patella", "x": 44, "y": 77, "description": "Kneecap."},
        {"id": "tibia", "label": "Tibia", "x": 43, "y": 90, "description": "Shin bone — the larger lower-leg bone."},
        {"id": "fibula", "label": "Fibula", "x": 58, "y": 89, "description": "Thin lower-leg bone beside the tibia."},
    ],
}


def _native(slug: str, title: str, subject: str, template: str, config: dict, description: str,
            concepts: list | None = None) -> dict:
    return {
        "concepts": concepts or [],
        "slug": slug, "title": title, "subject": subject, "provider": "native",
        "embed_url": None, "attribution": SASHA_ATTRIBUTION, "description": description,
        "native_template": template, "config": config,
    }


BUILTIN_LABS = [
    # physics
    _phet("projectile-motion", "Projectile Motion", "physics"),
    _phet("forces-and-motion-basics", "Forces and Motion: Basics", "physics"),
    _phet("circuit-construction-kit-dc", "Circuit Construction Kit (DC)", "physics"),
    _phet("energy-forms-and-changes", "Energy Forms and Changes", "physics"),
    _phet("gravity-and-orbits", "Gravity and Orbits", "physics"),
    # chemistry
    _phet("molecule-shapes", "Molecule Shapes", "chemistry"),
    _phet("acids-and-bases", "Acids and Bases", "chemistry"),
    _phet("balancing-chemical-equations", "Balancing Chemical Equations", "chemistry"),
    _phet("build-a-molecule", "Build a Molecule", "chemistry"),
    _phet("ph-scale", "pH Scale", "chemistry"),
    _phet("concentration", "Concentration", "chemistry"),
    _phet("states-of-matter", "States of Matter", "chemistry"),
    _native("reaction-lab-basics", "Reaction Lab: Balance the Equations", "chemistry",
            "reaction_lab", REACTION_LAB_BASICS,
            "Ten real reactions — combustion, rusting, the Haber process. Balance each one; "
            "the lab counts atoms live and grades every equation.",
            concepts=["balancing chemical equations", "conservation of mass", "stoichiometry"]),
    # biology
    _phet("natural-selection", "Natural Selection", "biology"),
    # "photosynthesis" removed 2026-09-05: PhET has no HTML5 sim by that slug (URL 404s).
    _phet("gene-expression-essentials", "Gene Expression Essentials", "biology"),
    _phet("neuron", "Neuron", "biology"),
    _native("cell-biology-identify", "Cell Biology: Identify the Organelles", "biology",
            "identify_lab", CELL_IDENTIFY,
            "Eleven organelles on a labelled animal cell. Find each structure on request; "
            "graded by structure, works on any phone.",
            concepts=["cell biology", "organelles"]),
    _native("skeleton-identify", "Human Skeleton: Name the Bones", "biology",
            "identify_lab", SKELETON_IDENTIFY,
            "Fourteen bones from skull to fibula on a front-view skeleton diagram.",
            concepts=["human skeleton", "bones"]),
    # mathematics
    _phet("area-builder", "Area Builder", "mathematics"),
    _phet("graphing-lines", "Graphing Lines", "mathematics"),
    _phet("fraction-matcher", "Fraction Matcher", "mathematics"),
]

from app.services.lab_studio_service import CBSE_LABS, CONCEPT_LABS
# The supplied library is the active product catalog. Retired entries are kept
# here as source history only, never offered to learners or course pickers.
RETIRED_SLUGS = {l['slug'] for l in BUILTIN_LABS + CONCEPT_LABS}
BUILTIN_LABS = list(CBSE_LABS)

BUILTIN_BY_SLUG = {l["slug"]: l for l in BUILTIN_LABS}
# Kept for older imports (courses.py used to import SIM_SLUGS); built-ins only.
SIM_SLUGS = set(BUILTIN_BY_SLUG)


def _row_dict(r: VirtualLabCatalog) -> dict:
    return {
        "slug": r.slug, "title": r.title, "subject": r.subject, "provider": r.provider,
        "embed_url": r.embed_url, "attribution": r.attribution, "description": r.description,
        "native_template": r.native_template, "config": r.config,
        "thumbnail_url": r.thumbnail_url, "is_published": r.is_published, "catalog_id": r.id,
    }


def catalog(db: Session, include_unpublished: bool = False) -> dict:
    """slug -> lab dict. DB rows override built-ins on slug collision."""
    merged = {s: dict(l, is_builtin=True, is_published=True) for s, l in BUILTIN_BY_SLUG.items()}
    for r in db.query(VirtualLabCatalog).all():
        if r.provider == 'phet' or r.slug in RETIRED_SLUGS:
            continue
        if r.embed_url and 'phet.colorado.edu' in r.embed_url.lower():
            continue
        if r.is_published or include_unpublished:
            merged[r.slug] = dict(_row_dict(r), is_builtin=False)
        elif r.slug in merged:
            # An unpublished override hides the built-in from the public list.
            merged.pop(r.slug, None)
    return merged


def get_lab(db: Session, slug: str) -> Optional[dict]:
    from app.services.lab_catalog_service import canonical_lab_slug
    return catalog(db).get(canonical_lab_slug(slug))


def is_valid_lab_slug(db: Session, slug: str) -> bool:
    return get_lab(db, slug) is not None


def _public(lab: dict, with_config: bool) -> dict:
    d = {k: v for k, v in lab.items() if k not in ("config",)}
    d["source"] = lab.get("attribution") or ""
    d["concepts"] = list(lab.get("concepts") or [])
    d['chapter_ids'] = (lab.get('config') or {}).get('chapter_ids', [])
    d["sim"] = lab["slug"]  # backwards-compatible field name for the picker
    if lab["provider"] == "native":
        d["max_score"] = derive_lab_max_score(lab["native_template"], lab.get("config") or {})
        if with_config:
            if lab.get('native_template') == 'concept_lab':
                from app.services.lab_investigation_service import learner_config, revision
                d['config'] = learner_config(lab.get('config'))
                d['revision'] = revision(lab.get('config'))
            else:
                d["config"] = lab.get("config")
    return d


@router.get("")
async def list_labs(subject: str | None = None, db: Session = Depends(get_db)):
    labs = [l for l in catalog(db).values() if subject is None or l["subject"] == subject]
    labs.sort(key=lambda l: (l["subject"], l["provider"] != "native", l["title"]))
    return {"labs": [_public(l, with_config=False) for l in labs]}


@router.get("/{slug}")
async def get_lab_detail(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_optional_current_user),
):
    lab = get_lab(db, slug)
    # Published concept investigations are explicitly shared in the public lab
    # catalog. Other interactive content keeps its existing preview gate.
    if current_user is None and not (lab and (lab.get('native_template') == 'concept_lab' or lab['slug'] in {l['slug'] for l in CBSE_LABS})):
        from app.services.public_preview import require_anonymous_preview
        require_anonymous_preview(db, "virtual_lab_sim", slug, "This lab")   # public-preview lessons only
    """Full entry for the player; native labs include their config (the answer
    key ships to the client — advisory grading, identical posture to /games/{id}/play)."""
    if not lab and current_user is not None:
        private = db.query(VirtualLabCatalog).filter_by(slug=slug).first()
        if private and (private.created_by == current_user.id or current_user.role in ('admin', 'superadmin')):
            lab = _row_dict(private)
    if not lab:
        raise HTTPException(status_code=404, detail="Virtual lab not found")
    d = _public(lab, with_config=True)
    if lab.get('native_template') == 'concept_lab' and current_user is not None:
        authored = db.query(VirtualLabCatalog).filter_by(slug=slug).first()
        if authored and (authored.created_by == current_user.id or current_user.role in ('admin','superadmin')):
            d['config'] = authored.config
    if lab["provider"] == "native":
        best = None
        if current_user is not None:
            best = (
                db.query(func.max(VirtualLabResult.score))
                .filter(VirtualLabResult.lab_slug == slug, VirtualLabResult.user_id == current_user.id)
                .scalar()
            )
        d["best_score"] = int(best) if best is not None else None
        if lab.get('native_template') == 'concept_lab' and current_user is not None:
            from app.services.lab_investigation_service import best_score
            scored = best_score(db,slug,current_user.id,lab.get('config') or {})
            d['best_score'] = int(scored[0]) if scored else None
    return d


class LabResultIn(BaseModel):
    score: StrictInt = Field(..., ge=0)
    duration_s: StrictInt = Field(0, ge=0, le=6 * 3600)


@router.post("/{slug}/results", status_code=201)
async def submit_lab_result(
    slug: str,
    payload: LabResultIn,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_active_user),
):
    lab = get_lab(db, slug)
    if not lab:
        raise HTTPException(status_code=404, detail="Virtual lab not found")
    if lab["provider"] != "native" or lab.get("native_template") == "concept_lab":
        raise HTTPException(status_code=400, detail="Only native labs record results")
    max_score = derive_lab_max_score(lab["native_template"], lab.get("config") or {})
    if payload.score > max_score:
        raise HTTPException(status_code=400, detail=f"score exceeds the lab's max_score ({max_score})")

    row = VirtualLabResult(
        lab_slug=slug, user_id=current_user.id, score=payload.score,
        max_score=max_score, duration_s=payload.duration_s,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # XP — AFTER the result commit, flush-only award(), best-effort.
    try:
        from app.services.gamification_service import award as _award_xp
        if payload.score > 0:
            _award_xp(db, current_user.id, "lab_completed", points=20,
                      event_key=f"lab:{slug}:completed:user:{current_user.id}",
                      meta={"lab_slug": slug, "template": lab["native_template"]})
        if payload.score == max_score and max_score > 0:
            _award_xp(db, current_user.id, "lab_perfect", points=10,
                      event_key=f"lab:{slug}:perfect:user:{current_user.id}",
                      meta={"lab_slug": slug, "template": lab["native_template"]})
        db.commit()
    except Exception as exc:  # never fail the POST on an XP hiccup
        logger.warning("Gamification award failed for lab result: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass

    best = (
        db.query(func.max(VirtualLabResult.score))
        .filter(VirtualLabResult.lab_slug == slug, VirtualLabResult.user_id == current_user.id)
        .scalar()
    )
    from app.services.mastery_service import safe_record_evidence
    safe_record_evidence(db, user_id=current_user.id, kind="lab", ref_id=slug, score=float(payload.score), max_score=float(max_score))

    return {"id": row.id, "score": row.score, "max_score": max_score,
            "best_score": int(best) if best is not None else row.score}
