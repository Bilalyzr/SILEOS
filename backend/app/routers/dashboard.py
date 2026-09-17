from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc, or_, Integer
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone, date

from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.course import Course, CourseReview
from app.models.enrollment import Enrollment, LessonProgress
from app.models.payment import Payment, Order, OrderItem, OrderStatus, PaymentStatus
from app.models.internship import InternshipVoucher, Internship, InternshipAttendance
from app.models.quiz import Quiz, QuizAttempt
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.certificate import IssuedCertificate

router = APIRouter()


def get_recent_activities(user_id: int, db: Session, limit: int = 10) -> List[Dict]:
    """
    Get recent activities for a student
    Shows recent enrollments
    """
    activities = []

    # Get recent enrollments (last 30 days)
    recent_enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user_id,
        Enrollment.enrollment_date >= datetime.now() - timedelta(days=30)
    ).order_by(desc(Enrollment.enrollment_date)).limit(limit).all()

    for enrollment in recent_enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            activities.append({
                "type": "enrollment",
                "action": "Enrolled in course",
                "title": f"Enrolled in {course.post_title}",
                "course": course.post_title,
                "description": "Started learning",
                "timestamp": enrollment.enrollment_date.strftime("%Y-%m-%d %H:%M") if enrollment.enrollment_date else "Recently",
                "time": get_relative_time(enrollment.enrollment_date) if enrollment.enrollment_date else "Recently"
            })

    return activities


def get_relative_time(dt: datetime) -> str:
    """Convert datetime to relative time string"""
    if not dt:
        return "Recently"

    # Make both datetimes timezone-aware for comparison
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    # If dt has timezone but now doesn't, make dt naive
    if dt.tzinfo and not now.tzinfo:
        dt = dt.replace(tzinfo=None)
    diff = now - dt

    if diff.days > 30:
        return f"{diff.days // 30} month{'s' if diff.days // 30 > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


