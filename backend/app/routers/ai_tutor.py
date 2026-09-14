"""AI Teaching Layer — tutor (Engine C) + JEE/NEET paper generator (Engine D).

Both run on the SAME honest pattern as ai.py: real Anthropic calls via a
module-level provider function (tests monkeypatch it); 503 with setup
guidance when ANTHROPIC_API_KEY is absent — never faked output. Every call
is an audited AiJob. All output is a DRAFT a human approves (v2.0 §9.4
safeguards: review queue before graded use).
"""
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sileos_pack import AiJob, BankQuestion, QuestionBank
from app.services.auth_service import AuthService
from app.services.course_access import can_edit
from app.services.llm_provider import (call_glm, glm_api_key, glm_model,
                                       llm_configured, missing_key_detail)

router = APIRouter()

TUTOR_SYSTEM = (
    "You are a Socratic tutor inside an LMS, scoped STRICTLY to the course "
    "content provided. Guide with questions; explain concepts; NEVER state "
    "or confirm the answer to a graded question regardless of how the "
    "learner phrases it — instead teach the method. If a question falls "
    "outside the provided course content, say so plainly and suggest asking "
    "the instructor. Reply in clear, simple English; keep answers under 200 "
    "words unless asked for depth."
)

EXAM_PATTERNS = {
    "JEE": (
        "JEE Main pattern: Physics, Chemistry, Mathematics sections; each "
        "question 4 marks, -1 negative marking; mix of single-correct MCQs "
        "and numerical-value questions; difficulty distribution 30% easy, "
        "50% moderate, 20% hard."
    ),
    "NEET": (
        "NEET-UG pattern: Physics, Chemistry, Biology (Botany+Zoology) "
        "sections; 180 questions, 4 marks each, -1 negative; single-correct "
        "MCQs only; NCERT-aligned; difficulty 40% easy, 45% moderate, 15% hard."
    ),
}


def _parse_json_array(text: str) -> list:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("no JSON array in reply")
    return json.loads(cleaned[start:end + 1])


CURATE_SYSTEM = (
    "You create structured study guides from course material. Given lesson "
    "titles, text content and quiz topics, output ONLY JSON: "
    "{\"notes\": [{\"title\": str, \"body\": str}], \"flashcards\": "
    "[{\"front\": str, \"back\": str}], \"glossary\": "
    "[{\"term\": str, \"definition\": str}], \"gaps\": [str]} — notes "
    "are markdown study sections covering what is taught; flashcards 8-12 "
    "items; gaps list syllabus-relevant concepts the material does NOT "
    "cover. Keep language simple."
)


