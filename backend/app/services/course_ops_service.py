"""Instructor growth tools (roadmap R6): course cloning + templates, quiz
import from CSV, co-instructors.
"""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

COURSE_COPY_FIELDS = (
    "post_content", "post_excerpt", "course_price_type", "course_price", "course_sale_price", "course_duration",
    "course_level", "course_category", "course_language", "course_benefits", "course_requirements",
    "course_target_audience", "course_material_includes", "course_tags", "num_offline_workshops", "num_hours",
    "institution", "course_thumbnail", "course_cover_image", "course_intro_video", "course_retakes_allowed",
    "course_auto_start_next_lesson", "course_content_drip_type", "certificate_template", "course_type", "certificate_design",
)
LESSON_COPY_FIELDS = (
    "post_content", "post_title", "post_excerpt", "post_status", "menu_order", "post_type", "lesson_video_source",
    "lesson_video_url", "lesson_youtube_url", "lesson_video_duration", "lesson_video_poster", "lesson_content_type",
    "h5p_content_id", "game_id", "geogebra_applet_id", "three_d_model_id", "virtual_lab_sim", "lesson_attachments",
    "lesson_preview", "lesson_attachment_url",
)
QUIZ_COPY_FIELDS = (
    "post_content", "post_title", "post_excerpt", "post_status", "menu_order", "post_type", "quiz_time_limit",
    "quiz_feedback_mode", "quiz_max_questions_for_take", "quiz_max_attempts_allowed", "quiz_passing_grade",
    "interactive_modules", "quiz_question_layout_view", "quiz_questions_order", "quiz_hide_quiz_details",
    "quiz_hide_quiz_time_display", "quiz_auto_start",
)
QUESTION_COPY_FIELDS = ("question_title", "question_description", "answer_explanation", "question_type", "question_mark",
                        "question_settings", "question_order")
ANSWER_COPY_FIELDS = ("belongs_question_type", "answer_title", "is_correct", "image_id", "answer_two_gap_match",
                      "answer_view_format", "answer_settings", "answer_order")
ASSIGNMENT_COPY_FIELDS = ("title", "description", "instructions", "due_date", "total_points", "allowed_file_types",
                          "max_file_size", "max_files", "submission_type", "attachments", "late_policy", "late_penalty_pct")


def _copy(src, dst, fields):
    for f in fields:
        if hasattr(src, f) and hasattr(dst, f):
            setattr(dst, f, getattr(src, f))


