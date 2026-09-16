---
name: sasha-particle-sim
description: Particle and simulation features
---

Blueprint 8.5.1 + SILEOS critique ADR-0001.7. Load for simulation work.

- GPU-instanced (WebGL2 transform feedback / WebGPU); CPU fallback capped at 2k particles.
- Deterministic + seeded with a FIXED timestep (frame-rate-dependent physics is forbidden) — BUT bitwise cross-vendor GPU determinism is NOT achievable (float ordering differs). Grading authority = quantized state, or a CPU-reference sim, or baked field grids. Design grading against the grid, not the render.
- Physically meaningful parameters only (field strength, viscosity, charge) — parameter names are the pedagogy.
- Probe-based assessment works at every tier: probes read numeric values from baked field grids at T3-T5.
- Budgets: mid Android 50k at 30fps; desktop 250k at 60; Quest 80k at 72.
