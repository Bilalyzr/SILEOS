# Teaching and examining with 3D files

How a 3D model becomes a lesson that teaches better and an exam that tests
better than a picture — and where each step lives in the LMS (2026-09-05).

## Why 3D beats a diagram

| A diagram gives | A 3D model gives |
|---|---|
| one fixed angle chosen by the illustrator | the learner chooses the angle — occlusion, depth and scale become real |
| labels printed on the picture | labels the learner has to *find*: anchors are placed on the surface, names never leak |
| "look at this" | "turn it until you see why" — the path a learner takes is recorded (rotate / zoom / reset / hesitate) |
| a right or wrong answer | a right answer **plus how it was reached**: clean, mixed or trial-and-error |

The last row is the examiner's win. A learner who clicks every region until one
turns green scores the same marks as one who reasoned — but the platform
tells the two apart (`confidence` on every attempt) and the mastery graph
weights the evidence accordingly (clean 1.0, mixed 0.8, trial-and-error 0.5).

## The four-step loop (the "Teach & examine" kit under every 3D lesson)

1. **Teach** — attach the model to a lesson (type "3D model"). Write the lesson
   description: what to look at, in what order. That text is also the T4
   fallback for learners on phones without WebGL, so a lesson is never "blank"
   on a weak device. The Tier Preview under the model shows exactly what each
   tier sees (interactive → turntable → still image + text) and the fps /
   triangle / GLB-size meter tells you before publishing whether low-end
   phones will cope. Uploads over the hard budget are refused; over the soft
   per-tier budget you get a warning and the lowest tier that still runs it.
2. **Examine** — "Create an exam task from this model" opens the task builder
   with the model already selected. Seven task types:
   - *identify* — "click the mitral valve" (anchors placed on the surface)
   - *match* — drag names onto numbered regions
   - *measure* — estimate a distance/angle between two anchors with tolerance
   - *verify* — change parameters until a claim holds (or prove it never does)
   - *manipulate* — reach a target state
   - *sequence* — order the steps of a process on the model
   - *assemble* — put parts into slots
   Grading is server-side from the submitted answers; the client never sends a
   score. Anchors show as "Region 1, 2, 3…" to learners; the real names stay on
   the server.
3. **Grade** — publish the task and add it to any quiz as a scorable item
   (kind `three_d_task`). It scores into the 3D bucket of the cumulative grade
   (type-profile weights) and writes evidence into the learner's mastery graph
   for the task's concepts. Practice-only items are exempt from the T4 parity
   rule; graded items must run on T4 so nobody is examined on hardware they
   do not have.
4. **Learn** — Insights → "Next Class & 3D Insights" shows, per task, the share
   of clean vs trial-and-error paths and how the same learners score on the
   task's concepts in quizzes. The insight sentences are explicit: "clean
   solvers score 90% on heart anatomy vs 40% for trial-and-error solvers — the
   path signal predicts understanding here" or "trial-and-error solvers still
   get full marks — grade the path or lower attempts_allowed".

Learners get the mirror image: under every 3D lesson, **Check yourself** lists
the published tasks on that model and plays them inline — explore first, then
prove it.

## Attracting learners with it

Mark the 3D lesson (or any lesson) as **Public preview** in the editor. Visitors
open the real model from the course page without an account — the model file
is served only for public-preview lessons in published courses, everything
else stays locked and its media never leaves the server.

## What to prepare (owner side)

- GLB files (glTF binary). Budgets: hard cap 1.5M triangles / 64 MB textures;
  soft T1 500k / 24 MB, T2 150k / 8 MB, T3 50k / 4 MB. Decimate in Blender,
  compress textures (KTX2) and meshes (Draco) — both are detected and shown.
- A shared library: admins import packs under Content Libraries; instructors
  attach library models cross-owner.
- Concepts on every task (comma-separated) — this is what links 3D evidence to
  quiz evidence in the mastery graph and what the insight cards compare.

## Where it lives

Backend `routers/three_d.py` (upload + budget), `routers/three_d_tasks.py`
(builder, play, grading, `for-model` list), `services/glb_budget.py`,
`services/flywheel_service.insight_cards`. Frontend `components/three-d/
{ThreeDViewer, ThreeDTeachingKit, ThreeDCheckYourself, tasks/ThreeDTaskPlayer}`,
`components/studio/TierPreview`, `pages/instructor/three-d-tasks`.
