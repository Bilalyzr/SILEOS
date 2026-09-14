"""Flywheel + world-class extras (v2.0 §10 — WP8).

* next_class_agenda — Class ENDED → report → mastery → proposal for the NEXT
  class. DERIVED, works without the LLM: attendance gaps, class-wide weak
  concepts among enrolled learners, open escalations / error reports, last
  report's topics + notes. When GLM is configured, an optional polish step
  turns the same facts into prose (draft, audited).
* insight_cards — pedagogical cards from 3D evidence × question outcomes:
  per published 3D task, how learners reached their answers (clean / mixed /
  trial-and-error) and how the same learners score on the task's concepts in
  quizzes. Derived, never stored.
* teach-back — peer explanations + helpful votes (+XP, small mastery signal).
* DigiLocker / APAAR adapter — stateless; honest 503 without credentials.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.llm_provider import call_glm, glm_model, llm_configured

WEAK_PCT = 50.0


def _enrolled_ids(db: Session, course_id: int) -> List[int]:
    from app.models.enrollment import Enrollment
    return [uid for (uid,) in db.query(Enrollment.user_id)
            .filter(Enrollment.course_id == course_id, Enrollment.enrollment_status.in_(["enrolled", "completed"])).all()]


# ---------------------------------------------------------------- next-class agenda

def next_class_agenda(db: Session, course_id: int, class_id: Optional[int] = None, polish: bool = False,
                      actor_id: Optional[int] = None) -> Dict[str, Any]:
    from app.models.ai_layer import ContentErrorReport, TutorEscalation
    from app.models.live_class import LiveClass, LiveClassStatus
    from app.models.live_class_report import ClassReport
    from app.models.mastery import LearnerMastery

    learners = _enrolled_ids(db, course_id)
    # 1. the last ended class + its report
    q = db.query(LiveClass).filter(LiveClass.course_id == course_id, LiveClass.status == LiveClassStatus.ENDED)
    if class_id:
        q = q.filter(LiveClass.id == class_id)
    last = q.order_by(LiveClass.ended_at.desc().nullslast(), LiveClass.id.desc()).first()
    report = db.query(ClassReport).filter(ClassReport.class_id == last.id).first() if last else None
    absent: List[int] = []
    if report:
        present = {a.get("user_id") for a in (report.attendance or []) if a.get("present")}
        absent = [u for u in learners if u not in present]
    # 2. class-wide weak concepts (mastery graph, learner-scoped → aggregated here)
    weak: Dict[str, List[float]] = defaultdict(list)
    if learners:
        for row in db.query(LearnerMastery).filter(LearnerMastery.user_id.in_(learners), LearnerMastery.evidence_count >= 1).all():
            if row.estimate < WEAK_PCT:
                weak[row.concept].append(row.estimate)
    weak_ranked = sorted(({"concept": c, "learners": len(v), "avg_estimate": round(sum(v) / len(v), 1)} for c, v in weak.items()),
                         key=lambda r: (-r["learners"], r["avg_estimate"]))[:8]
    # 3. open loops
    escalations = db.query(TutorEscalation).filter(TutorEscalation.course_id == course_id, TutorEscalation.status == "open").count()
    reports = db.query(ContentErrorReport).filter(ContentErrorReport.course_id == course_id, ContentErrorReport.status == "open").count()
    # 4. proposal (deterministic)
    items: List[Dict[str, Any]] = []
    if report and report.ai_topics:
        items.append({"kind": "recap", "text": "Recap last class: " + "; ".join(str(t.get("topic", t)) if isinstance(t, dict) else str(t) for t in report.ai_topics[:4]), "minutes": 5})
    elif report and report.instructor_notes:
        items.append({"kind": "recap", "text": "Recap last class (from your notes): " + report.instructor_notes[:160], "minutes": 5})
    for w in weak_ranked[:3]:
        items.append({"kind": "reteach", "text": f"Re-teach {w['concept']} — {w['learners']} learner(s) below {int(WEAK_PCT)}% (avg {w['avg_estimate']}%)", "minutes": 10, "concept": w["concept"]})
    if absent:
        items.append({"kind": "catch_up", "text": f"{len(absent)} enrolled learner(s) missed the last class — point them to the recording/report before moving on", "minutes": 2})
    if escalations:
        items.append({"kind": "questions", "text": f"Answer {escalations} open learner question(s) from the tutor hand-offs", "minutes": 5})
    if reports:
        items.append({"kind": "fix", "text": f"{reports} content error report(s) open — resolve before the next quiz", "minutes": 0})
    if not items:
        items.append({"kind": "advance", "text": "No gaps detected — advance to the next planned topic", "minutes": 0})
    out = {"course_id": course_id, "based_on_class_id": last.id if last else None, "last_class_title": last.title if last else None,
           "weak_concepts": weak_ranked, "absent_count": len(absent), "open_escalations": escalations, "open_error_reports": reports,
           "agenda": items, "prose": None, "llm_configured": llm_configured()}
    if polish and llm_configured():
        from app.models.sileos_pack import AiJob
        job = AiJob(created_by=actor_id or 0, job_type="next_class_agenda", status="pending", model=glm_model(),
                    input_json={"course_id": course_id, "class_id": out["based_on_class_id"]})
        db.add(job)
        db.commit()
        try:
            prose = call_glm("You turn a factual teaching agenda into a crisp 6-8 line plan for the instructor's next live class. "
                             "Do not invent facts; keep every number.", "\n".join(f"- {i['text']} ({i['minutes']} min)" for i in items),
                             feature="Next-class agenda polishing")
            out["prose"] = prose
            job.status, job.output_json, job.finished_at = "done", {"chars": len(prose)}, datetime.now(timezone.utc)
        except Exception as exc:
            job.status, job.error, job.finished_at = "failed", str(exc)[:2000], datetime.now(timezone.utc)
        db.commit()
    return out


# ---------------------------------------------------------------- insight cards

def _tasks_for_course(db: Session, course_id: int):
    """3D tasks attached to the course's quizzes (ScorableItem kind three_d_task)."""
    from app.models.quiz import Quiz
    from app.models.three_d_task import ThreeDTask
    ids = set()
    for (mods,) in db.query(Quiz.interactive_modules).filter(Quiz.post_parent == course_id).all():
        for m in mods or []:
            if isinstance(m, dict) and m.get("kind") == "three_d_task":
                try:
                    ids.add(int(m.get("id")))
                except (TypeError, ValueError):
                    continue
    if not ids:
        return []
    return db.query(ThreeDTask).filter(ThreeDTask.id.in_(ids)).order_by(ThreeDTask.id.asc()).all()


