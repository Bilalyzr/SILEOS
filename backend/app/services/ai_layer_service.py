"""AI layer completion (v2.0 §9 — WP7). Pure helpers used by
routers/ai_engines.py, ai_tutor.py (graded-item guard) and the transcript
ingest endpoints. Everything that needs the LLM goes through
llm_provider.call_glm and is an honest 503 without GLM_API_KEY; everything
deterministic (guard, item flags, escalation/report rows, transcript
storage) works without a key.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.llm_provider import call_glm, glm_model, llm_configured

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- Engine C: graded-item answer guard

_WS = re.compile(r"[^a-z0-9 ]+")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", _WS.sub(" ", (s or "").lower())).strip()


def graded_item_guard(db: Session, course_id: Optional[int], message: str) -> Optional[dict]:
    """If the learner's message IS (or contains) a graded quiz question of
    this course, refuse to answer it — deterministically, before any LLM
    call. Returns {"quiz_id", "question_id", "title"} when guarded."""
    if not course_id or len(_norm(message)) < 12:
        return None
    from app.models.quiz import Quiz, QuizQuestion
    m = _norm(message)
    rows = (db.query(QuizQuestion.question_id, QuizQuestion.quiz_id, QuizQuestion.question_title)
            .join(Quiz, Quiz.id == QuizQuestion.quiz_id).filter(Quiz.post_parent == course_id).limit(500).all())
    for qid, quiz_id, title in rows:
        t = _norm(title)
        if len(t) < 12:
            continue
        if t in m or m in t or _overlap(t, m) >= 0.8:
            return {"quiz_id": quiz_id, "question_id": qid, "title": title}
    return None


def _overlap(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


GUARD_REPLY = ("That looks like one of this course's graded questions, so I won't give or confirm the answer. "
               "Tell me which step you are stuck on and I'll walk you through the method, or ask your instructor.")


# ---------------------------------------------------------------- Engine C: mastery-calibrated check question

CHECK_SYSTEM = ("You write ONE short check-for-understanding question for a learner, calibrated to their current "
                "mastery, scoped to the course material given. Output ONLY JSON: "
                "{\"question\": str, \"kind\": \"open\"|\"mcq\", \"options\": [str] (mcq only), \"answer\": str, "
                "\"why\": str}. Never copy a graded quiz question.")


def calibrate(estimate: Optional[float]) -> str:
    """estimate is LearnerMastery.estimate — a 0..100 percentage."""
    if estimate is None:
        return "medium"
    return "easy" if estimate < 40 else "medium" if estimate < 75 else "hard"


def course_material(db: Session, course_id: int, limit: int = 40, chars: int = 500) -> str:
    from app.models.course import Lesson
    lessons = (db.query(Lesson).filter(Lesson.post_parent == course_id, Lesson.post_status == "publish")
               .order_by(Lesson.menu_order).limit(limit).all())
    return "\n".join(f"- {l.post_title}: {(l.post_content or '')[:chars]}" for l in lessons) or "(no lesson text)"


def learner_concept_state(db: Session, user_id: int, concept: Optional[str]) -> dict:
    from app.models.mastery import LearnerMastery
    from app.services.mastery_service import weak_concepts
    est = None
    if concept:
        row = db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id, LearnerMastery.concept == concept).first()
        est = row.estimate if row else None
    weak = [w["concept"] for w in weak_concepts(db, user_id, limit=6)]
    return {"concept": concept or (weak[0] if weak else None), "estimate": est, "weak": weak, "level": calibrate(est)}


def parse_json_object(text: str) -> dict:
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[s.find("{"):]
    start, end = s.find("{"), s.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(s[start:end + 1])


def parse_json_array(text: str) -> list:
    s = text.strip()
    start, end = s.find("["), s.rfind("]")
    if start < 0 or end < 0:
        raise ValueError("no JSON array in model output")
    return json.loads(s[start:end + 1])


# ---------------------------------------------------------------- Engine B: depth-adaptive lesson

MODES = ("recover", "consolidate", "extend")
ADAPT_SYSTEM = ("You are a course author writing a SHORT depth-adaptive mini-lesson for ONE learner, strictly from the course "
                "material given. Modes: recover = re-teach the prerequisite gently with a worked example; consolidate = "
                "practice + a second example at the same depth; extend = one step beyond with a challenge. Output ONLY JSON: "
                "{\"title\": str, \"mode\": str, \"concept\": str, \"sections\": [{\"heading\": str, \"body\": str}], "
                "\"check\": {\"question\": str, \"answer\": str}} — plain English, no markdown fences.")


def choose_mode(estimate: Optional[float]) -> str:
    """estimate is a 0..100 percentage (LearnerMastery.estimate)."""
    if estimate is None:
        return "consolidate"
    return "recover" if estimate < 40 else "consolidate" if estimate < 75 else "extend"


# ---------------------------------------------------------------- Engine D: item statistics + auto-flag

def item_stats(db: Session, question_id: int) -> dict:
    """facility (p-value) + discrimination (top-27% − bottom-27%) over
    live quiz answers — same math as question_banks.item_analysis."""
    from app.models.quiz import QuizAttemptAnswer
    answers = db.query(QuizAttemptAnswer).filter(QuizAttemptAnswer.question_id == question_id).all()
    attempts = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    facility = round(correct / attempts, 3) if attempts else None
    discrimination = None
    if attempts >= 6:
        by_attempt: Dict[int, float] = {}
        for a in answers:
            by_attempt[a.quiz_attempt_id] = by_attempt.get(a.quiz_attempt_id, 0.0) + float(a.achieved_mark or 0)
        ordered = sorted(by_attempt.items(), key=lambda kv: kv[1])
        k = max(1, int(len(ordered) * 0.27))
        weak_ids = {aid for aid, _ in ordered[:k]}
        strong_ids = {aid for aid, _ in ordered[-k:]}

        def _rate(ids: set) -> float:
            g = [a for a in answers if a.quiz_attempt_id in ids]
            return (sum(1 for a in g if a.is_correct) / len(g)) if g else 0.0
        discrimination = round(_rate(strong_ids) - _rate(weak_ids), 3)
    return {"attempts": attempts, "facility": facility, "discrimination": discrimination}


def flag_reasons(stats: dict) -> List[str]:
    """§9.4 safeguard 2 — explainable, derived. Thresholds are the classical
    item-analysis conventions (facility outside 0.2–0.95, discrimination <0.1)."""
    reasons: List[str] = []
    n, f, d = stats.get("attempts") or 0, stats.get("facility"), stats.get("discrimination")
    if n >= 10 and f is not None:
        if f < 0.2:
            reasons.append(f"very hard: only {int(f * 100)}% answer correctly over {n} attempts — check for an error or ambiguity")
        elif f > 0.95:
            reasons.append(f"trivial: {int(f * 100)}% answer correctly over {n} attempts")
    if n >= 6 and d is not None and d < 0.1:
        reasons.append(f"does not discriminate: strong and weak learners score alike (D={d})")
    if n >= 6 and d is not None and d < 0:
        reasons.append("negative discrimination: weak learners do BETTER — the key may be wrong")
    return reasons


def flagged_items(db: Session, instructor_id: int, admin: bool = False) -> List[dict]:
    from app.models.course import Course
    from app.models.quiz import Quiz, QuizQuestion
    q = db.query(QuizQuestion.question_id, QuizQuestion.quiz_id, QuizQuestion.question_title, Quiz.post_parent, Quiz.post_title,
                 QuizQuestion.is_retired)\
          .join(Quiz, Quiz.id == QuizQuestion.quiz_id).join(Course, Course.id == Quiz.post_parent)
    if not admin:
        q = q.filter(Course.post_author == instructor_id)
    out = []
    for qid, quiz_id, title, course_id, quiz_title, retired in q.limit(2000).all():
        st = item_stats(db, qid)
        reasons = flag_reasons(st)
        if reasons:
            out.append({"question_id": qid, "quiz_id": quiz_id, "quiz_title": quiz_title, "course_id": course_id,
                        "question_title": title, "is_retired": bool(retired), **st, "reasons": reasons})
    out.sort(key=lambda r: (-(len(r["reasons"])), -(r["attempts"])))
    return out


def ai_draft_queue(db: Session, instructor_id: int) -> List[dict]:
    from app.models.sileos_pack import BankQuestion, QuestionBank
    rows = (db.query(BankQuestion, QuestionBank).join(QuestionBank, QuestionBank.id == BankQuestion.bank_id)
            .filter(QuestionBank.instructor_id == instructor_id).order_by(BankQuestion.id.desc()).limit(500).all())
    return [{"question_id": bq.id, "bank_id": bank.id, "bank_title": bank.title, "question_title": bq.question_title,
             "question_type": bq.question_type, "options": bq.options, "correct_answer": bq.correct_answer,
             "difficulty": bq.difficulty, "tags": bq.tags or []}
            for bq, bank in rows if "ai-draft" in (bq.tags or [])]


# ---------------------------------------------------------------- Engine A: transcript ingest

SEGMENT_SYSTEM = ("You segment a live-class transcript into teaching topics. Output ONLY a JSON array of "
                  "{\"topic\": str (3-8 words), \"summary\": str (1-2 sentences), \"concepts\": [str] (lowercase, 1-3 words each), "
                  "\"start_hint\": str (first few words of the segment)}. 3-10 items.")


def process_transcript(db: Session, report, transcript: str, actor_id: Optional[int] = None) -> dict:
    """Store the transcript on the permanent ClassReport, then — only when the
    LLM is configured — segment it into topics/concepts (`ai_topics`) and
    propagate the concepts to the mastery graph as teaching links. Returns
    the resulting processing state. Never raises for a missing key."""
    from app.models.sileos_pack import AiJob
    report.transcript = transcript
    report.processing_status = "transcribed"
    db.commit()
    if not llm_configured():
        return {"processing_status": "transcribed", "ai_topics": None, "note": "GLM_API_KEY not set — transcript stored, topics pending"}
    job = AiJob(created_by=actor_id or report.instructor_id, job_type="segment_transcript", status="pending",
                model=glm_model(), input_json={"class_id": report.class_id, "chars": len(transcript)})
    db.add(job)
    db.commit()
    try:
        text = call_glm(SEGMENT_SYSTEM, transcript[:24000])
        topics = [t for t in parse_json_array(text) if isinstance(t, dict) and t.get("topic")]
    except Exception as exc:
        job.status, job.error, job.finished_at = "failed", str(exc)[:2000], datetime.now(timezone.utc)
        db.commit()
        return {"processing_status": "transcribed", "ai_topics": None, "note": f"segmentation failed: {str(exc)[:120]}"}
    report.ai_topics = topics
    report.processing_status = "processed"
    job.status, job.output_json, job.finished_at = "done", {"topics": len(topics)}, datetime.now(timezone.utc)
    db.commit()
    # concept propagation (best-effort): the class TAUGHT these concepts
    try:
        from app.services.mastery_service import set_links
        concepts = sorted({c.strip().lower() for t in topics for c in (t.get("concepts") or []) if isinstance(c, str) and c.strip()})
        if concepts:
            set_links(db, "live_class", str(report.class_id), concepts[:20], course_id=report.course_id)
            db.commit()
    except Exception:
        logger.debug("transcript concept propagation skipped", exc_info=True)
    return {"processing_status": "processed", "ai_topics": topics, "note": None}


# ---------------------------------------------------------------- misc

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ser(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def escalation_dict(e) -> Dict[str, Any]:
    return {"id": e.id, "course_id": e.course_id, "student_id": e.student_id, "instructor_id": e.instructor_id,
            "question": e.question, "context": e.context or {}, "status": e.status, "instructor_reply": e.instructor_reply,
            "created_at": ser(e.created_at), "answered_at": ser(e.answered_at)}


def report_dict(r) -> Dict[str, Any]:
    return {"id": r.id, "reporter_id": r.reporter_id, "course_id": r.course_id, "instructor_id": r.instructor_id,
            "kind": r.kind, "ref_id": r.ref_id, "message": r.message, "status": r.status, "resolution": r.resolution,
            "created_at": ser(r.created_at), "resolved_at": ser(r.resolved_at)}
