"""Mastery graph service (v2.0 §9.5 / §8.3 / §10.1 — WP3).

Doctrine (same as award() / emit_statement): `record_evidence` is called
best-effort from every scoring path AFTER that path's own commit, wrapped in
try/except at the call site, and it flushes + commits ONLY its own rows. A
mastery hiccup must never fail a quiz submit, a game result or a lab result.

Estimate = recency-weighted mean of evidence (newest weight 1, then ×0.85 per
older row) times the source weight; confidence = 1 − 1/(1 + Σweights), so one
weak practice game gives low confidence and three supervised quizzes give
high confidence. All numbers are explainable to an instructor.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.mastery import ConceptLink, ConceptPrerequisite, CourseOutcome, LearnerMastery, MasteryEvidence

logger = logging.getLogger(__name__)

LINK_KINDS = {"quiz", "question", "game", "h5p", "lab", "three_d_task", "lesson", "assignment", "course", "live_class", "teach_back", "practice_question"}
MAX_CONCEPTS_PER_ITEM = 20
RECENCY_DECAY = 0.85
WEAK_THRESHOLD = 50.0

# §9.5 evidence weights by source; 3D tasks are further scaled by the path.
SOURCE_WEIGHTS: Dict[str, float] = {
    "quiz": 1.0, "assignment": 1.0, "three_d_task": 1.0, "lab": 0.7, "h5p": 0.6, "game": 0.5,
    "teach_back": 0.3,   # WP8 peer explanation — a weak, self-reported signal
}
PATH_MULTIPLIER = {"clean": 1.0, "mixed": 0.8, "trial_and_error": 0.5, "unknown": 0.8}


def normalize_concept(raw: str) -> str:
    return " ".join(str(raw).strip().lower().split())[:80]


def clean_concepts(raw: Optional[Iterable[str]]) -> List[str]:
    out, seen = [], set()
    for c in raw or []:
        if not isinstance(c, str):
            continue
        s = normalize_concept(c)
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out[:MAX_CONCEPTS_PER_ITEM]


# ---------------------------------------------------------------- links

def set_links(db: Session, kind: str, ref_id, concepts: Iterable[str], course_id: Optional[int] = None,
              user_id: Optional[int] = None) -> List[str]:
    """Replace the concept set of one element. Commits."""
    if kind not in LINK_KINDS:
        raise ValueError(f"kind must be one of {sorted(LINK_KINDS)}")
    ref = str(ref_id)
    wanted = clean_concepts(concepts)
    existing = db.query(ConceptLink).filter(ConceptLink.kind == kind, ConceptLink.ref_id == ref).all()
    have = {e.concept: e for e in existing}
    for concept, row in have.items():
        if concept not in wanted:
            db.delete(row)
        elif course_id is not None and row.course_id != course_id:
            row.course_id = course_id
    for concept in wanted:
        if concept not in have:
            db.add(ConceptLink(kind=kind, ref_id=ref, concept=concept, course_id=course_id, created_by=user_id))
    db.commit()
    return wanted


def concepts_for(db: Session, kind: str, ref_id) -> List[str]:
    ref = str(ref_id)
    rows = db.query(ConceptLink.concept).filter(ConceptLink.kind == kind, ConceptLink.ref_id == ref).all()
    concepts = [r[0] for r in rows]
    if kind == "lab" and not concepts:
        # Native labs may declare concepts in the catalog (built-ins do).
        try:
            from app.routers.virtual_labs import get_lab
            lab = get_lab(db, ref)
            concepts = clean_concepts((lab or {}).get("concepts") or ((lab or {}).get('config') or {}).get('concepts') or [])
        except Exception:
            concepts = []
    if kind == "three_d_task" and not concepts:
        try:
            from app.models.three_d_task import ThreeDTask
            t = db.query(ThreeDTask).filter(ThreeDTask.id == int(ref)).first()
            concepts = clean_concepts((t.concepts if t else None) or [])
        except Exception:
            concepts = []
    return concepts


# ---------------------------------------------------------------- evidence → estimate

def _recompute(db: Session, user_id: int, concept: str) -> LearnerMastery:
    rows = (db.query(MasteryEvidence)
            .filter(MasteryEvidence.user_id == user_id, MasteryEvidence.concept == concept)
            .order_by(MasteryEvidence.created_at.desc(), MasteryEvidence.id.desc())
            .limit(50).all())
    num = den = total_w = 0.0
    for i, r in enumerate(rows):
        w = float(r.weight or 0) * (RECENCY_DECAY ** i)
        num += float(r.score_pct) * w
        den += w
        total_w += float(r.weight or 0)
    estimate = round(num / den, 1) if den > 0 else 0.0
    confidence = round(1.0 - 1.0 / (1.0 + total_w), 3) if total_w > 0 else 0.0
    lm = db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id, LearnerMastery.concept == concept).first()
    if lm is None:
        lm = LearnerMastery(user_id=user_id, concept=concept)
        db.add(lm)
    lm.estimate = estimate
    lm.confidence = confidence
    lm.evidence_count = len(rows)
    lm.last_evidence_at = rows[0].created_at if rows and rows[0].created_at else datetime.now(timezone.utc)
    return lm


def record_evidence(db: Session, user_id: int, kind: str, ref_id, score: float, max_score: float,
                    course_id: Optional[int] = None, path_confidence: Optional[str] = None,
                    weight_override: Optional[float] = None) -> List[str]:
    """Write one evidence row per concept the source declares and refresh the
    learner's estimates. Returns the concepts touched (empty = nothing declared).
    Commits its own rows; call AFTER the caller's commit, inside try/except."""
    if not max_score or max_score <= 0:
        return []
    concepts = concepts_for(db, kind, ref_id)
    if not concepts:
        return []
    pct = max(0.0, min(100.0, float(score) / float(max_score) * 100.0))
    weight = weight_override if weight_override is not None else SOURCE_WEIGHTS.get(kind, 0.5)
    if kind == "three_d_task" and path_confidence:
        weight *= PATH_MULTIPLIER.get(path_confidence, 0.8)
    for concept in concepts:
        db.add(MasteryEvidence(user_id=user_id, concept=concept, source_kind=kind, source_ref=str(ref_id),
                               score_pct=pct, weight=weight, course_id=course_id,
                               detail={"confidence": path_confidence} if path_confidence else None))
    db.flush()
    for concept in concepts:
        _recompute(db, user_id, concept)
    db.commit()
    return concepts


