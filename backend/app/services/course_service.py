"""
Course Service - Business logic for course management
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json
import re
import unicodedata
import logging

from app.models.course import Course, Lesson
from app.models.quiz import Quiz, QuizAttempt
from app.models.enrollment import Enrollment, LessonProgress

_slug_logger = logging.getLogger(__name__)


def _slugify_title(title: str) -> str:
    """Build a URL-safe base slug from a course title.

    Tamil / non-ASCII titles are transliterated via NFKD strip where
    possible. If nothing ASCII survives the stripping (pure Tamil title),
    returns empty string so the caller falls back to `course-<id>`.
    """
    if not title:
        return ""
    try:
        # Strip combining marks (accented latin → latin)
        normalized = unicodedata.normalize("NFKD", title)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    except Exception:
        ascii_only = ""
    base = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_only.lower()).strip("-")
    return base


def build_default_slug(course: Course) -> str:
    """Return a deterministic slug for a course: `<title-slug>-<id>`.

    For courses whose title produces no ASCII output (pure Tamil), falls
    back to `course-<id>`. NEVER returns empty string.
    """
    base = _slugify_title(course.post_title or "")
    if not base:
        return f"course-{course.id}"
    return f"{base}-{course.id}"


def _slug_is_unique(db: Session, slug: str, exclude_id: Optional[int] = None) -> bool:
    q = db.query(Course).filter(func.lower(Course.post_name) == slug.lower())
    if exclude_id is not None:
        q = q.filter(Course.id != exclude_id)
    return q.first() is None


def generate_unique_slug(db: Session, title: str, course_id: Optional[int] = None) -> str:
    """Generate a slug guaranteed unique across Course.post_name.

    Strategy:
      1. Produce ASCII base from title.
      2. If base empty (pure unicode/Tamil) → `course-<id>` if we know id,
         else `course`.
      3. Append `-2`, `-3`, ... until uniqueness holds.
    """
    base = _slugify_title(title or "")
    if not base:
        base = f"course-{course_id}" if course_id else "course"

    candidate = base
    n = 2
    while not _slug_is_unique(db, candidate, exclude_id=course_id):
        candidate = f"{base}-{n}"
        n += 1
        if n > 10000:  # safety
            candidate = f"{base}-{course_id or int(datetime.utcnow().timestamp())}"
            break
    return candidate


def ensure_slug(db: Session, course: Course) -> str:
    """Ensure a course has a persisted non-empty `post_name`. Returns it.

    Called by read paths that discover a course with empty post_name so the
    slug stabilises on first access. Wrapped in try/except — a failure here
    must never block course reads.
    """
    if course.post_name:
        return course.post_name
    try:
        slug = generate_unique_slug(db, course.post_title or "", course_id=course.id)
        course.post_name = slug
        db.commit()
        db.refresh(course)
        return slug
    except Exception as exc:
        _slug_logger.warning("ensure_slug failed for course %s: %s", course.id, exc)
        try:
            db.rollback()
        except Exception:
            pass
        return build_default_slug(course)


class CourseService:
    """Course service class"""

    LOCKED_LESSON_FIELDS = ("content", "lesson_content", "lesson_video", "youtube_url", "video_url", "attachment_url",
                            "h5p_content_id", "game_id", "geogebra_applet_id", "three_d_model_id", "virtual_lab_sim")

    @staticmethod
    def lock_lesson(lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Strip everything a non-enrolled visitor must not receive. Title,
        duration, type and is_preview stay so the curriculum can be shown."""
        for k in CourseService.LOCKED_LESSON_FIELDS:
            if k in lesson_data:
                lesson_data[k] = "" if isinstance(lesson_data[k], str) else None
        lesson_data["is_locked"] = True
        return lesson_data

    @staticmethod
    def format_course_response(course: Course, is_enrolled: bool = False, enrollment = None, db: Session = None,
                               full_access: Optional[bool] = None) -> Dict[str, Any]:
        """
        Format course data for API response.

        full_access (public-preview lock, 2026-09-05): when False, lessons that are
        not marked `lesson_preview` are returned WITHOUT media/content handles and
        with is_locked=True. Defaults to is_enrolled; callers pass True for the
        course owner / admin so the editor keeps working.
        """
        if full_access is None:
            full_access = bool(is_enrolled)
        # Parse JSON fields safely
        try:
            requirements = json.loads(course.course_requirements) if course.course_requirements else []
            # Ensure it's a list, not a dict
            if isinstance(requirements, dict):
                requirements = []
        except:
            requirements = []

        try:
            benefits = json.loads(course.course_benefits) if course.course_benefits else []
            # Ensure it's a list, not a dict
            if isinstance(benefits, dict):
                benefits = []
        except:
            benefits = []

        try:
            tags = json.loads(course.course_tags) if course.course_tags else []
            # Ensure it's a list
            if isinstance(tags, dict):
                tags = []
        except:
            tags = []

        # FAQ field doesn't exist in current model
        faq = []

        # Resolve h5p_content_id (integer PK, internal) -> public_id (opaque
        # hex string, the only handle the H5P frontend/API accept) for every
        # H5P-typed lesson in this course, in one query. Lesson.h5p_content_id
        # alone is useless to the frontend player (H5PLesson/h5p-player.html
        # route on public_id, matching app/routers/h5p.py's URL scheme) — the
        # lesson response never embedded this before H5P existed, so this is
        # additive, not a behavior change for non-H5P lessons.
        h5p_content_ids = {
            lesson.h5p_content_id for lesson in course.lessons if getattr(lesson, "h5p_content_id", None)
        }
        h5p_public_id_by_content_id: Dict[int, str] = {}
        if h5p_content_ids and db:
            from app.models.h5p import H5PContent
            rows = db.query(H5PContent.id, H5PContent.public_id).filter(
                H5PContent.id.in_(h5p_content_ids)
            ).all()
            h5p_public_id_by_content_id = {row.id: row.public_id for row in rows}

        # Learning games (plan Task 6, mirrors the H5P prefetch above): resolve
        # Lesson.game_id -> Game.title for every game-typed lesson in this
        # course, in one query.
        game_ids = {
            lesson.game_id for lesson in course.lessons if getattr(lesson, "game_id", None)
        }
        game_title_by_id: Dict[int, str] = {}
        if game_ids and db:
            from app.models.game import Game
            rows = db.query(Game.id, Game.title).filter(Game.id.in_(game_ids)).all()
            game_title_by_id = {row.id: row.title for row in rows}

        # Get lesson completion status if user is enrolled
        lessons_with_status = []
        if enrollment and db:
            from app.models.enrollment import LessonProgress
            for lesson in course.lessons:
                lesson_progress = db.query(LessonProgress).filter(
                    LessonProgress.enrollment_id == enrollment.id,
                    LessonProgress.lesson_id == lesson.id
                ).first()

                lesson_data = CourseService.format_lesson_info(lesson)
                lesson_data["is_completed"] = lesson_progress.progress_status == "completed" if lesson_progress else False
                lesson_data["is_locked"] = False
                lesson_data["h5p_public_id"] = h5p_public_id_by_content_id.get(lesson.h5p_content_id)
                lesson_data["game_id"] = lesson.game_id
                lesson_data["game_title"] = game_title_by_id.get(lesson.game_id)
                lessons_with_status.append(lesson_data)
        else:
            lessons_with_status = []
            for lesson in course.lessons:
                lesson_data = CourseService.format_lesson_info(lesson)
                lesson_data["h5p_public_id"] = h5p_public_id_by_content_id.get(lesson.h5p_content_id)
                lesson_data["game_id"] = lesson.game_id
                lesson_data["game_title"] = game_title_by_id.get(lesson.game_id)
                lesson_data["is_locked"] = False
                if not full_access and not lesson.lesson_preview:
                    CourseService.lock_lesson(lesson_data)
                lessons_with_status.append(lesson_data)

        return {
            "id": course.id,
            "slug": course.post_name or build_default_slug(course),
            "title": course.post_title,
            "description": course.post_content or "",
            "content": course.post_content or "",
            "excerpt": course.post_excerpt or "",
            "thumbnail": course.course_thumbnail or "",
            "intro_video": course.course_intro_video or "",
            "price": float(course.course_price) if course.course_price else 0,
            # align with pricing.is_on_sale() after merge
            "sale_price": float(course.course_sale_price) if course.course_sale_price and 0 < course.course_sale_price < (course.course_price or 0) else None,
            "level": course.course_level or "beginner",
            "category": course.course_category or "Course",
            "duration": int(course.course_duration) if course.course_duration and str(course.course_duration).isdigit() else 0,
            "language": course.course_language or "English",
            # Consumed by the course-detail "Who this course is for" block and by
            # the instructor/admin edit form — both read course_target_audience.
            "course_target_audience": course.course_target_audience or "",
            "target_audience": course.course_target_audience or "",
            "course_type": course.course_type or "",
            "requirements": requirements,
            "benefits": benefits,
            "tags": tags,
            "faq": faq,
            "instructor": {
                "id": course.instructor.id if course.instructor else 0,
                "name": course.instructor.display_name if course.instructor else "Unknown",
                "avatar": (course.instructor.profile.profile_photo or "") if course.instructor and course.instructor.profile else ""
            },
            "lessons": lessons_with_status,
            "quizzes": [CourseService.format_quiz_response(quiz) for quiz in course.quizzes],
            "assignments": [CourseService.format_assignment_response(assignment) for assignment in course.assignments],
            "stats": {
                "lessons": len(course.lessons),
                "quizzes": len(course.quizzes),
                "duration": sum([int(lesson.lesson_video_duration or 0) for lesson in course.lessons]),
                "students": course.total_enrollments or 0,
                "video_views": course.video_view_count or 0
            },
            "rating": course.average_rating or 0,
            "is_enrolled": is_enrolled,
            "enrollment_date": enrollment.enrollment_date if enrollment else None,
            "progress": enrollment.course_progress_percentage if enrollment else None,
            # The enrollment's own state. `progress` alone cannot express it:
            # a course can be marked complete while the stored percentage lags
            # (quiz/assignment weighting, admin release, legacy imports), and a
            # cancelled enrollment can carry a completion date. Without these
            # two fields the UI can only guess from the percentage, which is
            # why completed courses were showing up under "In Progress" and
            # "Not Started". `status` below is the COURSE's publish state and
            # is deliberately left alone — renaming it would break its readers.
            "completion_date": enrollment.completion_date if enrollment else None,
            "enrollment_status": enrollment.enrollment_status if enrollment else None,
            "status": course.post_status,
            "sections_meta": getattr(course, "course_sections_meta", "") or "",
            "num_offline_workshops": getattr(course, "num_offline_workshops", 0) or 0,
            "num_hours": getattr(course, "num_hours", 0) or 0,
            "institution": getattr(course, "institution", "") or "",
            "certificate_id": (
                int(course.certificate_template)
                if getattr(course, "certificate_template", "") and str(course.certificate_template).isdigit()
                else None
            ),
            "created_at": course.created_at,
            "updated_at": course.updated_at
        }

    @staticmethod
    def format_lesson_info(lesson: Lesson) -> Dict[str, Any]:
        """
        Format brief lesson data for course response (LessonInfo schema)
        """
        # Prefer uploaded video URL, fall back to YouTube URL
        video_url = lesson.lesson_video_url or getattr(lesson, 'lesson_youtube_url', "") or ""
        video_duration = int(lesson.lesson_video_duration) if lesson.lesson_video_duration else 0
        return {
            "id": lesson.id,
            "title": lesson.post_title,
            "content": lesson.post_content or "",
            "duration": video_duration,
            "video_duration": video_duration,
            "is_preview": bool(lesson.lesson_preview),
            "order": lesson.menu_order,
            "lesson_video": lesson.lesson_video_url or "",
            "youtube_url": getattr(lesson, 'lesson_youtube_url', "") or "",
            "video_url": video_url,
            "lesson_content": lesson.post_content or "",
            "attachment_url": getattr(lesson, "lesson_attachment_url", "") or "",
            "lesson_title": lesson.post_title,
            "course_id": lesson.post_parent,
            "created_at": lesson.created_at,
            "post_date": lesson.post_date,
            "lesson_content_type": getattr(lesson, "lesson_content_type", None) or "video",
            "h5p_content_id": getattr(lesson, "h5p_content_id", None),
            "game_id": getattr(lesson, "game_id", None),
            "geogebra_applet_id": getattr(lesson, "geogebra_applet_id", None),
            "three_d_model_id": getattr(lesson, "three_d_model_id", None),
            "virtual_lab_sim": getattr(lesson, "virtual_lab_sim", None),
        }

    @staticmethod
    def format_lesson_response(lesson: Lesson) -> Dict[str, Any]:
        """
        Format full lesson data for API response (LessonResponse schema)
        """
        return {
            "id": lesson.id,
            "title": lesson.post_title,
            "content": lesson.post_content or "",
            "video_url": lesson.lesson_video_url or "",
            "video_duration": int(lesson.lesson_video_duration) if lesson.lesson_video_duration else 0,
            "is_preview": bool(lesson.lesson_preview),
            "order": lesson.menu_order,
            "course_id": lesson.post_parent,
            "created_at": lesson.created_at,
            "updated_at": lesson.updated_at,
            "youtube_url": getattr(lesson, 'lesson_youtube_url', "") or "",
            "lesson_content_type": getattr(lesson, "lesson_content_type", None) or "video",
            "h5p_content_id": getattr(lesson, "h5p_content_id", None),
            "game_id": getattr(lesson, "game_id", None),
            "geogebra_applet_id": getattr(lesson, "geogebra_applet_id", None),
            "three_d_model_id": getattr(lesson, "three_d_model_id", None),
            "virtual_lab_sim": getattr(lesson, "virtual_lab_sim", None),
        }

    @staticmethod
    def format_quiz_response(quiz: Quiz) -> Dict[str, Any]:
        """
        Format quiz data for API response
        """
        return {
            "id": quiz.id,
            "title": quiz.post_title,
            "questions_count": len(quiz.questions) if quiz.questions else 0,
            "time_limit": quiz.quiz_time_limit,
            "created_at": quiz.created_at
        }

    @staticmethod
    def format_assignment_response(assignment) -> Dict[str, Any]:
        """
        Format assignment data for API response
        """
        return {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "total_points": assignment.total_points,
            "created_at": assignment.created_at
        }

    @staticmethod
    def passed_distinct_quizzes(db: Session, user_id: int, course_id: int):
        """DISTINCT passed-quiz counting shared by progress calculation and
        the certificate completion breakdown.

        A quiz counts as passed when the user has at least one ENDED attempt
        on it scoring ``earned_marks / total_marks`` at or above the quiz's
        passing grade. Counting is per DISTINCT quiz id — a quiz passed on
        several attempts is still one passed quiz (counting attempt rows
        inflated progress).

        Read-only: performs no writes and never commits, so write paths
        (``calculate_course_progress``) and readers (the certificate
        percentage columns) can both call it safely.

        Returns ``(passed_quiz_ids: set[int], total_quizzes: int)``.
        """
        quiz_rows = db.query(Quiz.id, Quiz.quiz_passing_grade).filter(
            Quiz.post_parent == course_id
        ).all()
        passing_grades = dict(quiz_rows)

        passed_quiz_ids = set()
        if passing_grades:
            for attempt in db.query(QuizAttempt).filter(
                QuizAttempt.user_id == user_id,
                QuizAttempt.course_id == course_id,
                QuizAttempt.attempt_status == "attempt_ended",
            ).all():
                if not attempt.total_marks or float(attempt.total_marks) <= 0:
                    continue
                grade = passing_grades.get(attempt.quiz_id)
                if grade is None:
                    # Attempt's quiz no longer belongs to this course.
                    continue
                percentage = (
                    float(attempt.earned_marks) / float(attempt.total_marks)
                ) * 100
                if percentage >= grade:
                    passed_quiz_ids.add(attempt.quiz_id)

        return passed_quiz_ids, len(quiz_rows)

    @staticmethod
    def calculate_course_progress(
        db: Session, enrollment: Enrollment, commit: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate student's progress in a course.

        ``commit=True`` (default) persists the recomputed tracker columns,
        runs the completion / regression transitions, and auto-issues the
        certificate on completion — preserving the behaviour every write
        path (lesson complete, quiz submit, grading, admin) relies on.

        ``commit=False`` is strictly READ-ONLY: nothing is written, no
        commit happens, and certificate issuance is skipped, so GET
        endpoints can report fresh progress numbers without side effects.
        """
        from app.models.assignment import Assignment, AssignmentSubmission

        course = enrollment.course

        # Get lesson progress. Count only lessons that are still part of the
        # course, deduped by lesson_id: progress rows for lessons removed
        # from the curriculum (or duplicated rows) used to inflate
        # completed_lessons above total_lessons, the min(100, ...) clamp then
        # reported 100%, but the completion equality check failed — student
        # saw a finished course that could never issue a certificate.
        lesson_progress = db.query(LessonProgress).filter(
            LessonProgress.enrollment_id == enrollment.id
        ).all()

        course_lesson_ids = {lesson.id for lesson in course.lessons}
        completed_lesson_ids = {
            lp.lesson_id for lp in lesson_progress
            if lp.progress_status == "completed" and lp.lesson_id in course_lesson_ids
        }
        completed_lessons = len(completed_lesson_ids)
        total_lessons = len(course_lesson_ids)

        # Get quiz attempts - calculate passed quizzes via the shared
        # read-only helper, so this service and the certificate completion
        # breakdown (CertificateService.course_completion_percentages) can
        # never drift apart on what "a passed quiz" means.
        passed_quiz_ids, total_quizzes = CourseService.passed_distinct_quizzes(
            db, enrollment.user_id, enrollment.course_id
        )
        completed_quizzes = len(passed_quiz_ids)

        # Get assignment submissions - calculate graded assignments
        all_assignments = db.query(Assignment).filter(
            Assignment.course_id == enrollment.course_id
        ).all()

        completed_assignments = 0
        if all_assignments:
            student_submissions = db.query(AssignmentSubmission).filter(
                AssignmentSubmission.user_id == enrollment.user_id,
                AssignmentSubmission.assignment_id.in_([a.id for a in all_assignments]),
                AssignmentSubmission.status == "graded"
            ).all()
            completed_assignments = len(student_submissions)

        total_assignments = len(all_assignments) if all_assignments else 0

        # Calculate overall progress, clamped to 100 so data anomalies
        # (e.g., extra passed attempts, deleted content) can never report
        # a percentage above 100.
        total_content = total_lessons + total_quizzes + total_assignments
        completed_content = completed_lessons + completed_quizzes + completed_assignments

        overall_progress = min(100, (completed_content / total_content * 100)) if total_content > 0 else 0

        # Check if course is completed.
        # Handles lesson-only courses (total_quizzes == 0, total_assignments == 0):
        # the two zero equalities (0 == 0) are trivially true, so completion
        # fires once all lessons are done. Same holds for quiz-only or
        # assignment-only courses. `total_content > 0` guards against the
        # empty-course edge case (no lessons, no quizzes, no assignments).
        is_completed = (completed_lessons == total_lessons and
                       completed_quizzes == total_quizzes and
                       completed_assignments == total_assignments and
                       total_content > 0)

        # Update enrollment progress + keep the tracker columns in sync so
        # the SPOC dashboard / analytics pages that read them directly (not
        # via this service) stay accurate. Skipped entirely in read-only
        # mode (commit=False) — a progress GET must not mutate anything.
        just_completed = False
        try:
            if commit:
                enrollment.course_progress_percentage = int(overall_progress)
                enrollment.completed_lessons = completed_lessons
                enrollment.total_lessons = total_lessons
                enrollment.completed_quizzes = completed_quizzes
                enrollment.total_quizzes = total_quizzes

                # `just_completed` drives the gamification award AFTER this
                # block's own db.commit() below (see that commit + the
                # award call that follows it) — never before. award()
                # only flushes, it does not own the transaction boundary
                # (post-review H1 fix), so calling it while this method's
                # own enrollment mutations are still uncommitted would risk
                # the reverse hazard: an award()-side failure rolling back
                # (or a caller-side flush error surfacing) before THIS
                # method's own commit ever ran. Mirrors how the certificate
                # auto-issue call below is sequenced after this commit.
                just_completed = is_completed and not enrollment.completion_date
                if just_completed:
                    # tz-aware to match the DateTime(timezone=True) column.
                    enrollment.completion_date = datetime.now(timezone.utc)
                    if enrollment.enrollment_status != "completed":
                        enrollment.enrollment_status = "completed"
                elif not is_completed and enrollment.enrollment_status == "completed":
                    # Course is no longer completed (e.g., content was added
                    # after completion, or a gate now blocks what used to
                    # count). Reset to enrolled state.
                    enrollment.enrollment_status = "enrolled"
                    enrollment.completion_date = None
                    enrollment.certificate_id = None
                    enrollment.certificate_url = None
                    # Any certificate issued against that now-revoked
                    # completion must stop verifying as authentic.
                    from app.models.certificate import (
                        IssuedCertificate,
                        COMPLETION_REGRESSED_INVALIDATION_REASON,
                    )
                    stale_certs = db.query(IssuedCertificate).filter(
                        IssuedCertificate.user_id == enrollment.user_id,
                        IssuedCertificate.course_id == enrollment.course_id,
                        IssuedCertificate.is_valid == True,  # noqa: E712
                    ).all()
                    for cert in stale_certs:
                        cert.is_valid = False
                        # Machine-readable marker, not free text: the revival
                        # branch in CertificateService.issue_certificate_for_enrollment
                        # resurrects ONLY certs invalidated with this exact
                        # reason — an admin revoke stays terminal.
                        cert.invalidation_reason = (
                            COMPLETION_REGRESSED_INVALIDATION_REASON
                        )
                        cert.invalidated_date = datetime.now(timezone.utc)

                db.commit()
        except Exception:
            db.rollback()
            raise

        # Gamification (spec D1): +100 XP on the FRESH transition to
        # completed only (just_completed, set above from the SAME
        # "not enrollment.completion_date" guard so this fires exactly once
        # per enrollment). Sequenced AFTER this method's own db.commit()
        # above — same reasoning as the certificate auto-issue call below —
        # so award()'s own flush + this call's own commit can never race
        # with, or be undone by, this method's enrollment mutation. Every
        # trigger site owns its own commit for the same reason (H1 review
        # fix); this one is that commit for the course-completion trigger.
        if commit and just_completed:
            try:
                from app.services.gamification_service import award as _award_xp
                _award_xp(
                    db, enrollment.user_id, "course_completed",
                    event_key=f"course:{enrollment.course_id}:completed:user:{enrollment.user_id}",
                    course_id=enrollment.course_id,
                    meta={"enrollment_id": enrollment.id},
                )
                db.commit()
            except Exception as game_err:
                _slug_logger.warning("Gamification award failed for course completion: %s", game_err)
                try:
                    db.rollback()
                except Exception:
                    pass

        # Auto-issue certificate exactly once, at the moment completion_date
        # transitions from NULL -> set. Best-effort — swallows errors.
        # Write path only: a read (commit=False) must never issue one.
        if commit and is_completed and enrollment.completion_date:
            try:
                from app.services.certificate_service import CertificateService
                CertificateService.issue_certificate_for_enrollment(db, enrollment)
            except Exception:
                # Never fail progress calc because cert issuance hiccupped.
                try:
                    db.rollback()
                except Exception:
                    pass

        return {
            "course_id": course.id,
            "student_id": enrollment.user_id,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "total_quizzes": total_quizzes,
            "completed_quizzes": completed_quizzes,
            "total_assignments": total_assignments,
            "completed_assignments": completed_assignments,
            "overall_progress": overall_progress,
            "last_accessed": enrollment.updated_at,
            "completion_date": enrollment.completion_date,
            "certificate_earned": is_completed,
            "completed_lesson_ids": [lp.lesson_id for lp in lesson_progress if lp.progress_status == "completed"]
        }

    @staticmethod
    def get_course_categories(db: Session) -> list:
        """
        Get all available course categories
        """
        categories = db.query(Course.course_category).distinct().all()
        return [cat[0] for cat in categories if cat[0]]

    @staticmethod
    def get_instructor_courses(db: Session, instructor_id: int, status: Optional[str] = None) -> list:
        """
        Get all courses for a specific instructor
        """
        query = db.query(Course).filter(Course.instructor_id == instructor_id)

        if status:
            query = query.filter(Course.course_status == status)

        return query.all()

    @staticmethod
    def update_lesson_order(db: Session, course_id: int, lesson_orders: Dict[int, int]) -> bool:
        """
        Update the order of lessons in a course
        """
        try:
            for lesson_id, new_order in lesson_orders.items():
                lesson = db.query(Lesson).filter(
                    Lesson.id == lesson_id,
                    Lesson.post_parent == course_id
                ).first()

                if lesson:
                    lesson.menu_order = new_order

            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
