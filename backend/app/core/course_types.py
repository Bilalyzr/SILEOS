"""Canonical course types.

Owner ruling (2026-09-04): every course belongs to exactly ONE of these
three types. `course_category` and tags stay free-form and are only sorting
aids *within* a type; they can never replace or override the type.
"""

from typing import Optional, Union

COURSE_TYPES = ("meiporul", "seyappaduporul", "utporul")

DEFAULT_COURSE_TYPE = "meiporul"

COURSE_TYPE_LABELS = {
    "meiporul": "Meiporul (AR/VR)",
    "seyappaduporul": "Seyappaduporul (Skill)",
    "utporul": "Utporul (Tech)",
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
    "meiporul": {  # MP — 3D/AR/VR focused
        "label": "Meiporul (AR/VR)",
        "capabilities": ["video", "quiz", "three_d_models", "geogebra", "h5p", "virtual_labs"],
    },
    "seyappaduporul": {  # SP — school students, recorded + live + games
        "label": "Seyappaduporul (School)",
        "capabilities": ["video", "quiz", "games", "h5p", "live_classes",
                         "learning_paths", "rewards", "virtual_labs"],
    },
    "utporul": {  # UP — skill oriented, everything enabled
        "label": "Utporul (Skill)",
        "capabilities": ["video", "quiz", "games", "h5p", "live_classes",
                         "learning_paths", "rewards", "geogebra",
                         "three_d_models", "virtual_labs"],
    },
}


def course_type_supports(course_type: str, capability: str) -> bool:
    cap = TYPE_CAPABILITIES.get((course_type or "").lower())
    return bool(cap and capability in cap["capabilities"])
