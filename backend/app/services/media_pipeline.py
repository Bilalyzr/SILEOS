"""Media pipeline (roadmap item 9, 2026-09-06): pre-built 3D tiers and
audio-only video renditions.

  build_glb_tiers(model_path)   → {"T2": path, "T3": path} via gltf-transform
                                  (simplify + resize/compress textures). T1 = original.
  build_audio_rendition(video)  → sibling .m4a (AAC 64 kbps) via ffmpeg.

Both are honest about missing tools: `tool_status()` reports what is
installed; callers return 503 with the install hint instead of pretending.
Tier files are recorded on three_d_models.tier_files (JSON) so the viewer
can request `?tier=T2|T3`; audio renditions sit next to the video and the
player probes them.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)

TIER_SPECS = {
    # ratio = fraction of triangles kept; texture max size; webp quality
    "T2": {"ratio": 0.45, "texture_size": 1024, "quality": 80},
    "T3": {"ratio": 0.15, "texture_size": 512, "quality": 70},
}


def _which(*names: str) -> Optional[str]:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def ffmpeg_path() -> Optional[str]:
    return os.environ.get("FFMPEG_BIN") or _which("ffmpeg", "ffmpeg.exe")


def gltf_transform_path() -> Optional[str]:
    return os.environ.get("GLTF_TRANSFORM_BIN") or _which("gltf-transform", "gltf-transform.cmd")


def tool_status() -> Dict[str, Optional[str]]:
    return {"ffmpeg": ffmpeg_path(), "gltf_transform": gltf_transform_path()}


def _run(cmd, timeout: int) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=os.name == "nt" and str(cmd[0]).lower().endswith(".cmd"))
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "")[-800:] or f"exit {proc.returncode}")


def build_glb_tiers(src_path: str, out_dir: Optional[str] = None, tiers=("T2", "T3")) -> Dict[str, str]:
    """Produce lower tiers next to the source GLB. Returns {tier: path}.
    Raises RuntimeError when gltf-transform is missing or a step fails."""
    tool = gltf_transform_path()
    if not tool:
        raise RuntimeError("gltf-transform is not installed (npm i -g @gltf-transform/cli)")
    out_dir = out_dir or os.path.dirname(src_path)
    base = os.path.splitext(os.path.basename(src_path))[0]
    out: Dict[str, str] = {}
    for tier in tiers:
        spec = TIER_SPECS[tier]
        simplified = os.path.join(out_dir, f"{base}.{tier.lower()}.tmp.glb")
        final = os.path.join(out_dir, f"{base}.{tier.lower()}.glb")
        _run([tool, "simplify", src_path, simplified, "--ratio", str(spec["ratio"]), "--error", "0.001"], timeout=600)
        try:
            _run([tool, "webp", simplified, final, "--quality", str(spec["quality"])], timeout=600)
            # resize is a separate command on older CLIs; ignore if unavailable
            try:
                _run([tool, "resize", final, final, "--width", str(spec["texture_size"]), "--height", str(spec["texture_size"])], timeout=600)
            except Exception:
                logger.info("gltf-transform resize skipped for %s", final)
        except Exception:
            # texture step failed (e.g. no textures) — keep the simplified mesh
            shutil.move(simplified, final)
        finally:
            if os.path.exists(simplified):
                os.remove(simplified)
        out[tier] = final
    return out


def build_audio_rendition(video_path: str) -> str:
    """AAC 64 kbps audio-only sibling: <video>.m4a. Returns the path."""
    tool = ffmpeg_path()
    if not tool:
        raise RuntimeError("ffmpeg is not installed")
    out = os.path.splitext(video_path)[0] + ".m4a"
    _run([tool, "-y", "-i", video_path, "-vn", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", out], timeout=1800)
    return out


def audio_sibling(video_path: str) -> Optional[str]:
    cand = os.path.splitext(video_path)[0] + ".m4a"
    return cand if os.path.exists(cand) else None
