"""Canonical Sasha Infinity business-vertical boundaries.

The platform is one shared control plane with three independently operated
business pillars. This module is intentionally data-only so API services,
reporting adapters, and policy code can share the same vocabulary without
importing UI or payment implementation details.
"""

from __future__ import annotations

from typing import Optional


VERTICAL_KEYS = ("meiporul", "seyappaduporul", "utporul")

VERTICALS = {
    "meiporul": {
        "code": "MA1",
        "label": "Meiporul",
        "tamil": "மெய்ப்பொருள்",
        "subdomain": "meiporul",
        "mission": "Immersive curriculum, 3D assets, AR, VR, and experiential labs.",
        "business_model": "Immersive content, asset licensing, lab subscriptions, hardware deployment, and support.",
    },
    "seyappaduporul": {
        "code": "MA2",
        "label": "Seyappaduporul",
        "tamil": "செயப்படுபொருள்",
        "subdomain": "seyappaduporul",
        "mission": "Tutoring and school operations, including live classes, fees, attendance, notes, ebooks, and exam papers.",
        "business_model": "Recurring tuition, institution operations, tutoring services, digital resources, and paper generation.",
    },
    "utporul": {
        "code": "MA3",
        "label": "Utporul",
        "tamil": "உட்பொருள்",
        "subdomain": "utporul",
        "mission": "Skill development through course creation, assessments, credentials, and career pathways.",
        "business_model": "Course sales, memberships, assessments, certificates, creator commerce, and career services.",
    },
}

# Every financial writer must choose one of these streams. Keeping the
# contract here prevents a checkout, invoice, or deployment workflow from
# inventing a reporting category that the central portfolio cannot reconcile.
REVENUE_STREAMS = {
    "meiporul": (
        "immersive_courses",
        "asset_licensing",
        "experience_subscription",
        "lab_deployment",
        "amc_support",
    ),
    "seyappaduporul": (
        "tuition_fees",
        "institution_operations",
        "digital_resources",
        "paper_generation",
        "franchise_services",
    ),
    "utporul": (
        "skill_courses",
        "assessment_services",
        "credentials",
        "creator_commerce",
        "career_services",
    ),
}


_ALIASES = {
    "meiporul": "meiporul",
    "ma1": "meiporul",
    "seyappaduporul": "seyappaduporul",
    "seyappadu-porul": "seyappaduporul",
    "seyappadu porul": "seyappaduporul",
    "seyappadu_porul": "seyappaduporul",
    "ma2": "seyappaduporul",
    "utporul": "utporul",
    "upporul": "utporul",
    "ma3": "utporul",
}


def normalize_vertical(value: Optional[str]) -> Optional[str]:
    """Return a canonical pillar key, accepting the blueprint's aliases."""
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if not cleaned:
        return None
    return _ALIASES.get(cleaned)


def revenue_metadata(vertical: Optional[str], stream: Optional[str] = None) -> dict[str, str]:
    """Immutable attribution snapshot for an order line."""
    canonical = normalize_vertical(vertical)
    if canonical is None:
        return {}
    default_stream = {
        "meiporul": "immersive_courses",
        "seyappaduporul": "tuition_fees",
        "utporul": "skill_courses",
    }[canonical]
    selected_stream = stream or default_stream
    if selected_stream not in REVENUE_STREAMS[canonical]:
        raise ValueError(f"Unknown revenue stream for {canonical}: {selected_stream}")
    return {"business_vertical": canonical, "revenue_stream": selected_stream}
