---
name: sasha-component-registry
description: Adding a lesson or content type to the course engine
---

The registry contract in THIS repo (lesson content types: video | h5p | game | geogebra). Load when adding any content type.

Seven seams, exactly:
1. Model: FK column on lessons (e.g. geogebra_applet_id) plus the owning content table.
2. courses.py _resolve_lesson_content_fields: extend the tuple — type + id ship ATOMICALLY in one request; a type-only PATCH to a non-video type is a 400; flipping to video clears ALL content FKs.
3. schemas/course.py: LESSON_CONTENT_TYPES set + the id field on LessonCreate AND LessonUpdate.
4. course_service.format_lesson_response: expose the handle the player needs.
5. frontend/src/lib/lessonContentSync.ts: extend the mapping — never inline-map in pages.
6. Player branch in lesson-redesigned.tsx (mirror the h5p/game ternary).
7. axios noSlashEndpoints for the new content router prefix.
Plus tests: attach happy path + type-without-id 400 + cross-owner 403 + status gating + free/paid business rules if any.

RULE: if you find yourself editing other course-engine files, stop and re-read this list.