def clone_course(db: Session, source, new_owner_id: int, title: Optional[str] = None,
                 from_template: bool = False):
    """Deep copy: course → lessons, quizzes (+questions/answers), assignments,
    sections_meta remapped to the new ids, studio settings. The copy is a
    DRAFT owned by new_owner_id with no enrolments, progress or reviews."""
    from app.models.assignment import Assignment
    from app.models.course import Course, Lesson
    from app.models.course_settings import CourseStudioSettings
    from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer

    new = Course(post_author=new_owner_id, post_title=(title or f"{source.post_title} (copy)")[:255], post_status="draft",
                 post_name="", post_type=getattr(source, "post_type", "courses") or "courses")
    _copy(source, new, COURSE_COPY_FIELDS)
    if from_template:
        new.is_template = False
    db.add(new)
    db.flush()

    id_map: Dict[str, str] = {}
    for lesson in db.query(Lesson).filter(Lesson.post_parent == source.id).order_by(Lesson.menu_order).all():
        nl = Lesson(post_author=new_owner_id, post_parent=new.id, post_name="")
        _copy(lesson, nl, LESSON_COPY_FIELDS)
        db.add(nl)
        db.flush()
        id_map[f"lesson-{lesson.id}"] = f"lesson-{nl.id}"
    for quiz in db.query(Quiz).filter(Quiz.post_parent == source.id).order_by(Quiz.menu_order).all():
        nq = Quiz(post_author=new_owner_id, post_parent=new.id, post_name="")
        _copy(quiz, nq, QUIZ_COPY_FIELDS)
        db.add(nq)
        db.flush()
        id_map[f"quiz-{quiz.id}"] = f"quiz-{nq.id}"
        for q in db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.question_order).all():
            nqq = QuizQuestion(quiz_id=nq.id)
            _copy(q, nqq, QUESTION_COPY_FIELDS)
            db.add(nqq)
            db.flush()
            for a in db.query(QuizQuestionAnswer).filter(QuizQuestionAnswer.belongs_question_id == q.question_id).all():
                na = QuizQuestionAnswer(belongs_question_id=nqq.question_id)
                _copy(a, na, ANSWER_COPY_FIELDS)
                db.add(na)
    for asg in db.query(Assignment).filter(Assignment.course_id == source.id).all():
        na = Assignment(course_id=new.id, created_by=new_owner_id)
        _copy(asg, na, ASSIGNMENT_COPY_FIELDS)
        db.add(na)
        db.flush()
        id_map[f"assignment-{asg.id}"] = f"assignment-{na.id}"

    # sections_meta: remap lectureIds so the section layout survives the copy
    meta_raw = getattr(source, "course_sections_meta", None)
    if meta_raw:
        try:
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            for sec in meta or []:
                ids = []
                for lid in sec.get("lectureIds") or []:
                    key = lid if re.match(r"^(lesson|quiz|assignment)-", str(lid)) else f"lesson-{lid}"
                    if key in id_map:
                        ids.append(id_map[key])
                sec["lectureIds"] = ids
            new.course_sections_meta = json.dumps(meta)
        except Exception:
            new.course_sections_meta = None

    st = db.query(CourseStudioSettings).filter(CourseStudioSettings.course_id == source.id).first()
    if st:
        db.add(CourseStudioSettings(course_id=new.id, parent_view=dict(st.parent_view or {}), rewards=dict(st.rewards or {}),
                                    face_dismissed=False, updated_by=new_owner_id))
    db.commit()
    db.refresh(new)
    return new, len([k for k in id_map if k.startswith("lesson-")]), len([k for k in id_map if k.startswith("quiz-")]), \
        len([k for k in id_map if k.startswith("assignment-")])


# ---------------------------------------------------------------- CSV quiz import

CSV_TYPES = {"multiple_choice", "true_false", "fill_in_blanks", "short_answer", "open_ended"}
CSV_HELP = ("Columns: question, type (multiple_choice | true_false | fill_in_blanks | short_answer), option_a, option_b, "
            "option_c, option_d, correct (A-D for multiple choice, TRUE/FALSE, or the expected text), marks, explanation")


