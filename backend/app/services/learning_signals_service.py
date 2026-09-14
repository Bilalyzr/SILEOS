"""Learning-signals engine (2026-09-06): ingest → struggle detection →
adaptive assessment. Everything derived is computed at read time.
"""
from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.learning_signals import AdaptiveSession, LearningSignal, LessonConceptMarker

logger = logging.getLogger(__name__)

KINDS = {
    "video_rewind": 1.0,      # jumped back (value = seconds)
    "video_replay": 1.5,      # re-watched a segment
    "video_pause": 0.3,
    "video_skip": -0.2,       # jumped forward — confident or bored, mildly negative
    "rate_change": 0.0,       # informational (value = playback rate)
    "quit_early": 2.0,        # left before 60% watched (value = pct watched)
    "note_written": -0.5,     # taking notes = engaged
    "question_time": 0.0,     # scored below by threshold (value = seconds)
    "answer_change": 0.0,     # scored below by threshold (value = changes)
    "adaptive_result": 0.0,
}
HESITATION_SECONDS = 45
ANSWER_CHANGES = 2
SEGMENT_SECONDS = 10
PROFILE_WINDOW_DAYS = 60
MAX_BATCH = 200
# Open-ended types need a human — adaptive practice is auto-graded, so they never enter a set.
UNGRADABLE_TYPES = ("essay", "open_ended", "file_upload", "image_answering")


def _seg(position_s: Optional[int]) -> Optional[int]:
    return None if position_s is None else int(position_s) // SEGMENT_SECONDS


def ingest(db: Session, user_id: int, events: List[dict]) -> int:
    rows = []
    for e in events[:MAX_BATCH]:
        kind = str(e.get("kind") or "")
        if kind not in KINDS:
            continue
        pos = e.get("position_s")
        pos = int(pos) if isinstance(pos, (int, float)) and pos >= 0 else None
        val = e.get("value")
        val = float(val) if isinstance(val, (int, float)) else None
        meta = {k: v for k, v in (e.get("meta") or {}).items() if isinstance(k, str) and isinstance(v, (str, int, float, bool))}
        rows.append(LearningSignal(user_id=user_id, course_id=e.get("course_id"), lesson_id=e.get("lesson_id"),
                                   quiz_id=e.get("quiz_id"), question_id=e.get("question_id"), kind=kind,
                                   position_s=pos, segment=_seg(pos), value=val, meta=meta or None))
    if rows:
        db.add_all(rows)
        db.commit()
    return len(rows)


# ---------------------------------------------------------------- concept attribution

def markers_for(db: Session, lesson_id: int) -> List[LessonConceptMarker]:
    return db.query(LessonConceptMarker).filter(LessonConceptMarker.lesson_id == lesson_id).order_by(LessonConceptMarker.time_s.asc()).all()


def concept_at(markers: List[LessonConceptMarker], position_s: Optional[int], fallback: List[str]) -> List[str]:
    """The marker in force at `position_s` (latest marker at or before it); a
    lesson without markers attributes every signal to its lesson concepts."""
    if position_s is not None and markers:
        current = None
        for m in markers:
            if m.time_s <= position_s:
                current = m
            else:
                break
        if current:
            return [current.concept]
    return fallback


def lesson_concepts(db: Session, lesson_id: int) -> List[str]:
    from app.services.mastery_service import concepts_for
    try:
        return concepts_for(db, "lesson", lesson_id)
    except Exception:
        return []


# ---------------------------------------------------------------- heat-map