def insight_cards(db: Session, course_id: int) -> List[Dict[str, Any]]:
    from app.models.mastery import MasteryEvidence
    from app.models.three_d_task import ThreeDTaskAttempt

    tasks = _tasks_for_course(db, course_id)
    cards: List[Dict[str, Any]] = []
    for task in tasks:
        attempts = db.query(ThreeDTaskAttempt).filter(ThreeDTaskAttempt.task_id == task.id).all()
        if not attempts:
            continue
        by_conf: Dict[str, List[ThreeDTaskAttempt]] = defaultdict(list)
        for a in attempts:
            by_conf[a.confidence or "unknown"].append(a)
        n = len(attempts)
        pct = lambda k: round(100 * len(by_conf.get(k, [])) / n)  # noqa: E731
        score = lambda k: round(sum(100 * a.score / max(a.max_score, 1) for a in by_conf.get(k, [])) / max(len(by_conf.get(k, [])), 1))  # noqa: E731
        concepts = [c for c in (task.concepts or []) if isinstance(c, str)]
        quiz_by_conf: Dict[str, List[float]] = defaultdict(list)
        if concepts:
            users_conf = {a.user_id: (a.confidence or "unknown") for a in attempts}
            rows = (db.query(MasteryEvidence).filter(MasteryEvidence.user_id.in_(list(users_conf)), MasteryEvidence.concept.in_(concepts),
                                                     MasteryEvidence.source_kind.in_(["quiz", "assignment"])).all())
            for r in rows:
                quiz_by_conf[users_conf[r.user_id]].append(r.score_pct)
        qavg = lambda k: (round(sum(quiz_by_conf[k]) / len(quiz_by_conf[k])) if quiz_by_conf.get(k) else None)  # noqa: E731
        card = {"task_id": task.id, "task_title": task.title, "task_type": task.task_type, "attempts": n, "concepts": concepts,
                "paths": {k: {"share_pct": pct(k), "avg_task_score": score(k), "avg_quiz_score": qavg(k)} for k in ("clean", "mixed", "trial_and_error")},
                "insights": []}
        tae = by_conf.get("trial_and_error", [])
        if tae and pct("trial_and_error") >= 40:
            card["insights"].append(f"{pct('trial_and_error')}% of attempts reached the answer by trial and error — the task may reward clicking over reasoning; add a 'why' prompt or tighten the anchors.")
        if qavg("clean") is not None and qavg("trial_and_error") is not None and qavg("clean") - qavg("trial_and_error") >= 15:
            card["insights"].append(f"Learners who solved it cleanly score {qavg('clean')}% on {', '.join(concepts[:2])} in quizzes vs {qavg('trial_and_error')}% for trial-and-error solvers — the path signal predicts understanding here.")
        if score("trial_and_error") >= 90 and tae:
            card["insights"].append("Trial-and-error solvers still get full marks — consider grading the path (confidence) or lowering attempts_allowed.")
        if pct("clean") >= 70:
            card["insights"].append(f"{pct('clean')}% clean paths — this task is teaching what it assesses.")
        if not card["insights"]:
            card["insights"].append("Not enough contrast yet — more attempts needed before the path signal says anything.")
        cards.append(card)
    return cards


