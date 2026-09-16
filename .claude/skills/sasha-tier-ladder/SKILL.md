---
name: sasha-tier-ladder
description: Any renderable content — degradation tiers T0-T7
---

Blueprint 8.6. Load whenever content must work on weak devices.

T0 XR, T1 full 3D, T2 lite 3D, T3 turntable, T4 stills, T5 text/audio, T6 offline, T7 SMS.
- Detection: device capability + network; transitions reversible MID-SESSION.
- THE RULE: identical marks achievable at every tier down to T4. If a task cannot be answered at T4, redesign the task (parameter-based success criteria), not the tier.
- Show the tier honestly in UI, non-judgementally, with manual override. Never make a low-tier student feel lesser.
- In Sasha LMS today: players must degrade gracefully (video to audio/transcript pattern); the GeoGebra embed already carries a connection-error state rather than a blank box.
- Test tier parity: same assessment answered at T4 vs T1 produces the same score.