def lesson_heatmap(db: Session, lesson_id: int, user_id: Optional[int] = None, days: int = PROFILE_WINDOW_DAYS) -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(LearningSignal).filter(LearningSignal.lesson_id == lesson_id, LearningSignal.created_at >= since,
                                        LearningSignal.segment.isnot(None))
    if user_id:
        q = q.filter(LearningSignal.user_id == user_id)
    rows = q.all()
    markers = markers_for(db, lesson_id)
    fallback = lesson_concepts(db, lesson_id)
    segs: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"rewinds": 0, "replays": 0, "pauses": 0, "skips": 0, "learners": set(), "score": 0.0})
    for r in rows:
        s = segs[r.segment]
        if r.kind == "video_rewind":
            s["rewinds"] += 1
        elif r.kind == "video_replay":
            s["replays"] += 1
        elif r.kind == "video_pause":
            s["pauses"] += 1
        elif r.kind == "video_skip":
            s["skips"] += 1
        s["learners"].add(r.user_id)
        s["score"] += KINDS.get(r.kind, 0.0)
    out = []
    for seg, s in sorted(segs.items()):
        start = seg * SEGMENT_SECONDS
        out.append({"segment": seg, "start_s": start, "end_s": start + SEGMENT_SECONDS, "rewinds": s["rewinds"], "replays": s["replays"],
                    "pauses": s["pauses"], "skips": s["skips"], "learners": len(s["learners"]), "score": round(s["score"], 2),
                    "concepts": concept_at(markers, start, fallback)})
    hot = sorted((x for x in out if x["score"] > 0), key=lambda x: -x["score"])[:5]
    quits = db.query(func.count(LearningSignal.id)).filter(LearningSignal.lesson_id == lesson_id, LearningSignal.kind == "quit_early",
                                                            LearningSignal.created_at >= since).scalar() or 0
    return {"lesson_id": lesson_id, "segments": out, "struggle_segments": hot, "early_quits": int(quits),
            "markers": [{"id": m.id, "time_s": m.time_s, "concept": m.concept} for m in markers], "lesson_concepts": fallback}


# ---------------------------------------------------------------- learner struggle profile

def _fmt_pos(p: Optional[int]) -> str:
    if p is None:
        return ""
    return f"{p // 60}:{p % 60:02d}"


def learner_profile(db: Session, user_id: int, course_id: Optional[int] = None, days: int = PROFILE_WINDOW_DAYS) -> Dict[str, Any]:
    from app.models.course import Lesson
    from app.models.mastery import LearnerMastery
    from app.services.mastery_service import concepts_for
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(LearningSignal).filter(LearningSignal.user_id == user_id, LearningSignal.created_at >= since)
    if course_id:
        q = q.filter(LearningSignal.course_id == course_id)
    rows = q.order_by(LearningSignal.id.asc()).limit(5000).all()
    marker_cache: Dict[int, List[LessonConceptMarker]] = {}
    lesson_cache: Dict[int, List[str]] = {}
    q_cache: Dict[int, List[str]] = {}
    lesson_titles = {}
    scores: Dict[str, float] = defaultdict(float)
    reasons: Dict[str, List[str]] = defaultdict(list)
    counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        concepts: List[str] = []
        if r.lesson_id:
            if r.lesson_id not in marker_cache:
                marker_cache[r.lesson_id] = markers_for(db, r.lesson_id)
                lesson_cache[r.lesson_id] = lesson_concepts(db, r.lesson_id)
                lt = db.query(Lesson.post_title).filter(Lesson.id == r.lesson_id).first()
                lesson_titles[r.lesson_id] = lt[0] if lt else f"lesson {r.lesson_id}"
            concepts = concept_at(marker_cache[r.lesson_id], r.position_s, lesson_cache[r.lesson_id])
        elif r.question_id:
            if r.question_id not in q_cache:
                c = concepts_for(db, "question", r.question_id)
                if not c and r.quiz_id:
                    c = concepts_for(db, "quiz", r.quiz_id)
                q_cache[r.question_id] = c
            concepts = q_cache[r.question_id]
        if not concepts:
            continue
        w = KINDS.get(r.kind, 0.0)
        if r.kind == "question_time" and (r.value or 0) >= HESITATION_SECONDS:
            w = 1.0
        if r.kind == "answer_change" and (r.value or 0) >= ANSWER_CHANGES:
            w = 0.7
        if w == 0:
            continue
        for c in concepts:
            scores[c] += w
            counts[c][r.kind] += 1
    # assemble
    top = max(scores.values(), default=0.0)
    mastery = {m.concept: (m.estimate, m.confidence) for m in db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id).all()}
    out = []
    for c, s in scores.items():
        why = []
        k = counts[c]
        if k.get("video_rewind"):
            why.append(f"rewound {k['video_rewind']}×")
        if k.get("video_replay"):
            why.append(f"re-watched {k['video_replay']} segment{'s' if k['video_replay'] != 1 else ''}")
        if k.get("quit_early"):
            why.append(f"left early {k['quit_early']}×")
        if k.get("question_time"):
            why.append(f"hesitated on {k['question_time']} question{'s' if k['question_time'] != 1 else ''}")
        if k.get("answer_change"):
            why.append(f"changed answers {k['answer_change']}×")
        if k.get("note_written"):
            why.append(f"took {k['note_written']} note{'s' if k['note_written'] != 1 else ''}")
        est, conf = mastery.get(c, (None, None))
        out.append({"concept": c, "struggle": round(100.0 * s / top, 1) if top > 0 else 0.0, "raw": round(s, 2), "why": why,
                    "mastery": round(est, 1) if est is not None else None, "confidence": round(conf, 2) if conf is not None else None})
    out.sort(key=lambda x: -x["struggle"])
    struggling = [x for x in out if x["raw"] >= 1.5]
    return {"user_id": user_id, "course_id": course_id, "days": days, "signals": len(rows), "concepts": out,
            "struggling": struggling[:8], "confident": [x for x in out if x["raw"] < 0][:5]}