@router.get("/student")
async def get_student_dashboard(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get student dashboard statistics
    """
    # Get enrolled courses count
    enrolled_count = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).count()

    # Get completed courses count
    completed_count = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.enrollment_status == "completed"
    ).count()

    # Calculate total learning hours from actual course durations
    total_hours = 0
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).all()

    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course and course.course_duration:
            try:
                # Try to parse hours from duration string (e.g., "20 hours", "3 weeks")
                duration_str = str(course.course_duration).lower()
                if 'hour' in duration_str:
                    hours = int(''.join(filter(str.isdigit, duration_str)))
                    total_hours += hours
                elif 'week' in duration_str:
                    weeks = int(''.join(filter(str.isdigit, duration_str)))
                    total_hours += weeks * 10  # Estimate 10 hours per week
            except:
                pass

    # Get certificates count (completed courses)
    certificates_count = completed_count

    # Get enrolled courses with details
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).limit(10).all()

    enrolled_courses = []
    for enrollment in enrollments:
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if course:
            # Get real lesson counts from enrollment
            total_lessons = enrollment.total_lessons or 0
            completed_lessons = enrollment.completed_lessons or 0

            # Get instructor name
            instructor = db.query(User).filter(User.id == course.post_author).first()
            instructor_name = instructor.display_name if instructor else "Instructor"

            # Calculate average rating from reviews
            reviews = db.query(func.avg(func.cast(CourseReview.rating, Integer))).filter(
                CourseReview.course_id == course.id,
                CourseReview.review_status == "approved"
            ).scalar()
            avg_rating = float(reviews) if reviews else 0.0

            # NULL-safe: a freshly enrolled course can have a NULL progress.
            # Comparing None < 100 raises TypeError and 500s the whole endpoint,
            # which made the student dashboard show "Error loading dashboard".
            progress_pct = enrollment.course_progress_percentage or 0
            enrolled_courses.append({
                "id": course.id,
                # These three are required (non-null) on the Flutter model — keep
                # them as strings so fromJson never chokes on a null.
                "title": course.post_title or "Untitled Course",
                "thumbnail": course.course_thumbnail or "/api/placeholder/300/200",
                "progress": progress_pct,
                "totalLessons": total_lessons,
                "completedLessons": completed_lessons,
                "instructor": instructor_name,
                "rating": round(avg_rating, 1),
                "nextLesson": "Continue Learning" if progress_pct < 100 else "Completed",
                "enrollment_status": enrollment.enrollment_status or "enrolled"
            })

    # Get recent activities
    recent_activity = get_recent_activities(current_user.id, db, limit=10)

    # Calculate weekly learning goal (based on this week's activity)
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Count lessons completed this week
    lessons_this_week = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id,
        LessonProgress.progress_status == "completed",
        LessonProgress.completion_date >= week_start
    ).count()

    # Calculate estimated hours from lessons completed this week
    # Assume average 30 minutes per lesson
    hours_this_week = lessons_this_week * 0.5

    # Set a goal based on enrolled courses (aim for 1 hour per enrolled course per week)
    weekly_goal_hours = max(enrolled_count * 1, 5)  # Minimum 5 hours
    weekly_progress_percentage = min(int((hours_this_week / weekly_goal_hours) * 100), 100) if weekly_goal_hours > 0 else 0

    # Internship data for student dashboard
    internship_vouchers = db.query(InternshipVoucher).filter(
        InternshipVoucher.buyer_user_id == current_user.id
    ).all()

    internships = []
    for voucher in internship_vouchers:
        internship = db.query(Internship).filter(Internship.id == voucher.internship_id).first()
        if internship:
            # Get attendance count for this internship
            attendance_count = db.query(func.count(InternshipAttendance.id)).filter(
                InternshipAttendance.internship_id == internship.id,
                InternshipAttendance.user_id == current_user.id,
                InternshipAttendance.status.in_(["present", "late"])
            ).scalar() or 0

            # Get hired company name (from manual override OR accepted interest)
            hired_company_name = None
            if voucher.hired_by_company_id:
                # Admin manually assigned company
                from app.models.company import Company
                company = db.query(Company).filter(Company.id == voucher.hired_by_company_id).first()
                hired_company_name = company.name if company else None
            else:
                # Check if student accepted a company's interest
                from app.models.company import CompanyInterest, Company
                accepted_interest = db.query(CompanyInterest).filter(
                    CompanyInterest.candidate_user_id == current_user.id,
                    CompanyInterest.status == 'accepted'
                ).first()
                if accepted_interest:
                    company = db.query(Company).filter(Company.id == accepted_interest.company_id).first()
                    hired_company_name = company.name if company else None

            internships.append({
                "id": internship.id,
                "title": internship.title,
                "voucher_code": voucher.code,
                "status": voucher.status,
                "redeemed_course_title": voucher.redeemed_course.post_title if voucher.redeemed_course else None,
                "attendance_days": attendance_count,
                "hired_company": hired_company_name,
                "created_at": voucher.created_at.isoformat() if voucher.created_at else None
            })

    return {
        "stats": {
            "enrolled_courses": enrolled_count,
            "completed_courses": completed_count,
            "total_hours": total_hours,
            "certificates": certificates_count
        },
        "enrolled_courses": enrolled_courses,
        "recent_activity": recent_activity,
        "internships": internships,
        "weekly_goal": {
            "goal_hours": weekly_goal_hours,
            "completed_hours": round(hours_this_week, 1),
            "progress_percentage": weekly_progress_percentage,
            "lessons_completed": lessons_this_week
        }
    }


# ---------------------------------------------------------------------------
# Student Analytics Report
# ---------------------------------------------------------------------------

# period key -> lookback window in days (None = lifetime)
ANALYTICS_PERIODS: Dict[str, Optional[int]] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "1y": 365,
    "all": None,
}

# Fallback used only when a lesson has no recorded watch/read time at all.
ASSUMED_MINUTES_PER_LESSON = 30


def _as_float(value: Any, default: float = 0.0) -> float:
    """Decimal / None / str -> float, never raises."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_date(value: Any) -> Optional[date]:
    """Normalise a DB value (date / datetime / ISO string) to a plain date."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (TypeError, ValueError):
        return None


def _compute_streaks(active_days: List[date]) -> Dict[str, int]:
    """Current + longest run of consecutive active days.

    The current streak is only "alive" if the most recent activity was today
    or yesterday — otherwise it has been broken and reads 0.
    """
    if not active_days:
        return {"current_streak": 0, "longest_streak": 0}

    days = sorted(set(active_days))
    longest = 1
    run = 1
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    today = datetime.now(timezone.utc).date()
    current = 0
    if (today - days[-1]).days <= 1:
        current = 1
        for prev, curr in zip(reversed(days[:-1]), reversed(days[1:])):
            if (curr - prev).days == 1:
                current += 1
            else:
                break

    return {"current_streak": current, "longest_streak": longest}


def _get_streaks(db: Session, user_id: int, active_days: List[date]) -> Dict[str, int]:
    """Streak unification (spec D4): gamification_service.touch_streak is
    THE streak implementation now. Reads UserGameStats.current_streak/
    longest_streak when a stats row exists; `_compute_streaks` above is kept
    ONLY as the fallback for a user with no stats row yet (e.g. no
    gamification-triggering activity has happened since this feature
    shipped), so this endpoint's shape never changes for existing callers."""
    from app.services.gamification_service import get_streak_for_user

    streaks = get_streak_for_user(db, user_id)
    if streaks is not None:
        return streaks
    return _compute_streaks(active_days)


def _lesson_minutes(row: Any) -> float:
    """Minutes of study time recorded against a single LessonProgress row.

    `video_current_time` is the last playback position in seconds, which for a
    finished lesson approximates the time watched — the closest thing the schema
    records. Lessons with neither a video position nor reading time fall back to
    a flat estimate so completed-but-untracked lessons still count as effort.
    """
    watched = (row.video_current_time or 0) / 60.0   # seconds -> minutes
    read = float(row.reading_time or 0)              # already minutes
    minutes = watched + read
    if minutes <= 0 and (row.progress_status or "") == "completed":
        minutes = ASSUMED_MINUTES_PER_LESSON
    return minutes


def _build_insights(summary: Dict[str, Any], courses: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Plain-language takeaways derived from the numbers above. Purely
    presentational — the frontend renders these as the report's narrative."""
    insights: List[Dict[str, str]] = []

    if summary["completed_courses"] > 0:
        insights.append({
            "tone": "positive",
            "title": f"{summary['completed_courses']} course"
                     f"{'' if summary['completed_courses'] == 1 else 's'} completed",
            "detail": f"You've earned {summary['certificates_earned']} certificate"
                      f"{'' if summary['certificates_earned'] == 1 else 's'} so far. "
                      f"Your overall completion rate is {summary['completion_rate']}%.",
        })

    if summary["current_streak"] >= 2:
        insights.append({
            "tone": "positive",
            "title": f"{summary['current_streak']}-day learning streak",
            "detail": f"Your longest streak is {summary['longest_streak']} days. "
                      "Keep going to beat your record.",
        })
    elif summary["active_days"] == 0:
        insights.append({
            "tone": "warning",
            "title": "No study activity in this period",
            "detail": "Complete a lesson to start building your learning streak.",
        })

    if summary["quizzes_attempted"] > 0:
        tone = "positive" if summary["avg_quiz_score"] >= 70 else "warning"
        insights.append({
            "tone": tone,
            "title": f"Average quiz score {summary['avg_quiz_score']}%",
            "detail": f"Across {summary['quizzes_attempted']} attempt"
                      f"{'' if summary['quizzes_attempted'] == 1 else 's'}, "
                      f"you passed {summary['quizzes_passed']}.",
        })

    stalled = [c for c in courses if 0 < c["progress"] < 100 and c["days_since_activity"] is not None
               and c["days_since_activity"] >= 14]
    if stalled:
        target = min(stalled, key=lambda c: 100 - c["progress"])
        insights.append({
            "tone": "warning",
            "title": f"'{target['title']}' has been idle for {target['days_since_activity']} days",
            "detail": f"You're {100 - target['progress']}% away from finishing it — "
                      "it's your quickest win right now.",
        })

    not_started = [c for c in courses if c["progress"] == 0]
    if not_started:
        insights.append({
            "tone": "neutral",
            "title": f"{len(not_started)} course{'' if len(not_started) == 1 else 's'} not started",
            "detail": "Opening the first lesson is usually enough to build momentum.",
        })

    return insights


@router.get("/student/analytics")
async def get_student_analytics(
    period: str = Query("90d", description="7d | 30d | 90d | 180d | 1y | all"),
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Analytics report for the logged-in student.

    Everything here is derived from real rows (enrollments, lesson progress,
    quiz attempts, assignment submissions, issued certificates) — no mock
    series. `period` only scopes the time-boxed sections (activity timeline,
    quiz/assignment history, active days & streaks); lifetime totals such as
    enrolled/completed courses and certificates are always all-time so the
    report header doesn't change meaning when the filter moves.
    """
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Use one of: {', '.join(ANALYTICS_PERIODS)}",
        )

    window_days = ANALYTICS_PERIODS[period]
    now = datetime.now(timezone.utc)
    today = now.date()
    since = now - timedelta(days=window_days) if window_days else None

    # ---- Enrollments + course metadata (one pass, no N+1) -----------------
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).all()
    course_ids = [e.course_id for e in enrollments]

    courses_by_id: Dict[int, Course] = {}
    if course_ids:
        courses_by_id = {
            c.id: c for c in db.query(Course).filter(Course.id.in_(course_ids)).all()
        }

    instructor_ids = {c.post_author for c in courses_by_id.values() if c.post_author}
    instructors_by_id: Dict[int, str] = {}
    if instructor_ids:
        instructors_by_id = {
            u.id: (u.display_name or "Instructor")
            for u in db.query(User).filter(User.id.in_(instructor_ids)).all()
        }

    # ---- Lesson progress --------------------------------------------------
    lesson_rows = db.query(LessonProgress).filter(
        LessonProgress.user_id == current_user.id
    ).all()

    completed_lessons_all = [r for r in lesson_rows if (r.progress_status or "") == "completed"]

    # Study minutes per course + per day (attributed to the completion day).
    minutes_by_course: Dict[int, float] = {}
    minutes_by_day: Dict[date, float] = {}
    lessons_by_day: Dict[date, int] = {}
    last_activity_by_course: Dict[int, date] = {}

    for row in lesson_rows:
        minutes = _lesson_minutes(row)
        minutes_by_course[row.course_id] = minutes_by_course.get(row.course_id, 0.0) + minutes

        day = _as_date(row.completion_date) or _as_date(row.updated_at) or _as_date(row.created_at)
        if not day:
            continue
        prev = last_activity_by_course.get(row.course_id)
        if prev is None or day > prev:
            last_activity_by_course[row.course_id] = day

        if since is not None and day < since.date():
            continue
        minutes_by_day[day] = minutes_by_day.get(day, 0.0) + minutes
        if (row.progress_status or "") == "completed":
            lessons_by_day[day] = lessons_by_day.get(day, 0) + 1

    # ---- Quiz attempts ----------------------------------------------------
    quiz_query = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.attempt_status == "attempt_ended",
    )
    if since is not None:
        quiz_query = quiz_query.filter(QuizAttempt.attempt_started_at >= since)
    quiz_attempts = quiz_query.order_by(desc(QuizAttempt.attempt_started_at)).all()

    quiz_titles: Dict[int, str] = {}
    quiz_pass_marks: Dict[int, int] = {}
    attempt_quiz_ids = {a.quiz_id for a in quiz_attempts}
    if attempt_quiz_ids:
        for q in db.query(Quiz).filter(Quiz.id.in_(attempt_quiz_ids)).all():
            quiz_titles[q.id] = q.post_title or "Quiz"
            quiz_pass_marks[q.id] = q.quiz_passing_grade or 80

    quiz_history: List[Dict[str, Any]] = []
    quiz_scores_by_course: Dict[int, List[float]] = {}
    quizzes_passed = 0

    for attempt in quiz_attempts:
        total = _as_float(attempt.total_marks)
        earned = _as_float(attempt.earned_marks)
        score = round((earned / total) * 100, 1) if total > 0 else 0.0
        pass_mark = quiz_pass_marks.get(attempt.quiz_id, 80)
        passed = score >= pass_mark
        if passed:
            quizzes_passed += 1
        quiz_scores_by_course.setdefault(attempt.course_id, []).append(score)

        if len(quiz_history) < 20:
            course = courses_by_id.get(attempt.course_id)
            quiz_history.append({
                "attempt_id": attempt.attempt_id,
                "quiz_title": quiz_titles.get(attempt.quiz_id, "Quiz"),
                "course_title": course.post_title if course else "Course",
                "score": score,
                "passing_grade": pass_mark,
                "passed": passed,
                "earned_marks": earned,
                "total_marks": total,
                "attempted_at": attempt.attempt_started_at.isoformat() if attempt.attempt_started_at else None,
            })

    quiz_scores = [h for a in quiz_scores_by_course.values() for h in a]
    avg_quiz_score = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0.0

    # ---- Assignment submissions ------------------------------------------
    submission_query = db.query(AssignmentSubmission, Assignment).join(
        Assignment, AssignmentSubmission.assignment_id == Assignment.id
    ).filter(AssignmentSubmission.user_id == current_user.id)
    if since is not None:
        submission_query = submission_query.filter(AssignmentSubmission.submitted_at >= since)
    submission_rows = submission_query.order_by(desc(AssignmentSubmission.submitted_at)).all()

    assignment_history: List[Dict[str, Any]] = []
    assignment_percentages: List[float] = []

    for submission, assignment in submission_rows:
        total_points = assignment.total_points or 0
        grade = submission.grade
        percentage = None
        if grade is not None and total_points > 0:
            percentage = round((_as_float(grade) / total_points) * 100, 1)
            assignment_percentages.append(percentage)

        status_value = submission.status.value if hasattr(submission.status, "value") else str(submission.status or "")
        if len(assignment_history) < 20:
            course = courses_by_id.get(assignment.course_id)
            assignment_history.append({
                "id": submission.id,
                "title": assignment.title,
                "course_title": course.post_title if course else "Course",
                "status": status_value,
                "grade": _as_float(grade) if grade is not None else None,
                "total_points": total_points,
                "percentage": percentage,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "graded_at": submission.graded_at.isoformat() if submission.graded_at else None,
            })

    graded_count = len(assignment_percentages)
    avg_assignment_score = (
        round(sum(assignment_percentages) / graded_count, 1) if graded_count else 0.0
    )

    # ---- Certificates (all-time) -----------------------------------------
    certificate_rows = db.query(IssuedCertificate).filter(
        IssuedCertificate.user_id == current_user.id,
        or_(IssuedCertificate.is_valid.is_(None), IssuedCertificate.is_valid.is_(True)),
    ).order_by(desc(IssuedCertificate.created_at)).all()

    cert_course_ids = [c.course_id for c in certificate_rows if c.course_id not in courses_by_id]
    if cert_course_ids:
        for c in db.query(Course).filter(Course.id.in_(cert_course_ids)).all():
            courses_by_id[c.id] = c

    certificates: List[Dict[str, Any]] = []
    certificate_course_ids = set()
    for cert in certificate_rows:
        certificate_course_ids.add(cert.course_id)
        course = courses_by_id.get(cert.course_id)
        certificates.append({
            "id": cert.id,
            "course_id": cert.course_id,
            "course_title": (course.post_title if course else None) or cert.certificate_title or "Course",
            "issued_at": cert.created_at.isoformat() if cert.created_at else None,
            "completion_date": cert.completion_date.isoformat() if cert.completion_date else None,
            "secure_certificate_id": cert.secure_certificate_id,
            "certificate_hash": cert.certificate_hash,
        })

    # ---- Per-course breakdown --------------------------------------------
    course_breakdown: List[Dict[str, Any]] = []
    for enrollment in enrollments:
        course = courses_by_id.get(enrollment.course_id)
        if not course:
            continue

        progress = int(enrollment.course_progress_percentage or 0)
        scores = quiz_scores_by_course.get(enrollment.course_id, [])
        last_active = last_activity_by_course.get(enrollment.course_id)

        course_breakdown.append({
            "course_id": course.id,
            "title": course.post_title or "Untitled Course",
            "slug": course.post_name or "",
            "thumbnail": course.course_thumbnail or "/api/placeholder/300/200",
            "instructor": instructors_by_id.get(course.post_author, "Instructor"),
            "progress": progress,
            "completed_lessons": enrollment.completed_lessons or 0,
            "total_lessons": enrollment.total_lessons or 0,
            "hours": round(minutes_by_course.get(course.id, 0.0) / 60.0, 1),
            "avg_quiz_score": round(sum(scores) / len(scores), 1) if scores else None,
            "status": "completed" if progress >= 100 else ("in_progress" if progress > 0 else "not_started"),
            "has_certificate": course.id in certificate_course_ids,
            "enrolled_at": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "completed_at": enrollment.completion_date.isoformat() if enrollment.completion_date else None,
            "last_activity": last_active.isoformat() if last_active else None,
            "days_since_activity": (today - last_active).days if last_active else None,
        })

    course_breakdown.sort(key=lambda c: (c["status"] != "in_progress", -c["progress"]))

    # ---- Activity timeline (one row per day in the window) ----------------
    timeline_days = window_days or max(
        (today - min(minutes_by_day)).days + 1 if minutes_by_day else 30, 30
    )
    timeline_days = min(timeline_days, 365)

    activity_timeline: List[Dict[str, Any]] = []
    for offset in range(timeline_days - 1, -1, -1):
        day = today - timedelta(days=offset)
        activity_timeline.append({
            "date": day.isoformat(),
            "label": day.strftime("%d %b"),
            "lessons": lessons_by_day.get(day, 0),
            "hours": round(minutes_by_day.get(day, 0.0) / 60.0, 2),
        })

    # ---- Monthly completions (last 12 months, all-time source data) -------
    monthly: Dict[str, int] = {}
    for enrollment in enrollments:
        completed_on = _as_date(enrollment.completion_date)
        if completed_on:
            monthly[completed_on.strftime("%Y-%m")] = monthly.get(completed_on.strftime("%Y-%m"), 0) + 1

    monthly_completions: List[Dict[str, Any]] = []
    cursor = date(today.year, today.month, 1)
    months: List[date] = []
    for _ in range(12):
        months.append(cursor)
        cursor = date(cursor.year - 1, 12, 1) if cursor.month == 1 else date(cursor.year, cursor.month - 1, 1)
    for month_start in reversed(months):
        key = month_start.strftime("%Y-%m")
        monthly_completions.append({
            "month": key,
            "label": month_start.strftime("%b %y"),
            "completed": monthly.get(key, 0),
        })

    # ---- Summary ----------------------------------------------------------
    enrolled_count = len(enrollments)
    completed_count = sum(1 for c in course_breakdown if c["status"] == "completed")
    in_progress_count = sum(1 for c in course_breakdown if c["status"] == "in_progress")
    not_started_count = sum(1 for c in course_breakdown if c["status"] == "not_started")

    total_lessons = sum(e.total_lessons or 0 for e in enrollments)
    completed_lessons = sum(e.completed_lessons or 0 for e in enrollments)
    # Enrollment counters can lag behind lesson_progress; trust whichever is higher.
    completed_lessons = max(completed_lessons, len(completed_lessons_all))

    active_day_set = sorted(d for d, m in minutes_by_day.items() if m > 0)
    streaks = _get_streaks(db, current_user.id, active_day_set)

    total_hours = round(sum(minutes_by_course.values()) / 60.0, 1)
    period_hours = round(sum(minutes_by_day.values()) / 60.0, 1)
    period_lessons = sum(lessons_by_day.values())

    summary = {
        "enrolled_courses": enrolled_count,
        "completed_courses": completed_count,
        "in_progress_courses": in_progress_count,
        "not_started_courses": not_started_count,
        "completion_rate": round((completed_count / enrolled_count) * 100) if enrolled_count else 0,
        "certificates_earned": len(certificates),
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "lesson_completion_rate": round((completed_lessons / total_lessons) * 100) if total_lessons else 0,
        "total_hours": total_hours,
        "period_hours": period_hours,
        "period_lessons": period_lessons,
        "avg_progress": round(sum(c["progress"] for c in course_breakdown) / len(course_breakdown)) if course_breakdown else 0,
        "active_days": len(active_day_set),
        "current_streak": streaks["current_streak"],
        "longest_streak": streaks["longest_streak"],
        "avg_session_hours": round(period_hours / len(active_day_set), 1) if active_day_set else 0.0,
        "quizzes_attempted": len(quiz_attempts),
        "quizzes_passed": quizzes_passed,
        "quiz_pass_rate": round((quizzes_passed / len(quiz_attempts)) * 100) if quiz_attempts else 0,
        "avg_quiz_score": avg_quiz_score,
        "assignments_submitted": len(submission_rows),
        "assignments_graded": graded_count,
        "avg_assignment_score": avg_assignment_score,
    }

    return {
        "period": period,
        "period_label": "All time" if window_days is None else f"Last {window_days} days",
        "generated_at": now.isoformat(),
        "student": {
            "name": current_user.display_name or current_user.user_login,
            "email": current_user.user_email,
        },
        "summary": summary,
        "activity_timeline": activity_timeline,
        "monthly_completions": monthly_completions,
        "course_breakdown": course_breakdown,
        "quiz_history": quiz_history,
        "assignment_history": assignment_history,
        "certificates": certificates,
        "insights": _build_insights(summary, course_breakdown),
    }


@router.get("/instructor")
async def get_instructor_dashboard(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get instructor dashboard statistics
    """
    # Verify user is instructor
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as instructor"
        )

    # Get courses created by instructor
    courses = db.query(Course).filter(
        Course.post_author == current_user.id
    ).all()

    total_courses = len(courses)

    # Get enrollment metrics for instructor's courses.
    #  - total_purchases: every enrollment row = one course a student purchased
    #    (a single student buying 3 courses counts as 3 purchases).
    #  - total_students: distinct students, so the same person across multiple
    #    courses is only counted once.
    course_ids = [course.id for course in courses]
    total_students = 0
    total_purchases = 0
    if course_ids:
        total_purchases = db.query(Enrollment).filter(
            Enrollment.course_id.in_(course_ids)
        ).count()
        total_students = db.query(Enrollment.user_id).filter(
            Enrollment.course_id.in_(course_ids)
        ).distinct().count()

    # Calculate total earnings through orders, per course line.
    # OrderItem.total is the amount actually paid for that course (net of any
    # coupon discount). Summing Payment.amount across an OrderItem join instead
    # fanned out: a 3-course order counted its full total three times.
    earnings_by_course: Dict[int, float] = {}
    total_earnings = 0.0
    if course_ids:
        earning_rows = db.query(
            OrderItem.course_id,
            func.sum(OrderItem.total),
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            OrderItem.course_id.in_(course_ids),
            Order.order_status == OrderStatus.COMPLETED,
            # Exclude the un-paid mock cart orders — see the admin revenue
            # calculation below for why these exist.
            func.coalesce(Order.payment_method, "") != "mock",
        ).group_by(OrderItem.course_id).all()
        earnings_by_course = {cid: float(amount or 0) for cid, amount in earning_rows}
        total_earnings = sum(earnings_by_course.values())

    # Average rating across all of this instructor's reviews.
    from app.models.instructor_review import InstructorReview
    avg_rating_row = db.query(func.avg(InstructorReview.rating)).filter(
        InstructorReview.instructor_id == current_user.id
    ).scalar()
    average_rating = round(float(avg_rating_row), 2) if avg_rating_row is not None else None

    # Per-course average rating — compute in one query to avoid N+1.
    per_course_rating = dict(
        db.query(
            InstructorReview.course_id,
            func.avg(InstructorReview.rating),
        ).filter(InstructorReview.course_id.in_(course_ids or [0]))
         .group_by(InstructorReview.course_id)
         .all()
    ) if course_ids else {}

    # Get course details
    course_list = []
    for course in courses[:10]:  # Limit to 10
        enrollments = db.query(Enrollment).filter(
            Enrollment.course_id == course.id
        ).count()

        course_rating = per_course_rating.get(course.id)
        course_rating = round(float(course_rating), 2) if course_rating is not None else None

        course_list.append({
            "id": course.id,
            "title": course.post_title,
            "students": enrollments,
            "total_enrollments": enrollments,
            "rating": course_rating,
            "average_rating": course_rating,
            "earnings": earnings_by_course.get(course.id, 0.0),
            "course_price": course.course_price or 0,
            "course_sale_price": course.course_sale_price or course.course_price or 0,
            "course_duration": course.course_duration or "4 weeks",
            "status": "published"
        })

    # Get recent enrollments in instructor's courses
    recent_activity = []
    if course_ids:
        recent_enrollments = db.query(Enrollment).filter(
            Enrollment.course_id.in_(course_ids),
            Enrollment.enrollment_date >= datetime.now() - timedelta(days=30)
        ).order_by(desc(Enrollment.enrollment_date)).limit(10).all()

        for enrollment in recent_enrollments:
            student = db.query(User).filter(User.id == enrollment.user_id).first()
            course = db.query(Course).filter(Course.id == enrollment.course_id).first()
            if student and course:
                recent_activity.append({
                    "type": "enrollment",
                    "action": "New enrollment",
                    "title": f"{student.display_name} enrolled",
                    "course": course.post_title,
                    "description": f"New student in {course.post_title}",
                    "timestamp": enrollment.enrollment_date.strftime("%Y-%m-%d %H:%M") if enrollment.enrollment_date else "Recently",
                    "time": get_relative_time(enrollment.enrollment_date) if enrollment.enrollment_date else "Recently"
                })

    return {
        "stats": {
            "total_courses": total_courses,
            "total_students": total_students,
            "total_purchases": total_purchases,
            "total_earnings": f"₹{total_earnings:,.0f}",
            "average_rating": average_rating
        },
        "courses": course_list,
        "recent_activity": recent_activity
    }


@router.get("/instructor/students")
async def get_instructor_students(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get students enrolled in instructor's courses with their details
    """
    # Verify user is instructor
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as instructor"
        )

    # Get courses created by instructor
    courses = db.query(Course).filter(
        Course.post_author == current_user.id
    ).all()
    course_ids = [course.id for course in courses]

    if not course_ids:
        return {"students": []}

    # Get enrollments for instructor's courses with student details
    enrollments = db.query(Enrollment).filter(
        Enrollment.course_id.in_(course_ids)
    ).all()

    # Get unique students and their details
    students_map = {}
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.user_id).first()
        if not student:
            continue

        course = db.query(Course).filter(Course.id == enrollment.course_id).first()
        if not course:
            continue

        # Get student profile
        from app.models.user import UserProfile
        profile = db.query(UserProfile).filter(UserProfile.user_id == student.id).first()

        if student.id not in students_map:
            students_map[student.id] = {
                "id": student.id,
                "name": student.display_name,
                "email": student.user_email,
                "avatar": profile.profile_photo if profile else None,
                "enrolledCourses": [],
                "totalCourses": 0,
                "completedCourses": 0,
                "joinDate": min((e.enrollment_date for e in enrollments if e.user_id == student.id), default=None).isoformat() if any(e.user_id == student.id for e in enrollments) else None,
                "lastActive": max((e.enrollment_date for e in enrollments if e.user_id == student.id), default=None).isoformat() if any(e.user_id == student.id for e in enrollments) else None,
                "averageRating": 0
            }

        # Add course to student's enrolled courses
        students_map[student.id]["enrolledCourses"].append({
            "courseId": course.id,
            "courseTitle": course.post_title,
            "progress": enrollment.course_progress_percentage or 0,
            "status": enrollment.enrollment_status or "active",
            "lastAccessed": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "timeSpent": 0
        })
        students_map[student.id]["totalCourses"] = len(students_map[student.id]["enrolledCourses"])
        if enrollment.enrollment_status == "completed":
            students_map[student.id]["completedCourses"] += 1

    return {"students": list(students_map.values())}


@router.get("/admin")
async def get_admin_dashboard(
    current_user: User = Depends(AuthService.get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get admin dashboard statistics
    """
    # Verify user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as admin"
        )

    # Get total counts
    total_courses = db.query(Course).count()
    total_students = db.query(User).filter(User.role == "student").count()
    total_enrollments = db.query(Enrollment).count()

    # Calculate total revenue (payments + internship vouchers)
    #
    # Cart checkout (POST /orders/) writes an Order + Payment already stamped
    # COMPLETED with payment_method="mock" — no money is ever collected on that
    # path. Counting those inflated reported revenue with rupees that were
    # never received, which is why the dashboard showed payments as credited
    # for orders that never went through a gateway.
    payment_revenue = float(
        db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.payment_status == PaymentStatus.COMPLETED,
            func.coalesce(Payment.payment_method, "") != "mock",
        ).scalar() or 0
    )

    # Add internship voucher revenue (all issued vouchers are paid)
    internship_revenue = db.query(func.coalesce(func.sum(InternshipVoucher.amount_paid), 0)).scalar() or 0
    total_revenue = payment_revenue + float(internship_revenue)

    # Get recent courses
    recent_courses = db.query(Course).order_by(
        Course.created_at.desc()
    ).limit(10).all()

    course_list = []
    for course in recent_courses:
        enrollments = db.query(Enrollment).filter(
            Enrollment.course_id == course.id
        ).count()

        # Revenue per course flows through OrderItem (Order has no course_id).
        # Sum OrderItem.total — the amount paid for *this* line — not
        # Payment.amount, which is the whole order's total and therefore
        # credited the full basket value to every course in a multi-course
        # order. Same fix already applied to the instructor path above.
        # Keyed on Order.order_status rather than joining Payment: /verify sets
        # both to COMPLETED together, and a second Payment row on the same
        # order (a retry) would otherwise fan the line total out again.
        course_revenue = db.query(func.coalesce(func.sum(OrderItem.total), 0)).select_from(
            OrderItem
        ).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            OrderItem.course_id == course.id,
            Order.order_status == OrderStatus.COMPLETED,
            func.coalesce(Order.payment_method, "") != "mock",
        ).scalar() or 0
        course_revenue = float(course_revenue)

        from app.models.instructor_review import InstructorReview as _Rev
        rating = db.query(func.avg(_Rev.rating)).filter(_Rev.course_id == course.id).scalar()
        course_list.append({
            "id": course.id,
            "title": course.post_title,
            "students": enrollments,
            "revenue": f"₹{course_revenue:,.0f}",
            "rating": round(float(rating), 2) if rating is not None else None,
            "status": "Published"
        })

    # Get recent enrollments
    recent_enrollments = db.query(Enrollment).order_by(
        Enrollment.enrollment_date.desc()
    ).limit(10).all()

    enrollment_list = []
    for enrollment in recent_enrollments:
        student = db.query(User).filter(User.id == enrollment.user_id).first()
        course = db.query(Course).filter(Course.id == enrollment.course_id).first()

        if student and course:
            enrollment_list.append({
                "student": student.display_name,
                "course": course.post_title,
                "date": enrollment.enrollment_date.strftime("%Y-%m-%d") if enrollment.enrollment_date else "Recent",
                "status": "active"
            })

    return {
        "stats": {
            "total_courses": total_courses,
            "total_students": total_students,
            "total_revenue": f"₹{total_revenue:,.0f}",
            "active_enrollments": total_enrollments
        },
        "recent_courses": course_list,
        "recent_enrollments": enrollment_list
    }