def safe_record_evidence(db: Session, **kwargs) -> None:
    """Best-effort wrapper for call sites."""
    try:
        record_evidence(db, **kwargs)
    except Exception as exc:  # never fail the host request
        logger.warning("mastery evidence failed (%s): %s", kwargs.get("kind"), exc)
        try:
            db.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------- graph reads

def level_for(estimate: float) -> str:
    return "novice" if estimate < 40 else "developing" if estimate < 70 else "proficient" if estimate < 90 else "mastered"


def learner_graph(db: Session, user_id: int) -> dict:
    rows = db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id).order_by(LearnerMastery.concept).all()
    by = {r.concept: r for r in rows}
    prereqs = db.query(ConceptPrerequisite).filter(ConceptPrerequisite.concept.in_(list(by) or [""])).all()
    req_map: Dict[str, List[str]] = {}
    for p in prereqs:
        req_map.setdefault(p.concept, []).append(p.requires)
    nodes = []
    gaps = []
    for r in rows:
        requires = req_map.get(r.concept, [])
        missing = [q for q in requires if (by.get(q).estimate if by.get(q) else 0.0) < WEAK_THRESHOLD]
        node = {
            "concept": r.concept, "estimate": r.estimate, "confidence": r.confidence, "level": level_for(r.estimate),
            "evidence_count": r.evidence_count, "last_evidence_at": r.last_evidence_at, "requires": requires,
            "prerequisite_gaps": missing,
        }
        nodes.append(node)
        if missing and r.estimate < 70:
            gaps.append({"concept": r.concept, "recover_first": missing})
    weak = sorted([n for n in nodes if n["estimate"] < WEAK_THRESHOLD and n["evidence_count"] >= 1],
                  key=lambda n: (n["estimate"], -n["confidence"]))
    overall = round(sum(n["estimate"] for n in nodes) / len(nodes), 1) if nodes else 0.0
    return {"user_id": user_id, "concepts": nodes, "weak_concepts": [n["concept"] for n in weak[:10]],
            "recover_first": gaps, "overall": overall, "overall_level": level_for(overall)}