def parse_quiz_csv(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Returns (questions, errors). All-or-nothing: any error → nothing imported."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        return [], ["empty file"]
    cols = {c.strip().lower(): c for c in reader.fieldnames}
    if "question" not in cols:
        return [], ["missing 'question' column — " + CSV_HELP]
    get = lambda row, key: (row.get(cols[key]) or "").strip() if key in cols else ""  # noqa: E731
    out, errors = [], []
    for n, row in enumerate(reader, start=2):
        title = get(row, "question")
        if not title:
            continue
        qtype = (get(row, "type") or "multiple_choice").lower().replace("-", "_").replace(" ", "_")
        if qtype in ("mcq", "choice"):
            qtype = "multiple_choice"
        if qtype in ("tf", "boolean"):
            qtype = "true_false"
        if qtype not in CSV_TYPES:
            errors.append(f"row {n}: unknown type '{qtype}'")
            continue
        marks_raw = get(row, "marks") or "1"
        try:
            marks = float(marks_raw)
        except ValueError:
            errors.append(f"row {n}: marks must be a number")
            continue
        correct = get(row, "correct")
        answers: List[Dict[str, Any]] = []
        if qtype == "multiple_choice":
            opts = [(letter, get(row, f"option_{letter}")) for letter in ("a", "b", "c", "d")]
            opts = [(l, t) for l, t in opts if t]
            if len(opts) < 2:
                errors.append(f"row {n}: multiple choice needs at least option_a and option_b")
                continue
            letters = {l.upper() for l in correct.replace(" ", "").split(",") if l}
            if not letters or not letters <= {l.upper() for l, _ in opts}:
                errors.append(f"row {n}: correct must name one of the filled options (A-D)")
                continue
            answers = [{"answer_title": t, "is_correct": l.upper() in letters} for l, t in opts]
        elif qtype == "true_false":
            c = correct.upper()
            if c not in ("TRUE", "FALSE", "T", "F"):
                errors.append(f"row {n}: correct must be TRUE or FALSE")
                continue
            truth = c.startswith("T")
            answers = [{"answer_title": "True", "is_correct": truth}, {"answer_title": "False", "is_correct": not truth}]
        elif qtype == "fill_in_blanks":
            if not correct:
                errors.append(f"row {n}: correct text is required for fill in the blanks")
                continue
            answers = [{"answer_title": correct, "is_correct": True}]
        else:
            answers = [{"answer_title": correct, "is_correct": True}] if correct else []
        out.append({"question_title": title, "question_type": qtype, "question_mark": marks,
                    "answer_explanation": get(row, "explanation"), "answers": answers})
    if not out and not errors:
        errors.append("no question rows found")
    return out, errors


def create_quiz_from_rows(db: Session, course_id: int, author_id: int, title: str, rows: List[Dict[str, Any]],
                          passing_grade: int = 50):
    from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
    quiz = Quiz(post_author=author_id, post_parent=course_id, post_title=title[:200], post_status="publish", post_name="",
                quiz_passing_grade=passing_grade)
    db.add(quiz)
    db.flush()
    for i, r in enumerate(rows, start=1):
        q = QuizQuestion(quiz_id=quiz.id, question_title=r["question_title"], question_type=r["question_type"],
                         question_mark=r["question_mark"], answer_explanation=r.get("answer_explanation") or "", question_order=i)
        db.add(q)
        db.flush()
        for j, a in enumerate(r["answers"], start=1):
            db.add(QuizQuestionAnswer(belongs_question_id=q.question_id, belongs_question_type=r["question_type"],
                                      answer_title=a["answer_title"], is_correct=bool(a["is_correct"]), answer_order=j))
    db.commit()
    db.refresh(quiz)
    return quiz


# ---------------------------------------------------------------- collaborators

def list_collaborators(db: Session, course_id: int) -> List[Dict[str, Any]]:
    from app.models.course_ops import CourseCollaborator
    from app.models.user import User
    rows = (db.query(CourseCollaborator, User).join(User, User.id == CourseCollaborator.user_id)
            .filter(CourseCollaborator.course_id == course_id).order_by(CourseCollaborator.id.asc()).all())
    return [{"id": c.id, "user_id": u.id, "name": u.display_name, "email": u.user_email, "role": c.role,
             "created_at": c.created_at.isoformat() if c.created_at else None} for c, u in rows]


def add_collaborator(db: Session, course, email: str, added_by: int):
    from app.models.course_ops import CourseCollaborator
    from app.models.user import User
    user = db.query(User).filter(User.user_email == email.strip().lower()).first()
    if not user:
        raise LookupError("No account with that email")
    if user.role not in ("instructor", "admin", "superadmin"):
        raise ValueError("Only instructor accounts can be co-instructors")
    if user.id == course.post_author:
        raise ValueError("That is already the course owner")
    existing = db.query(CourseCollaborator).filter(CourseCollaborator.course_id == course.id, CourseCollaborator.user_id == user.id).first()
    if existing:
        return existing, False
    row = CourseCollaborator(course_id=course.id, user_id=user.id, added_by=added_by)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, True
