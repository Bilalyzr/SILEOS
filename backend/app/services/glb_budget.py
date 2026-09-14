"""GLB budget check (v2.0 §11 quality disciplines — WP9).

Parses the GLB container (12-byte header + JSON chunk) WITHOUT a 3D library:
counts triangles from mesh primitives (indices accessor count / 3, or
POSITION accessor count / 3 for non-indexed), sums texture bytes from
image bufferViews, and reports meshes / materials / textures. Returns an
explainable budget report with a per-tier verdict:

  T1 (interactive 3D on capable devices) — soft cap 500k triangles / 24MB textures
  T2 (mid-range phones)                  — 150k / 8MB
  T3 (turntable)                         — 50k  / 4MB

Anything over HARD caps (1.5M triangles, 64MB textures) is rejected with
a 422 by the upload/import endpoints; anything over a tier's soft cap is
returned as a warning so the instructor sees which tiers the asset will
degrade on. Pure function of the bytes — never stored.
"""
from __future__ import annotations

import json
import struct
from typing import Any, Dict, List

HARD_TRIANGLES = 1_500_000
HARD_TEXTURE_BYTES = 64 * 1024 * 1024
TIER_CAPS = {"T1": (500_000, 24 * 1024 * 1024), "T2": (150_000, 8 * 1024 * 1024), "T3": (50_000, 4 * 1024 * 1024)}
MODE_TRIANGLES = 4   # glTF primitive mode TRIANGLES


class GlbBudgetError(ValueError):
    pass


def parse_glb_json(raw: bytes) -> Dict[str, Any]:
    if len(raw) < 20 or raw[:4] != b"glTF":
        raise GlbBudgetError("not a GLB container")
    version, total = struct.unpack_from("<II", raw, 4)
    if version != 2:
        raise GlbBudgetError(f"unsupported glTF version {version}")
    chunk_len, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != 0x4E4F534A:  # 'JSON'
        raise GlbBudgetError("first chunk is not JSON")
    body = raw[20:20 + chunk_len]
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as exc:
        raise GlbBudgetError(f"malformed JSON chunk: {exc}") from exc


def analyze_glb(raw: bytes) -> Dict[str, Any]:
    """Budget report for a GLB blob. Raises GlbBudgetError only for a
    structurally unreadable container (magic already checked by callers)."""
    doc = parse_glb_json(raw)
    accessors = doc.get("accessors") or []
    buffer_views = doc.get("bufferViews") or []
    triangles = 0
    for mesh in doc.get("meshes") or []:
        for prim in mesh.get("primitives") or []:
            mode = prim.get("mode", MODE_TRIANGLES)
            if mode != MODE_TRIANGLES:
                continue
            idx = prim.get("indices")
            if idx is not None and idx < len(accessors):
                triangles += int(accessors[idx].get("count", 0)) // 3
            else:
                pos = (prim.get("attributes") or {}).get("POSITION")
                if pos is not None and pos < len(accessors):
                    triangles += int(accessors[pos].get("count", 0)) // 3
    texture_bytes = 0
    for img in doc.get("images") or []:
        bv = img.get("bufferView")
        if bv is not None and bv < len(buffer_views):
            texture_bytes += int(buffer_views[bv].get("byteLength", 0))
    report = {
        "file_bytes": len(raw), "triangles": triangles, "texture_bytes": texture_bytes,
        "meshes": len(doc.get("meshes") or []), "materials": len(doc.get("materials") or []),
        "textures": len(doc.get("textures") or []), "images": len(doc.get("images") or []),
        "draco": "KHR_draco_mesh_compression" in (doc.get("extensionsUsed") or []),
        "ktx2": "KHR_texture_basisu" in (doc.get("extensionsUsed") or []),
    }
    warnings: List[str] = []
    tiers_ok: Dict[str, bool] = {}
    for tier, (tri_cap, tex_cap) in TIER_CAPS.items():
        ok = triangles <= tri_cap and texture_bytes <= tex_cap
        tiers_ok[tier] = ok
        if not ok:
            warnings.append(f"{tier}: {triangles:,} triangles / {texture_bytes // 1024 // 1024} MB textures exceed the "
                            f"{tri_cap:,} / {tex_cap // 1024 // 1024} MB budget — learners on this tier fall back to a lower one")
    report["tiers_ok"] = tiers_ok
    report["warnings"] = warnings
    report["lowest_full_tier"] = next((t for t in ("T1", "T2", "T3") if tiers_ok[t]), None)
    report["reject_reason"] = None
    if triangles > HARD_TRIANGLES:
        report["reject_reason"] = f"{triangles:,} triangles exceed the hard cap of {HARD_TRIANGLES:,} — decimate in Blender first"
    elif texture_bytes > HARD_TEXTURE_BYTES:
        report["reject_reason"] = f"{texture_bytes // 1024 // 1024} MB of textures exceed the hard cap of {HARD_TEXTURE_BYTES // 1024 // 1024} MB"
    return report


def check_or_raise(raw: bytes, name: str = "model"):
    """Used by upload + library import: reject over hard caps, else return
    the report (with soft warnings) for the caller to surface."""
    from fastapi import HTTPException
    try:
        report = analyze_glb(raw)
    except GlbBudgetError as exc:
        # Magic bytes already passed; an unreadable JSON chunk means we cannot
        # BUDGET it, not that it is invalid — three.js may still load it.
        # Never block on our own parser: report "unknown" and let it through.
        return {"file_bytes": len(raw), "triangles": None, "texture_bytes": None, "tiers_ok": {}, "warnings": [],
                "lowest_full_tier": None, "reject_reason": None, "parse_error": str(exc)}
    if report["reject_reason"]:
        raise HTTPException(status_code=422, detail=f"{name}: {report['reject_reason']}")
    return report