def weak_concepts(db: Session, user_id: int, limit: int = 10) -> List[dict]:
    rows = (db.query(LearnerMastery)
            .filter(LearnerMastery.user_id == user_id, LearnerMastery.estimate < WEAK_THRESHOLD,
                    LearnerMastery.evidence_count >= 1)
            .order_by(LearnerMastery.estimate.asc()).limit(limit).all())
    return [{"concept": r.concept, "estimate": r.estimate, "confidence": r.confidence} for r in rows]


def evidence_for_concept(db: Session, user_id: int, concept: str, limit: int = 20) -> List[dict]:
    rows = (db.query(MasteryEvidence)
            .filter(MasteryEvidence.user_id == user_id, MasteryEvidence.concept == normalize_concept(concept))
            .order_by(MasteryEvidence.created_at.desc(), MasteryEvidence.id.desc()).limit(limit).all())
    return [{"source_kind": r.source_kind, "source_ref": r.source_ref, "score_pct": r.score_pct, "weight": r.weight,
             "course_id": r.course_id, "detail": r.detail, "created_at": r.created_at} for r in rows]


# ---------------------------------------------------------------- course coverage (§8.3 #1, §4.3)

TEACHING_KINDS = {"lesson", "lab", "h5p", "game", "course", "live_class"}
ASSESSING_KINDS = {"quiz", "question", "three_d_task", "lab", "assignment", "game"}


def course_elements(db: Session, course_id: int) -> List[dict]:
    """Every element of a course that can declare concepts, with current links."""
    from app.models.course import Lesson
    from app.models.quiz import Quiz
    from app.models.assignment import Assignment
    els: List[dict] = []
    for l in db.query(Lesson).filter(Lesson.post_parent == course_id).order_by(Lesson.menu_order, Lesson.id).all():
        ct = getattr(l, "lesson_content_type", None) or "video"
        els.append({"kind": "lesson", "ref_id": str(l.id), "title": l.post_title, "role": "teaches",
                    "content_type": ct})
        if ct == "virtual_lab" and getattr(l, "virtual_lab_sim", None):
            els.append({"kind": "lab", "ref_id": l.virtual_lab_sim, "title": f"Lab: {l.virtual_lab_sim}", "role": "teaches+assesses"})
        if ct == "game" and getattr(l, "game_id", None):
            els.append({"kind": "game", "ref_id": str(l.game_id), "title": f"Game #{l.game_id}", "role": "teaches+assesses"})
    for q in db.query(Quiz).filter(Quiz.post_parent == course_id).all():
        els.append({"kind": "quiz", "ref_id": str(q.id), "title": q.post_title, "role": "assesses"})
        for m in (q.interactive_modules or []):
            if m.get("kind") in ("three_d_task", "lab", "game", "h5p"):
                els.append({"kind": m["kind"], "ref_id": str(m["id"]), "title": m.get("title") or f"{m['kind']} {m['id']}",
                            "role": "assesses", "practice_only": bool(m.get("practice_only"))})
    try:
        for a in db.query(Assignment).filter(Assignment.course_id == course_id).all():
            els.append({"kind": "assignment", "ref_id": str(a.id), "title": getattr(a, "title", f"Assignment {a.id}"), "role": "assesses"})
    except Exception:
        pass
    # de-duplicate (a lab can be both a lesson and a quiz item)
    seen, out = set(), []
    for e in els:
        k = (e["kind"], e["ref_id"])
        if k in seen:
            continue
        seen.add(k)
        e["concepts"] = concepts_for(db, e["kind"], e["ref_id"])
        out.append(e)
    return out


