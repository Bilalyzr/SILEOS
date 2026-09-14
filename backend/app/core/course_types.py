"""Canonical course types.

Owner ruling (2026-09-04): every course belongs to exactly ONE of these
three types. `course_category` and tags stay free-form and are only sorting
aids *within* a type; they can never replace or override the type.
"""

from typing import Optional, Union

from app.core.business_verticals import VERTICAL_KEYS, VERTICALS

COURSE_TYPES = VERTICAL_KEYS

# A course with no specialist choice belongs to the shared skills/authoring
# pillar. Meiporul and Seyappaduporul are explicit delivery decisions.
DEFAULT_COURSE_TYPE = "utporul"

COURSE_TYPE_LABELS = {
    key: f"{item['label']} - {item['mission']}" for key, item in VERTICALS.items()
}


def normalize_course_type(value: Optional[str]) -> Optional[str]:
    """Normalize a client-supplied course_type to its canonical lowercase form.

    Returns None for None/blank (caller decides whether that means "leave
    unchanged" or "apply the default"). Accepts the legacy capitalized forms
    ("Meiporul", "SEYAPPADUPORUL", ...) previously stored by edit-course.
    Raises ValueError for anything outside the three allowed types so the
    routers can reject it with a clear message instead of silently storing
    a value that later shows up as an unknown filter bucket.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if lowered not in COURSE_TYPES:
        raise ValueError(
            f"course_type must be one of: {', '.join(COURSE_TYPES)}"
        )
    return lowered


# ---------------------------------------------------------------------------
# Type capability matrix (owner restructure, 2026-09-04)
# Tools/features each course type enables. The course-creation UI reads this
# (GET /api/v1/courses/type-capabilities) and shows/hides tooling; the
# backend enforces attach rules where a capability has a hard gate.
#   availability: "live" = tool exists today; "planned" = on the roadmap,
#   shown disabled (never faked).
TOOL_AVAILABILITY = {
    "video": "live", "quiz": "live", "games": "live", "h5p": "live",
    "geogebra": "live", "learning_paths": "live", "rewards": "live",
    "three_d_models": "live",      # Phase 2: GLB upload + viewer
    "live_classes": "live", "virtual_labs": "live",        # Phase 4: PhET embeds
}
TYPE_CAPABILITIES = {
    "meiporul": {  # MP - immersive curriculum and experiential learning
        "label": "Meiporul (Immersive)",
        "capabilities": ["video", "quiz", "games", "h5p", "geogebra",
                         "three_d_models", "virtual_labs", "live_classes",
                         "learning_paths", "rewards"],
    },
    "seyappaduporul": {  # SP - tutoring and school operations
        "label": "Seyappaduporul (Tutoring)",
        "capabilities": ["video", "quiz", "games", "h5p", "live_classes",
                         "learning_paths", "rewards", "virtual_labs", "geogebra"],
    },
    "utporul": {  # UP - course creation, skills, assessment, credentials
        "label": "Utporul (Skills)",
        "capabilities": ["video", "quiz", "games", "h5p", "live_classes",
                         "learning_paths", "rewards", "geogebra",
                         "three_d_models", "virtual_labs"],
    },
}


def course_type_supports(course_type: str, capability: str) -> bool:
    cap = TYPE_CAPABILITIES.get((course_type or "").lower())
    return bool(cap and capability in cap["capabilities"])
