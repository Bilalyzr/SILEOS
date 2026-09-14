"""GET /api/v1/courses/type-capabilities — the MP/SP/UP tool matrix.

Lives in its own router registered BEFORE the courses router in main.py:
the courses router declares parametrised GET routes that would otherwise
shadow /courses/type-capabilities."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/courses/type-capabilities")
async def get_type_capabilities():
    """The tool-enablement matrix per course type (MP/SP/UP). The creation
    wizard reads this to show/hide tooling; tools marked "planned" render
    disabled and are never faked."""
    from app.core.course_types import TOOL_AVAILABILITY, TYPE_CAPABILITIES
    out = {}
    for ctype, meta in TYPE_CAPABILITIES.items():
        out[ctype] = {
            "label": meta["label"],
            "tools": [
                {"tool": c, "availability": TOOL_AVAILABILITY.get(c, "planned")}
                for c in meta["capabilities"]
            ],
        }
    return {"types": out}