# ---------------------------------------------------------------- teach it back

TEACH_BACK_MIN = 40
TEACH_BACK_MAX = 1500
XP_WRITE = 15
XP_HELPFUL = 5


def teach_back_dict(t, my_vote: Optional[bool] = None, author: Optional[str] = None) -> Dict[str, Any]:
    return {"id": t.id, "user_id": t.user_id, "author": author, "course_id": t.course_id, "concept": t.concept, "text": t.text,
            "status": t.status, "helpful_count": t.helpful_count, "not_helpful_count": t.not_helpful_count,
            "my_vote": my_vote, "created_at": t.created_at.isoformat() if t.created_at else None}


def write_teach_back(db: Session, user_id: int, concept: str, text: str, course_id: Optional[int]):
    from app.models.flywheel import TeachBack
    from app.services.mastery_service import normalize_concept
    concept_n = normalize_concept(concept)
    text = text.strip()
    if not concept_n:
        raise ValueError("concept is required")
    if not (TEACH_BACK_MIN <= len(text) <= TEACH_BACK_MAX):
        raise ValueError(f"explanation must be {TEACH_BACK_MIN}-{TEACH_BACK_MAX} characters")
    tb = TeachBack(user_id=user_id, course_id=course_id, concept=concept_n, text=text)
    db.add(tb)
    db.commit()
    db.refresh(tb)
    # XP (first teach-back per concept) + small mastery signal — both best-effort AFTER commit
    try:
        from app.services.gamification_service import award
        award(db, user_id, "teach_back_written", f"teach_back:{concept_n}:user:{user_id}", points=XP_WRITE, course_id=course_id,
              meta={"teach_back_id": tb.id})
        db.commit()
    except Exception:
        db.rollback()
    try:
        from app.services.mastery_service import safe_record_evidence, set_links
        set_links(db, "teach_back", tb.id, [concept_n], course_id=course_id)
        db.commit()
        safe_record_evidence(db, user_id=user_id, kind="teach_back", ref_id=tb.id, score=70.0, max_score=100.0, course_id=course_id)
    except Exception:
        db.rollback()
    return tb


def rate_teach_back(db: Session, tb_id: int, rater_id: int, helpful: bool):
    from app.models.flywheel import TeachBack, TeachBackRating
    tb = db.query(TeachBack).filter(TeachBack.id == tb_id, TeachBack.status == "visible").first()
    if tb is None:
        raise LookupError("teach-back not found")
    if tb.user_id == rater_id:
        raise ValueError("you cannot rate your own explanation")
    existing = db.query(TeachBackRating).filter(TeachBackRating.teach_back_id == tb_id, TeachBackRating.rater_id == rater_id).first()
    if existing:
        if existing.helpful == helpful:
            return tb, False
        if existing.helpful:
            tb.helpful_count = max(0, tb.helpful_count - 1)
        else:
            tb.not_helpful_count = max(0, tb.not_helpful_count - 1)
        existing.helpful = helpful
    else:
        db.add(TeachBackRating(teach_back_id=tb_id, rater_id=rater_id, helpful=helpful))
    if helpful:
        tb.helpful_count += 1
    else:
        tb.not_helpful_count += 1
    db.commit()
    if helpful and tb.helpful_count in (3, 10):
        try:
            from app.services.gamification_service import award
            award(db, tb.user_id, "teach_back_helpful", f"teach_back:{tb.id}:helpful{tb.helpful_count}:user:{tb.user_id}",
                  points=XP_HELPFUL * (2 if tb.helpful_count == 10 else 1), course_id=tb.course_id)
            db.commit()
        except Exception:
            db.rollback()
    return tb, True


# ---------------------------------------------------------------- DigiLocker / APAAR adapter

def digilocker_configured() -> bool:
    return bool(os.environ.get("DIGILOCKER_CLIENT_ID")) and bool(os.environ.get("DIGILOCKER_CLIENT_SECRET"))


def digilocker_payload(issued) -> Dict[str, Any]:
    """The document descriptor a DigiLocker 'Issuer' push would carry. Pure
    mapping — no network here; the push itself needs owner credentials."""
    return {
        "doc_type": "CRTF", "issuer": os.environ.get("DIGILOCKER_ISSUER_ID", "sashainfinity"),
        "uri_suffix": issued.secure_certificate_id, "verification_hash": issued.certificate_hash,
        "holder_user_id": issued.user_id, "course_id": issued.course_id, "title": issued.certificate_title,
        "issued_on": issued.completion_date.date().isoformat() if issued.completion_date else None,
        "apaar_id_field": "APAAR_ID (from the learner's profile once ABC-ID capture ships)",
        "file_path": issued.certificate_file_path or None,
    }
