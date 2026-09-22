# Sasha Learning Monitor

## Product boundary

Sasha is a student-facing Socratic tutor. The instructor experience is a
course-scoped monitoring and intervention surface, not a second chatbot.

- A learner's **general learning** space stays private and emits no instructor
  learning signal.
- When the learner explicitly selects an enrolled course, each question emits
  a bounded learning signal for an instructor who can edit that course.
- The signal stores a 500-character learner-question excerpt, detected concept,
  concern score, likely gap, repeat count and human-readable reasons.
- The AI reply is not stored in the instructor signal and is never returned by
  the instructor API.
- The learner sees the boundary in both the full Sasha studio and lesson tutor.

## Explainable concern model

The score is deterministic and independent of the language model. It combines:

1. explicit self-reported confusion;
2. requests to repeat or simplify;
3. application/problem-solving language;
4. repeated questions on the same course concept within 30 days;
5. verified learner-mastery evidence; and
6. graded-answer guard activation.

Likely gaps are classified as foundational, repeated confusion, confidence,
terminology, application, or concept clarity. Every classification includes
plain-language reasons so an instructor can verify the evidence before acting.

## Access control and scale

`GET /api/v1/signals/courses/{course_id}/sasha-insights` uses the existing
`can_edit` rule (owner, collaborator, admin or superadmin). Student and unrelated
instructor access is denied. Indexed course/time, learner/course/time and
course/concept paths support the main production queries. Aggregation happens in
SQL and student/evidence result sets are bounded.

## Deployment

Run Alembic revision `0049` after `0048`. Fresh environments also receive the
table through SQLAlchemy metadata creation during application startup.

The instructor UI is the default **Sasha Monitor** tab at
`/instructor/insights`. The student surface is `/learn-with-sasha`.