def course_coverage(db: Session, course_id: int) -> dict:
    els = course_elements(db, course_id)
    taught: Dict[str, List[str]] = {}
    assessed: Dict[str, List[str]] = {}
    for e in els:
        for c in e["concepts"]:
            if e["kind"] in TEACHING_KINDS or "teaches" in e["role"]:
                taught.setdefault(c, []).append(e["title"])
            if e["kind"] in ASSESSING_KINDS and "assesses" in e["role"] and not e.get("practice_only"):
                assessed.setdefault(c, []).append(e["title"])
    outcome = db.query(CourseOutcome).filter(CourseOutcome.course_id == course_id).first()
    targets = clean_concepts(outcome.target_concepts if outcome else [])
    all_concepts = sorted(set(taught) | set(assessed) | set(targets))
    rows = []
    for c in all_concepts:
        rows.append({
            "concept": c, "taught_by": taught.get(c, []), "assessed_by": assessed.get(c, []),
            "is_target": c in targets,
            "gap": ("no_teaching" if c in assessed and c not in taught else
                    "no_assessment" if c in taught and c not in assessed else
                    "target_uncovered" if c in targets and c not in taught and c not in assessed else None),
        })
    gaps = [r for r in rows if r["gap"]]
    return {"course_id": course_id, "outcome": {"text": outcome.outcome_text if outcome else "",
                                                "target_concepts": targets},
            "elements": els, "concepts": rows, "gaps": gaps,
            "summary": {"concepts": len(rows), "taught": len(taught), "assessed": len(assessed),
                        "targets": len(targets), "gaps": len(gaps)}}


def progress_map(db: Session, course_id: int, user_id: int) -> dict:
    """§8.3 #2 — the learner path: every element as a milestone with its own
    completion and the learner's mastery of the concepts it carries."""
    els = course_elements(db, course_id)
    mastery = {r.concept: r for r in db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id).all()}
    from app.models.enrollment import Enrollment
    enr = db.query(Enrollment).filter(Enrollment.course_id == course_id, Enrollment.user_id == user_id).first()
    completed_lessons = set()
    try:
        from app.models.enrollment import LessonProgress
        completed_lessons = {str(r.lesson_id) for r in db.query(LessonProgress)
                             .filter(LessonProgress.user_id == user_id, LessonProgress.course_id == course_id,
                                     LessonProgress.progress_status == "completed").all()}
    except Exception:
        pass
    from app.schemas.scorable import best_item_score
    from app.models.quiz import QuizAttempt
    milestones = []
    for e in els:
        state = "not_started"
        score = None
        if e["kind"] == "lesson":
            state = "completed" if e["ref_id"] in completed_lessons else "not_started"
        elif e["kind"] == "quiz":
            att = (db.query(QuizAttempt).filter(QuizAttempt.quiz_id == int(e["ref_id"]), QuizAttempt.user_id == user_id,
                                                 QuizAttempt.attempt_status.in_(["attempt_submitted", "attempt_ended"]))
                   .order_by(QuizAttempt.earned_marks.desc()).first())
            if att and float(att.total_marks or 0) > 0:
                score = round(float(att.earned_marks or 0) / float(att.total_marks) * 100, 1)
                state = "completed"
        elif e["kind"] in ("game", "lab", "three_d_task", "h5p"):
            res = best_item_score(db, {"kind": e["kind"], "id": int(e["ref_id"]) if e["kind"] != "lab" else e["ref_id"]}, user_id)
            if res and res[1] > 0:
                score = round(res[0] / res[1] * 100, 1)
                state = "completed"
        concept_mastery = [{"concept": c, "estimate": mastery[c].estimate if c in mastery else None} for c in e["concepts"]]
        est = [m["estimate"] for m in concept_mastery if m["estimate"] is not None]
        milestones.append({**e, "state": state, "score_pct": score,
                           "concept_mastery": concept_mastery,
                           "mastery": round(sum(est) / len(est), 1) if est else None})
    return {"course_id": course_id, "user_id": user_id,
            "progress_pct": int(enr.course_progress_percentage or 0) if enr else 0,
            "milestones": milestones}
