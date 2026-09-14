"""
Video watch progress router.

Refactored to route all writes through the LessonProgress ORM model so that
video-watch progress participates in the same bookkeeping as
`mark-lesson-complete` (backend/app/routers/courses.py):

  * progress updates course_progress_percentage via CourseService
  * crossing the 90% watch threshold marks the lesson completed,
    which feeds into the certificate auto-issue path

TODO: the legacy raw `video_progress` table is no longer written to by this
router. It may still be read by other consumers or exist in the DB. It is
intentionally NOT dropped here (no migration ownership in this change). Audit
other consumers and schedule a follow-up migration to remove it.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.services.course_service import CourseService
from app.models.enrollment import Enrollment, LessonProgress, WatchSession
from app.models.course import Lesson

logger = logging.getLogger(__name__)

router = APIRouter()

# Completion threshold for video watch -> lesson completed
VIDEO_COMPLETION_THRESHOLD = 0.9


class ProgressUpdate(BaseModel):
    lesson_id: int
    course_id: int
    watched_seconds: float
    total_seconds: float


class WatchEvent(BaseModel):
    """Issue 8: a single video-watch lifecycle event.

    event is one of: 'started', 'paused', 'resumed', 'completed'.
    duration_seconds is the watch time accumulated during the segment that
    just ended (e.g. between play and pause). position_seconds is the
    player's current offset, captured for the viewing-history timeline.
    """
    lesson_id: int
    course_id: int
    event: str
    duration_seconds: float = 0
    position_seconds: float = 0


def _get_user_enrollment(db: Session, user_id: int, course_id: int) -> Enrollment:
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user_id,
        Enrollment.course_id == course_id,
    ).first()
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course",
        )
    return enrollment


@router.post("/save")
async def save_progress(
    data: ProgressUpdate,
    current_user=Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    # Verify enrollment ownership
    enrollment = _get_user_enrollment(db, current_user.id, data.course_id)

    # Verify lesson belongs to this course (Lesson.post_parent is the course FK)
    lesson = db.query(Lesson).filter(
        Lesson.id == data.lesson_id,
        Lesson.post_parent == data.course_id,
    ).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found in this course",
        )

    watched = max(0, int(data.watched_seconds or 0))
    total = max(0, int(data.total_seconds or 0))
    pct = int((watched / total) * 100) if total > 0 else 0
    is_completed = total > 0 and (watched / total) >= VIDEO_COMPLETION_THRESHOLD

    try:
        # Upsert LessonProgress by (enrollment_id, user_id, lesson_id)
        lp = db.query(LessonProgress).filter(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == data.lesson_id,
        ).first()

        newly_completed = False
        if lp is None:
            lp = LessonProgress(
                user_id=current_user.id,
                course_id=data.course_id,
                lesson_id=data.lesson_id,
                enrollment_id=enrollment.id,
                progress_status="completed" if is_completed else "started",
                video_current_time=watched,
                video_total_duration=total,
                video_completion_percentage=pct,
                completion_date=datetime.now(timezone.utc) if is_completed else None,
            )
            db.add(lp)
            if is_completed:
                newly_completed = True
        else:
            # Never let watched time/duration regress on the same lesson
            lp.video_current_time = max(lp.video_current_time or 0, watched)
            if total > 0:
                lp.video_total_duration = total
            lp.video_completion_percentage = max(lp.video_completion_percentage or 0, pct)

            if is_completed and lp.progress_status != "completed":
                lp.progress_status = "completed"
                lp.completion_date = datetime.now(timezone.utc)
                newly_completed = True

        # Note: enrollment.completed_lessons and total_lessons are
        # recomputed from scratch by CourseService.calculate_course_progress
        # below, so we don't manually increment here.

        db.flush()

        # Drive course_progress_percentage + certificate auto-issue path.
        # calculate_course_progress commits internally and rewrites the four
        # counter columns (completed_lessons, total_lessons, completed_quizzes,
        # total_quizzes) every call.
        CourseService.calculate_course_progress(db, enrollment)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    # Gamification (review finding I3): crossing the 90% watch threshold is a
    # real lesson completion and must award the same +10 XP the explicit
    # "mark complete" button awards (courses.py's mark_lesson_complete) —
    # otherwise a student who finishes a course purely by watching videos
    # earns no lesson XP at all.
    #
    # The event_key is IDENTICAL to the button path's
    # (`lesson:{id}:completed:user:{uid}`) on purpose: the XP ledger is
    # idempotent on event_key, so whichever path fires first wins and the
    # other converges to a no-op. A student who watches past 90% AND then
    # clicks "mark complete" is awarded exactly once.
    #
    # Best-effort with its own commit, sequenced strictly AFTER
    # calculate_course_progress's commit — same ordering rationale as the
    # button path: award() owns none of the caller's transaction boundary,
    # so its flush/rollback must never be able to touch this request's
    # still-uncommitted lesson-progress state.
    if newly_completed:
        try:
            from app.services.gamification_service import award as _award_xp
            _award_xp(
                db, current_user.id, "lesson_completed",
                event_key=f"lesson:{data.lesson_id}:completed:user:{current_user.id}",
                course_id=data.course_id,
                meta={"lesson_id": data.lesson_id, "source": "video_threshold"},
            )
            db.commit()
        except Exception as game_err:
            logger.warning(
                "Gamification award failed for video-threshold lesson complete: %s",
                game_err,
            )
            try:
                db.rollback()
            except Exception:
                pass

    return JSONResponse({
        "success": True,
        "completed": bool(is_completed),
        "watched_seconds": float(lp.video_current_time or 0),
        "total_seconds": float(lp.video_total_duration or 0),
        "completion_percentage": int(lp.video_completion_percentage or 0),
    })


@router.get("/get/{lesson_id}")
async def get_progress(
    lesson_id: int,
    current_user=Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    lp = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.lesson_id == lesson_id,
    ).first()
    if not lp:
        return JSONResponse({
            "watched_seconds": 0,
            "total_seconds": 0,
            "is_completed": False,
        })
    return JSONResponse({
        "watched_seconds": float(lp.video_current_time or 0),
        "total_seconds": float(lp.video_total_duration or 0),
        "is_completed": lp.progress_status == "completed",
    })


@router.get("/course/{course_id}")
async def get_course_progress(
    course_id: int,
    current_user=Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    # Verify enrollment ownership
    enrollment = _get_user_enrollment(db, current_user.id, course_id)

    rows = db.query(LessonProgress).filter(
        LessonProgress.enrollment_id == enrollment.id,
        LessonProgress.user_id == current_user.id,
    ).all()

    return JSONResponse({
        "progress": {
            r.lesson_id: {
                "watched_seconds": float(r.video_current_time or 0),
                "is_completed": r.progress_status == "completed",
            }
            for r in rows
        }
    })


@router.post("/watch-event")
async def record_watch_event(
    data: WatchEvent,
    current_user=Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Issue 8: record a video-watch lifecycle event (started / paused /
    resumed / completed) for the Student Activity panel.

    Each call writes one WatchSession row. The frontend fires this on the
    matching player events; the admin Student Activity endpoints aggregate
    these rows into time-spent, session count, last-active and the full
    viewing history.
    """
    # Verify enrollment ownership so a user can't log activity for courses
    # they haven't joined.
    enrollment = _get_user_enrollment(db, current_user.id, data.course_id)

    lesson = db.query(Lesson).filter(
        Lesson.id == data.lesson_id,
        Lesson.post_parent == data.course_id,
    ).first()
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found in this course",
        )

    event = (data.event or "").strip().lower()
    allowed = {"started", "paused", "resumed", "completed"}
    if event not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"event must be one of {sorted(allowed)}",
        )

    duration = max(0, int(data.duration_seconds or 0))
    position = max(0, int(data.position_seconds or 0))

    now = datetime.now(timezone.utc)
    session = WatchSession(
        user_id=current_user.id,
        course_id=data.course_id,
        lesson_id=data.lesson_id,
        event=event,
        duration_seconds=duration,
        position_seconds=position,
        started_at=now,
        ended_at=now if event in {"paused", "completed"} else None,
    )
    db.add(session)

    # Bump the course video-view counter too — a 'started' event is the
    # most reliable signal that a video was actually played.
    if event == "started":
        course = enrollment.course
        if course is not None:
            course.video_view_count = (getattr(course, "video_view_count", 0) or 0) + 1

    db.commit()

    # SILEOS event spine: watch events as xAPI statements (best-effort,
    # post-commit — analytics must never break the learner action).
    from app.services.xapi_service import emit_statement
    emit_statement(
        actor_user_id=current_user.id,
        verb=event if event in ("paused", "resumed") else ("watched" if event in ("started", "heartbeat") else "completed"),
        object_type="lesson",
        object_id=data.lesson_id,
        result={"duration_seconds": duration, "position_seconds": position},
        context={"course_id": enrollment.course_id, "source": "watch-event"},
    )

    return JSONResponse({"success": True, "recorded": event})

