---
name: sasha-3d-pipeline
description: 3D asset ingestion and optimisation work
---

Blueprint 8.4. Load for any 3D asset work.

Pipeline order: upload, then format detect/validate (reject >500MB or >2M tris without approval), then security scan (NO embedded scripts; glTF extension allowlist; zip-bomb caps), then Blender headless normalise (metres, transforms applied), then PBR metallic-roughness, then texture ladder 2048-to-KTX2/BasisU, then meshoptimizer LOD0-3 + Draco, then USDZ, then fallbacks (FFmpeg turntable mp4, stills, text description), then budget check, then content-addressed store.

Hard budgets (reject or auto-fix, NEVER wave through):
- Low Android 2GB: 25k tris / 8MB textures / 40 draws / 30fps
- Mid Android: 120k / 25MB / 80 / 30
- Desktop: 800k / 80MB / 200 / 60
- Quest 3S: 250k / 40MB / 100 / 72

In the Sasha repo today: 3D lessons are a queued sub-project. The upload-hardening templates to mirror are library_storage.py (uuid naming, path reassertion, quota) and the H5P zip hardening.