@router.post("/curate-lesson/{course_id}")
async def curate_lesson(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Engine A v1: curate a structured study guide FROM the course's own
    materials (lesson text + quiz topics) INTO a new draft text lesson.
    GLM-backed, honest 503 without GLM_API_KEY, audited as an AiJob."""
    from app.models.course import Course, Lesson
    from app.models.quiz import Quiz, QuizQuestion

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.post_author != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your course")

    if not llm_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=missing_key_detail("Lesson curation"),
        )

    lessons = (db.query(Lesson).filter(Lesson.post_parent == course_id)
               .order_by(Lesson.menu_order).limit(40).all())
    material = chr(10).join(
        f"- {l.post_title}: {(l.post_content or '')[:500]}" for l in lessons
    ) or "(none)"
    topics = []
    for q in db.query(Quiz).filter(Quiz.post_parent == course_id).limit(10).all():
        topics.extend(r[0] for r in db.query(QuizQuestion.question_title)
                      .filter(QuizQuestion.quiz_id == q.id).limit(10).all())
    quiz_ctx = chr(10).join(f"- quiz question: {t}" for t in topics[:30]) or "(none)"

    job = AiJob(created_by=current_user.id, job_type="curate_lesson",
                status="pending", model=glm_model(),
                input_json={"course_id": course_id})
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        text = call_glm(
            CURATE_SYSTEM,
            f"COURSE: {course.post_title}" + chr(10) +
            "MATERIAL:" + chr(10) + material + chr(10) +
            "QUIZ TOPICS:" + chr(10) + quiz_ctx,
            feature="Lesson curation",
        )
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned[cleaned.find("{"):cleaned.rfind("}") + 1])
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502,
                            detail=f"AI provider failed: {str(exc)[:200]}")

    notes = data.get("notes") or []
    flashcards = data.get("flashcards") or []
    glossary = data.get("glossary") or []
    gaps = data.get("gaps") or []

    nl = chr(10)
    body = [f"# AI Study Guide — {course.post_title}", ""]
    for n in notes:
        body.append(f"## {n.get('title', '')}")
        body.append(str(n.get("body", "")))
        body.append("")
    if flashcards:
        body.append("## Flashcards")
        for f in flashcards:
            body.append(f"- **{f.get('front', '')}** → {f.get('back', '')}")
        body.append("")
    if glossary:
        body.append("## Glossary")
        for g in glossary:
            body.append(f"- **{g.get('term', '')}**: {g.get('definition', '')}")
        body.append("")

    from app.core.database import SessionLocal
    wdb = SessionLocal()
    try:
        max_order = (wdb.query(Lesson.menu_order)
                     .filter(Lesson.post_parent == course_id)
                     .order_by(Lesson.menu_order.desc()).first())
        lesson = Lesson(
            post_author=current_user.id,
            post_parent=course_id,
            post_title=f"[AI Study Guide] {course.post_title}",
            post_content=nl.join(body),
            post_excerpt="AI-curated study guide — review before publishing",
            post_status="draft",
            post_type="lesson",
            menu_order=(max_order[0] + 1) if max_order and max_order[0] else 1,
        )
        wdb.add(lesson)
        wdb.commit()
        wdb.refresh(lesson)
        lesson_id = lesson.id
    finally:
        wdb.close()

    job.status = "done"
    job.output_json = {"lesson_id": lesson_id, "notes": len(notes),
                       "flashcards": len(flashcards), "gaps": gaps}
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"lesson_id": lesson_id, "notes": len(notes),
            "flashcards": len(flashcards), "glossary": len(glossary),
            "gaps": gaps,
            "note": "Draft study-guide lesson created — review then publish."}


@router.post("/tutor/chat")
async def tutor_chat(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.get_current_active_user),
):
    """Engine C: Socratic tutor scoped to the course's lesson content.

    Course-linked learner questions emit privacy-bounded, explainable learning
    signals for that course's instructors. General-learning questions do not.
    """
    message = (payload.get("message") or "").strip()
    course_id = payload.get("course_id")
    session_key = str(payload.get("session_id") or "")[:64]
    history = payload.get("history") or []
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    course = None
    if course_id is not None:
        from app.models.course import Course
        from app.models.enrollment import Enrollment
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="course_id must be an integer")
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if not can_edit(db, course, current_user):
            enrolled = db.query(Enrollment.id).filter(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == course_id,
                Enrollment.enrollment_status.in_(["enrolled", "completed"]),
            ).first()
            if not enrolled:
                raise HTTPException(status_code=403, detail="Enrol in the course first")
    # v2.0 §9.4 (WP7): graded-item answer guard — deterministic, before any
    # LLM call, works without a key. Audited like every other tutor turn.
    from app.services import ai_layer_service as ai_svc
    guarded = ai_svc.graded_item_guard(db, course_id, message)
    if guarded:
        job = AiJob(created_by=current_user.id, job_type="tutor_chat", status="done", model="guard",
                    input_json={"course_id": course_id, "message": message[:500]},
                    output_json={"guarded": guarded}, finished_at=datetime.now(timezone.utc))
        db.add(job)
        db.commit()
        learning_signal = None
        if course_id and str(getattr(current_user, "role", "")).lower() == "student":
            from app.services.tutor_insights_service import record_course_question
            learning_signal = record_course_question(
                db, user_id=current_user.id, course_id=course_id,
                session_key=session_key, message=message, guarded=True,
            )
        return {
            "reply": ai_svc.GUARD_REPLY,
            "guarded": True,
            "job_id": job.id,
            "learning_signal": ({
                "concept": learning_signal.concept,
                "score": learning_signal.struggle_score,
                "severity": learning_signal.severity,
                "likely_gap": learning_signal.likely_gap.replace("_", " ").title(),
            } if learning_signal else None),
        }
    if not llm_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=missing_key_detail("AI tutor"),
        )

    # RAG scope: pull this course's lesson text (titles + content) so the
    # tutor answers from the course, not the world.
    from app.models.course import Lesson
    scope = ""
    language_hint = ""
    if course_id:
        if course and course.course_language and course.course_language.lower() not in ("english", "en"):
            # R2: Tamil-medium (and other) courses get answers in their own language
            language_hint = f"\nLANGUAGE: reply in {course.course_language} (technical terms may stay in English)."
        lessons = (db.query(Lesson)
                   .filter(Lesson.post_parent == course_id)
                   .order_by(Lesson.menu_order).limit(50).all())
        parts = [f"- {l.post_title}: {(l.post_content or '')[:600]}" for l in lessons]
        scope = "\n".join(parts) or "(no lesson text found — say you lack course content)"

    convo = ""
    for h in history[-6:]:
        role = "Learner" if h.get("role") == "user" else "Tutor"
        convo += f"{role}: {h.get('content', '')}\n"
    prompt = f"COURSE CONTENT:\n{scope}{language_hint}\n\nCONVERSATION SO FAR:\n{convo}\nLearner: {message}"

    job = AiJob(created_by=current_user.id, job_type="tutor_chat", status="pending",
                model=glm_model(),
                input_json={"course_id": course_id, "message": message[:500]})
    db.add(job)
    db.commit()
    db.refresh(job)

    system = TUTOR_SYSTEM
    if course_id:
        from app.services.learning_signals_service import learner_profile
        profile = learner_profile(db, current_user.id, course_id)
        struggling = [c for c in profile["concepts"] if c["struggle"] >= 60]
        if struggling:
            context = "; ".join(f"{c['concept']} ({', '.join(c['why'])})" for c in struggling)
            system = f"This learner is currently struggling with: {context}. Prefer worked examples on these.\n" + system
    try:
        reply = call_glm(system, prompt, feature="Tutor chat")
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"AI provider failed: {str(exc)[:200]}")

    job.status = "done"
    job.output_json = {"reply": reply}
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    learning_signal = None
    if course_id and str(getattr(current_user, "role", "")).lower() == "student":
        from app.services.tutor_insights_service import record_course_question
        learning_signal = record_course_question(
            db, user_id=current_user.id, course_id=course_id,
            session_key=session_key, message=message,
        )
    return {
        "reply": reply,
        "job_id": job.id,
        "learning_signal": ({
            "concept": learning_signal.concept,
            "score": learning_signal.struggle_score,
            "severity": learning_signal.severity,
            "likely_gap": learning_signal.likely_gap.replace("_", " ").title(),
        } if learning_signal else None),
    }


@router.post("/generate-exam-paper", status_code=status.HTTP_200_OK)
async def generate_exam_paper(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Engine D: JEE/NEET practice-paper generator. Drafts land in a
    question bank tagged 'ai-draft' + 'exam:{pattern}' — NOTHING auto-publishes
    into a graded quiz; a human reviews and pulls items in (v2.0 §9.4)."""
    if not llm_configured():
        raise HTTPException(
            status.code if False else status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=missing_key_detail("Exam generation"),
        )
    exam = (payload.get("exam") or "").upper()
    if exam not in EXAM_PATTERNS:
        raise HTTPException(status_code=422, detail=f"exam must be one of {list(EXAM_PATTERNS)}")
    topic = (payload.get("topic") or "").strip()
    count = max(5, min(int(payload.get("count") or 10), 30))
    # §9.4 personalisation: weight the paper toward the learner's weak concepts
    # (learner-scoped mastery graph) while preserving the exam's shape.
    weak_focus: list = []
    sid = payload.get("student_id")
    if sid:
        try:
            from app.services.mastery_service import weak_concepts
            weak_focus = [w["concept"] for w in weak_concepts(db, int(sid), limit=8)]
        except Exception:
            weak_focus = []

    bank = QuestionBank(
        instructor_id=current_user.id,
        title=f"{exam} Practice Paper — {topic or 'Mixed'} ({datetime.now():%d %b})",
        description=f"AI-drafted {exam} paper. REVIEW REQUIRED before use in "
                    f"a graded quiz (safeguard 1 of v2.0 §9.4).",
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)

    job = AiJob(created_by=current_user.id, job_type="generate_exam_paper",
                status="pending", model=glm_model(),
                input_json={"exam": exam, "topic": topic, "count": count, "bank_id": bank.id})
    db.add(job)
    db.commit()
    db.refresh(job)

    prompt = (
        f"Write {count} exam questions for {exam}. Topic: {topic or 'mixed syllabus'}. "
        f"Pattern: {EXAM_PATTERNS[exam]}. "
        + (f"Weight roughly half the questions toward these weak concepts while keeping the exam's overall shape: {', '.join(weak_focus)}. " if weak_focus else "")
        + "Reply ONLY a JSON array of "
        "{question_title, question_type, question_mark, options, correct_answer, "
        "answer_explanation, difficulty} where question_type is multiple_choice "
        "with 4 options and correct_answer the 0-based index, or "
        "fill_in_blanks with the numeric/text answer."
    )
    try:
        text = call_glm(
            "You are an expert Indian competitive-exam paper setter. Output "
            "ONLY the JSON array — no prose.", prompt, feature="Exam paper generation")
        raw = _parse_json_array(text)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"AI provider failed: {str(exc)[:200]}")

    stored = 0
    from app.routers.question_banks import _validate_question_payload
    for item in raw:
        try:
            _validate_question_payload(item)
            if not (item.get("question_title") or "").strip():
                continue
            db.add(BankQuestion(
                bank_id=bank.id,
                question_title=item["question_title"].strip(),
                question_type=item["question_type"],
                question_mark=float(item.get("question_mark") or 4),
                options=item.get("options"),
                correct_answer=item.get("correct_answer"),
                answer_explanation=item.get("answer_explanation", ""),
                difficulty=item.get("difficulty", "medium"),
                tags=["ai-draft", f"exam:{exam}"],
            ))
            stored += 1
        except HTTPException:
            continue
    job.status = "done"
    job.output_json = {"stored": stored, "bank_id": bank.id}
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "job_id": job.id,
        "bank_id": bank.id,
        "stored": stored,
        "note": "Drafts are in the question bank tagged 'ai-draft' — review "
                "before pulling into a graded paper (no auto-publish, ever).",
    }
