"""Explainable diagnostics and instructor rollups for course-linked Sasha use.

The score is deliberately deterministic: instructors can see the evidence
behind it and the same learner input always follows the same rules.  The LLM
does not label risk and its reply is never included in instructor analytics.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.course import Lesson
from app.models.mastery import ConceptLink, LearnerMastery
from app.models.tutor_learning_signal import TutorLearningSignal
from app.models.user import User


_STOP_WORDS = {
    "about", "after", "again", "course", "from", "have", "into", "lesson",
    "that", "their", "this", "what", "when", "where", "which", "with",
}
_CONFUSION = (
    "don't understand", "do not understand", "confused", "stuck", "lost",
    "cannot understand", "can't understand", "makes no sense", "i need help",
)
_REPEAT = ("again", "another way", "simpler", "still don't", "still do not")
_APPLICATION = ("example", "apply", "solve", "problem", "step by step", "how do i")
_TERMINOLOGY = ("what is", "meaning", "define", "definition", "difference between")
_CONFIDENCE = ("not sure", "i guess", "afraid", "worried", "i think maybe")


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in _STOP_WORDS
    }


def _course_concepts(db: Session, course_id: int) -> list[str]:
    linked = [row[0] for row in (
        db.query(ConceptLink.concept)
        .filter(ConceptLink.course_id == course_id)
        .distinct()
        .order_by(ConceptLink.concept)
        .all()
    ) if row[0]]
    if linked:
        return linked[:300]
    # Older courses may not have a mastery graph yet. Lesson titles are a
    # bounded, course-owned fallback instead of inventing a global taxonomy.
    return [row[0][:80] for row in (
        db.query(Lesson.post_title)
        .filter(Lesson.post_parent == course_id)
        .order_by(Lesson.menu_order)
        .limit(100)
        .all()
    ) if row[0]]


def detect_concept(message: str, concepts: Iterable[str]) -> str:
    lower = message.lower()
    message_tokens = _tokens(message)
    best: tuple[float, str] | None = None
    for concept in concepts:
        clean = " ".join(str(concept).split())[:80]
        if not clean:
            continue
        concept_tokens = _tokens(clean)
        if clean.lower() in lower:
            score = 2.0 + len(concept_tokens) / 100
        elif concept_tokens:
            overlap = len(message_tokens & concept_tokens) / len(concept_tokens)
            score = overlap if overlap >= 0.5 else 0.0
        else:
            score = 0.0
        if score and (best is None or score > best[0]):
            best = (score, clean)
    return best[1] if best else "General course support"


def _likely_gap(message: str, repeat_count: int, mastery: float | None) -> str:
    lower = message.lower()
    if mastery is not None and mastery < 40:
        return "foundational_gap"
    if repeat_count >= 2 or any(phrase in lower for phrase in _REPEAT):
        return "repeated_confusion"
    if any(phrase in lower for phrase in _CONFIDENCE):
        return "confidence_gap"
    if any(phrase in lower for phrase in _TERMINOLOGY):
        return "terminology_gap"
    if any(phrase in lower for phrase in _APPLICATION):
        return "application_gap"
    return "concept_clarity"


def diagnose(
    message: str,
    *,
    concept: str,
    repeat_count: int = 0,
    mastery: float | None = None,
    guarded: bool = False,
) -> dict[str, Any]:
    """Return an explainable 0-100 concern score and supporting evidence."""
    lower = message.lower()
    score = 22.0
    reasons: list[str] = []
    if any(phrase in lower for phrase in _CONFUSION):
        score += 30
        reasons.append("The learner explicitly described confusion or being stuck.")
    if any(phrase in lower for phrase in _REPEAT):
        score += 18
        reasons.append("The learner asked for the idea again or in a simpler form.")
    if any(phrase in lower for phrase in _APPLICATION):
        score += 10
        reasons.append("The learner needs help applying the concept, not only recalling it.")
    if repeat_count:
        score += min(repeat_count * 8, 24)
        reasons.append(f"This concept appeared in {repeat_count} earlier Sasha question{'s' if repeat_count != 1 else ''}.")
    if mastery is not None and mastery < 40:
        score += 25
        reasons.append(f"Verified mastery evidence is currently {round(mastery)}%.")
    elif mastery is not None and mastery < 60:
        score += 12
        reasons.append(f"Verified mastery evidence is still developing at {round(mastery)}%.")
    if guarded:
        score = max(score, 50)
        reasons.append("Sasha redirected a request involving a graded answer to the learning method.")
    if not reasons:
        reasons.append("A course-linked explanation request was recorded for follow-up evidence.")

    score = round(min(score, 100.0), 1)
    severity = "high" if score >= 75 else "watch" if score >= 50 else "developing"
    return {
        "concept": concept,
        "score": score,
        "severity": severity,
        "likely_gap": _likely_gap(message, repeat_count, mastery),
        "reasons": reasons[:4],
    }


def record_course_question(
    db: Session,
    *,
    user_id: int,
    course_id: int,
    session_key: str,
    message: str,
    guarded: bool = False,
) -> TutorLearningSignal:
    concept = detect_concept(message, _course_concepts(db, course_id))
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    repeat_count = db.query(func.count(TutorLearningSignal.id)).filter(
        TutorLearningSignal.user_id == user_id,
        TutorLearningSignal.course_id == course_id,
        TutorLearningSignal.concept == concept,
        TutorLearningSignal.created_at >= cutoff,
    ).scalar() or 0
    mastery_row = None
    if concept != "General course support":
        mastery_row = db.query(LearnerMastery.estimate).filter(
            LearnerMastery.user_id == user_id,
            LearnerMastery.concept == concept.lower(),
        ).first()
    mastery = float(mastery_row[0]) if mastery_row else None
    result = diagnose(
        message,
        concept=concept,
        repeat_count=int(repeat_count),
        mastery=mastery,
        guarded=guarded,
    )
    row = TutorLearningSignal(
        user_id=user_id,
        course_id=course_id,
        session_key=(session_key or "")[:64],
        prompt_excerpt=" ".join(message.split())[:500],
        concept=result["concept"],
        struggle_score=result["score"],
        severity=result["severity"],
        likely_gap=result["likely_gap"],
        reasons=result["reasons"],
        repeat_count=int(repeat_count),
        is_guarded=guarded,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _label_gap(value: str) -> str:
    return value.replace("_", " ").title()


def course_insights(db: Session, course_id: int, days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    base = [
        TutorLearningSignal.course_id == course_id,
        TutorLearningSignal.created_at >= cutoff,
    ]
    total, active, avg_score, high = db.query(
        func.count(TutorLearningSignal.id),
        func.count(func.distinct(TutorLearningSignal.user_id)),
        func.avg(TutorLearningSignal.struggle_score),
        func.sum(case((TutorLearningSignal.struggle_score >= 75, 1), else_=0)),
    ).filter(*base).one()

    student_groups = db.query(
        TutorLearningSignal.user_id,
        User.display_name,
        User.user_email,
        func.count(TutorLearningSignal.id).label("questions"),
        func.avg(TutorLearningSignal.struggle_score).label("average"),
        func.max(TutorLearningSignal.struggle_score).label("maximum"),
        func.max(TutorLearningSignal.created_at).label("last_seen"),
    ).join(User, User.id == TutorLearningSignal.user_id).filter(*base).group_by(
        TutorLearningSignal.user_id, User.display_name, User.user_email,
    ).order_by(func.max(TutorLearningSignal.struggle_score).desc()).limit(100).all()

    top_ids = [row.user_id for row in student_groups]
    concepts_by_student: dict[int, list[str]] = defaultdict(list)
    gaps_by_student: dict[int, str] = {}
    excerpts_by_student: dict[int, list[str]] = defaultdict(list)
    if top_ids:
        concept_groups = db.query(
            TutorLearningSignal.user_id,
            TutorLearningSignal.concept,
            func.count(TutorLearningSignal.id).label("n"),
            func.avg(TutorLearningSignal.struggle_score).label("score"),
        ).filter(*base, TutorLearningSignal.user_id.in_(top_ids)).group_by(
            TutorLearningSignal.user_id, TutorLearningSignal.concept,
        ).order_by(func.avg(TutorLearningSignal.struggle_score).desc()).all()
        for row in concept_groups:
            if len(concepts_by_student[row.user_id]) < 3:
                concepts_by_student[row.user_id].append(row.concept)

        gap_groups = db.query(
            TutorLearningSignal.user_id,
            TutorLearningSignal.likely_gap,
            func.count(TutorLearningSignal.id).label("n"),
        ).filter(*base, TutorLearningSignal.user_id.in_(top_ids)).group_by(
            TutorLearningSignal.user_id, TutorLearningSignal.likely_gap,
        ).order_by(func.count(TutorLearningSignal.id).desc()).all()
        for row in gap_groups:
            gaps_by_student.setdefault(row.user_id, _label_gap(row.likely_gap))

        evidence_rows = db.query(TutorLearningSignal).filter(
            *base, TutorLearningSignal.user_id.in_(top_ids)
        ).order_by(TutorLearningSignal.created_at.desc()).limit(300).all()
        for row in evidence_rows:
            if len(excerpts_by_student[row.user_id]) < 2:
                excerpts_by_student[row.user_id].append(row.prompt_excerpt)

    students = []
    for row in student_groups:
        score = round(float(row.maximum or 0) * 0.65 + float(row.average or 0) * 0.35, 1)
        students.append({
            "user_id": row.user_id,
            "name": row.display_name,
            "email": row.user_email,
            "risk_score": score,
            "severity": "high" if score >= 75 else "watch" if score >= 50 else "developing",
            "questions": int(row.questions),
            "top_concepts": concepts_by_student[row.user_id],
            "likely_gap": gaps_by_student.get(row.user_id, "Concept Clarity"),
            "evidence": excerpts_by_student[row.user_id],
            "last_seen": _iso(row.last_seen),
        })

    concept_groups = db.query(
        TutorLearningSignal.concept,
        func.count(TutorLearningSignal.id).label("questions"),
        func.count(func.distinct(TutorLearningSignal.user_id)).label("learners"),
        func.avg(TutorLearningSignal.struggle_score).label("score"),
    ).filter(*base).group_by(TutorLearningSignal.concept).order_by(
        func.avg(TutorLearningSignal.struggle_score).desc(),
        func.count(TutorLearningSignal.id).desc(),
    ).limit(12).all()

    concept_gaps = db.query(
        TutorLearningSignal.concept,
        TutorLearningSignal.likely_gap,
        func.count(TutorLearningSignal.id).label("n"),
    ).filter(*base).group_by(
        TutorLearningSignal.concept, TutorLearningSignal.likely_gap,
    ).order_by(func.count(TutorLearningSignal.id).desc()).all()
    top_gap_by_concept: dict[str, str] = {}
    for row in concept_gaps:
        top_gap_by_concept.setdefault(row.concept, _label_gap(row.likely_gap))

    concepts = [{
        "concept": row.concept,
        "score": round(float(row.score or 0), 1),
        "questions": int(row.questions),
        "learners": int(row.learners),
        "likely_gap": top_gap_by_concept.get(row.concept, "Concept Clarity"),
    } for row in concept_groups]

    recent_rows = db.query(TutorLearningSignal, User.display_name).join(
        User, User.id == TutorLearningSignal.user_id,
    ).filter(*base).order_by(TutorLearningSignal.created_at.desc()).limit(12).all()
    recent = [{
        "id": signal.id,
        "user_id": signal.user_id,
        "student_name": display_name,
        "concept": signal.concept,
        "score": round(float(signal.struggle_score), 1),
        "severity": signal.severity,
        "likely_gap": _label_gap(signal.likely_gap),
        "excerpt": signal.prompt_excerpt,
        "reasons": signal.reasons or [],
        "created_at": _iso(signal.created_at),
    } for signal, display_name in recent_rows]

    needing_attention = sum(1 for row in students if row["risk_score"] >= 50)
    return {
        "course_id": course_id,
        "days": days,
        "summary": {
            "questions": int(total or 0),
            "active_students": int(active or 0),
            "students_needing_attention": needing_attention,
            "average_struggle": round(float(avg_score or 0), 1),
            "high_concern_questions": int(high or 0),
        },
        "students": students,
        "concepts": concepts,
        "recent": recent,
        "privacy": "Only course-linked learner questions are included. General Sasha chats and AI replies are excluded.",
        "generated_at": _iso(datetime.now(timezone.utc)),
    }