# ---------------------------------------------------------------- adaptive assessment

def _difficulty_of(q) -> str:
    st = q.question_settings or {}
    return str(st.get("difficulty") or "medium")


def build_adaptive(db: Session, user_id: int, course_id: int, count: int = 8, focus_concepts: Optional[List[str]] = None, focus_only: bool = False, commit: bool = True, phase: str = "practice") -> AdaptiveSession:
    """Compose a practice set: struggling concepts first, then weak mastery,
    then the rest; difficulty from mastery (easy < 40, medium < 75, hard);
    item types varied; never a question the learner answered in the last
    adaptive session. Returns the stored session (questions stripped of keys
    by the router)."""
    if focus_only:
        from app.services.assessment_studio_service import build_focused
        return build_focused(db, user_id, course_id, count, focus_concepts, phase, commit)
    from app.models.quiz import Quiz, QuizQuestion
    from app.services.mastery_service import concepts_for
    from sqlalchemy import or_
    profile = learner_profile(db, user_id, course_id)
    weights: Dict[str, float] = {}
    for c in profile["concepts"]:
        weights[c["concept"]] = weights.get(c["concept"], 0.0) + max(0.0, c["raw"])
        if c["mastery"] is not None:
            weights[c["concept"]] += max(0.0, (60 - c["mastery"]) / 20)
    from app.models.mastery import LearnerMastery
    for m in db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id).all():
        if m.estimate < 60:
            weights[m.concept] = weights.get(m.concept, 0.0) + (60 - m.estimate) / 20
    from app.services.mastery_service import clean_concepts
    focus = clean_concepts(focus_concepts)
    for concept in focus:
        weights[concept] = max(1.0, weights.get(concept, 0.0)) * 2
    quiz_query = db.query(Quiz).filter(Quiz.post_parent == course_id)
    if focus_only:
        quiz_query = quiz_query.filter(Quiz.post_status.in_(["publish", "published"]),
                                       or_(Quiz.quiz_feedback_mode.is_(None), Quiz.quiz_feedback_mode != "reveal_never"))
    quizzes = quiz_query.all()
    quiz_concepts = {qz.id: concepts_for(db, "quiz", qz.id) for qz in quizzes}
    questions = (db.query(QuizQuestion).filter(QuizQuestion.quiz_id.in_([qz.id for qz in quizzes] or [0]),
                                               or_(QuizQuestion.is_retired.is_(None), QuizQuestion.is_retired.is_(False)),
                                               QuizQuestion.question_type.notin_(UNGRADABLE_TYPES)).all())
    last = (db.query(AdaptiveSession).filter(AdaptiveSession.user_id == user_id, AdaptiveSession.course_id == course_id)
            .order_by(AdaptiveSession.id.desc()).first())
    recent = set(last.question_ids or []) if last else set()
    scored = []
    for q in questions:
        cs = concepts_for(db, "question", q.question_id) or quiz_concepts.get(q.quiz_id, [])
        if focus_only and q.question_type not in ("multiple_choice", "multiple_select", "true_false", "fill_in_blanks", "short_answer"):
            continue
        if focus_only and not set(cs).intersection(focus):
            continue
        pri = max((weights.get(c, 0.0) for c in cs), default=0.0)
        mastery_vals = [m.estimate for m in db.query(LearnerMastery).filter(LearnerMastery.user_id == user_id, LearnerMastery.concept.in_(cs)).all()] if cs else []
        est = sum(mastery_vals) / len(mastery_vals) if mastery_vals else None
        want = "easy" if est is not None and est < 40 else "hard" if est is not None and est >= 75 else "medium"
        fit = 1.0 if _difficulty_of(q) == want else 0.6
        scored.append((pri * fit + random.random() * 0.05 - (0.5 if q.question_id in recent else 0.0), q, cs, want))
    scored.sort(key=lambda t: -t[0])
    chosen, types_seen, skipped = [], defaultdict(int), []
    for pri, q, cs, want in scored:
        if len(chosen) >= count:
            break
        if types_seen[q.question_type] >= max(2, count // 2) and len(scored) > count:
            skipped.append((q, cs, want))   # variety first…
            continue
        chosen.append((q, cs, want))
        types_seen[q.question_type] += 1
    for item in skipped:                      # …but never short-change the set
        if len(chosen) >= count:
            break
        chosen.append(item)
    plan = {"focus_concepts": focus, "concepts": list(dict.fromkeys(focus + [c["concept"] for c in profile["struggling"][:5]])),
            "why": [f"{c['concept']}: {', '.join(c['why'])}" for c in profile["struggling"][:5]],
            "difficulty": {q.question_id: want for q, _, want in chosen}}
    sess = AdaptiveSession(user_id=user_id, course_id=course_id, question_ids=[q.question_id for q, _, _ in chosen], plan=plan)
    db.add(sess)
    if commit:
        db.commit()
        db.refresh(sess)
    else:
        db.flush()
    return sess


def adaptive_questions(db: Session, sess: AdaptiveSession) -> List[Dict[str, Any]]:
    from app.models.quiz import QuizQuestion, QuizQuestionAnswer
    from app.services.mastery_service import concepts_for
    out = []
    for qid in sess.question_ids or []:
        if qid < 0:
            from app.services.assessment_studio_service import studio_snapshot
            snapshot = studio_snapshot(db, qid, sess.course_id)
            if snapshot:
                out.append({k: v for k, v in snapshot.items() if k in ("question_id", "title", "type", "marks", "options", "concepts", "difficulty")})
            continue
        q = db.query(QuizQuestion).filter(QuizQuestion.question_id == qid).first()
        if not q:
            continue
        answers = db.query(QuizQuestionAnswer).filter(QuizQuestionAnswer.belongs_question_id == qid).order_by(QuizQuestionAnswer.answer_order.asc()).all()
        out.append({"question_id": q.question_id, "title": q.question_title, "type": q.question_type, "marks": float(q.question_mark or 1),
                    "options": [a.answer_title for a in answers] if q.question_type in ("multiple_choice", "multiple_select", "true_false") else [],
                    "concepts": concepts_for(db, "question", qid) or concepts_for(db, "quiz", q.quiz_id),
                    "difficulty": (sess.plan or {}).get("difficulty", {}).get(str(qid)) or (sess.plan or {}).get("difficulty", {}).get(qid) or "medium"})
    return out


def grade_adaptive(db: Session, sess: AdaptiveSession, answers: Dict[str, Any]) -> Dict[str, Any]:
    from app.models.quiz import QuizQuestion, QuizQuestionAnswer
    from app.services.mastery_service import concepts_for, safe_record_evidence
    results, score, max_score = [], 0, 0
    for qid in sess.question_ids or []:
        if qid < 0:
            from app.services.assessment_studio_service import studio_snapshot
            snapshot = studio_snapshot(db, qid, sess.course_id)
            if not snapshot:
                continue
            correct = {str(x).strip().lower() for x in snapshot["expected"]}
            given = answers.get(str(qid), answers.get(qid))
            given_set = {str(x).strip().lower() for x in (given if isinstance(given, list) else [given])} if given not in (None, "") else set()
            ok = bool(given_set) and (given_set == correct if snapshot["type"] == "multiple_select" else len(given_set) == 1 and bool(given_set & correct))
            max_score += 1
            score += int(ok)
            results.append({"question_id": qid, "correct": ok, "concepts": snapshot["concepts"], "expected": sorted(correct), "explanation": snapshot["explanation"]})
            continue
        q = db.query(QuizQuestion).filter(QuizQuestion.question_id == qid).first()
        if not q:
            continue
        correct_rows = db.query(QuizQuestionAnswer).filter(QuizQuestionAnswer.belongs_question_id == qid, QuizQuestionAnswer.is_correct.is_(True)).all()
        correct = {str(a.answer_title).strip().lower() for a in correct_rows}
        given = answers.get(str(qid), answers.get(qid))
        given_set = {str(x).strip().lower() for x in (given if isinstance(given, list) else [given])} if given not in (None, "") else set()
        ok = bool(given_set) and (given_set == correct if q.question_type == "multiple_select" else len(given_set) == 1 and bool(given_set & correct))
        max_score += 1
        score += 1 if ok else 0
        cs = concepts_for(db, "question", qid) or concepts_for(db, "quiz", q.quiz_id)
        results.append({"question_id": qid, "correct": ok, "concepts": cs, "expected": sorted(correct)})
    sess.answers = {str(k): v for k, v in answers.items()}
    sess.results = results
    sess.score, sess.max_score = score, max_score
    sess.submitted_at = datetime.now(timezone.utc)
    db.commit()
    # mastery evidence per question (kind question → its links, fallback quiz), AFTER commit, best-effort
    for r in results:
        try:
            q = db.query(QuizQuestion).filter(QuizQuestion.question_id == r["question_id"]).first()
            kind, ref = (("practice_question", -r["question_id"]) if r["question_id"] < 0 else
                         ("question", r["question_id"]) if concepts_for(db, "question", r["question_id"]) else ("quiz", q.quiz_id if q else None))
            if ref is not None:
                safe_record_evidence(db, user_id=sess.user_id, kind=kind, ref_id=ref, score=1.0 if r["correct"] else 0.0, max_score=1.0,
                                     course_id=sess.course_id, weight_override=0.8)
        except Exception:
            logger.debug("adaptive evidence skipped", exc_info=True)
    try:
        ingest(db, sess.user_id, [{"kind": "adaptive_result", "course_id": sess.course_id, "value": score / max_score if max_score else 0.0,
                                  "meta": {"session_id": sess.id}}])
    except Exception:
        pass
    by_concept: Dict[str, List[bool]] = defaultdict(list)
    for r in results:
        for c in r["concepts"]:
            by_concept[c].append(r["correct"])
    return {"session_id": sess.id, "score": score, "max_score": max_score, "results": results,
            "by_concept": [{"concept": c, "correct": sum(v), "total": len(v)} for c, v in by_concept.items()]}



def course_segments(db: Session, course_id: int, days: int = 30, now=None) -> Dict[str, Any]:
    """Aggregate observed segments using authoritative lesson ownership, not client course IDs."""
    from app.models.course import Lesson
    since = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    lessons = {l.id: l for l in db.query(Lesson).filter(Lesson.post_parent == course_id).all()}
    rows = db.query(LearningSignal).filter(
        LearningSignal.lesson_id.in_(list(lessons)), LearningSignal.created_at >= since).all()
    markers = {lid: markers_for(db, lid) for lid in lessons}
    fallback = {lid: lesson_concepts(db, lid) for lid in lessons}
    segments, quits, raw = {}, defaultdict(int), defaultdict(float)
    for r in rows:
        if r.kind == "quit_early":
            quits[r.lesson_id] += 1
        concepts = concept_at(markers[r.lesson_id], r.position_s, fallback[r.lesson_id])
        for c in concepts:
            raw[(c, r.user_id)] += KINDS.get(r.kind, 0.0)
        if r.segment is None:
            continue
        key = (r.lesson_id, r.segment)
        if key not in segments:
            start = r.segment * SEGMENT_SECONDS
            segments[key] = dict(lesson_id=r.lesson_id, lesson_title=lessons[r.lesson_id].post_title,
                                 segment=r.segment, start_s=start, end_s=start + SEGMENT_SECONDS,
                                 score=0.0, learners=set(), rewinds=0, replays=0, early_quits=0,
                                 concepts=concept_at(markers[r.lesson_id], start, fallback[r.lesson_id]))
        s = segments[key]
        s["score"] += KINDS.get(r.kind, 0.0)
        s["learners"].add(r.user_id)
        counter = {"video_rewind": "rewinds", "video_replay": "replays", "quit_early": "early_quits"}.get(r.kind)
        if counter:
            s[counter] += 1
    for s in segments.values():
        s["learners"] = len(s["learners"])
        s["score"] = round(s["score"], 2)
    struggling = defaultdict(int)
    for (concept, _uid), score in raw.items():
        if score >= 1.5:
            struggling[concept] += 1
    return {"course_id": course_id, "days": days,
            "segments": sorted(segments.values(), key=lambda s: (-s["score"], s["lesson_id"], s["segment"])),
            "early_quits_by_lesson": [{"lesson_id": lid, "lesson_title": lessons[lid].post_title, "early_quits": count}
                                     for lid, count in sorted(quits.items())],
            "struggling_by_concept": [{"concept": c, "learners": n} for c, n in sorted(struggling.items(), key=lambda x: (-x[1], x[0]))]}


def course_hotspots(db: Session, course_id: int, days: int = 30) -> Dict[str, Any]:
    result = course_segments(db, course_id, days)
    result["hotspots"] = [s for s in result.pop("segments") if s["score"] > 0][:10]
    return result



def weak_attempt_concepts(db: Session, attempt) -> List[str]:
    """Read persisted wrong answers; unfinished manual marks are not evidence."""
    from app.models.quiz import QuizAttemptAnswer, QuizQuestion
    from app.services.mastery_service import concepts_for
    if attempt.attempt_status not in ("attempt_ended", "pending_review"):
        return []
    rows = db.query(QuizAttemptAnswer.question_id, QuizQuestion.question_type).join(
        QuizQuestion, QuizQuestion.question_id == QuizAttemptAnswer.question_id).filter(
        QuizAttemptAnswer.quiz_attempt_id == attempt.attempt_id, QuizAttemptAnswer.is_correct.is_(False)).all()
    return sorted({c for qid, qtype in rows
                   if attempt.attempt_status == "attempt_ended" or qtype not in UNGRADABLE_TYPES
                   for c in concepts_for(db, "question", qid)})
