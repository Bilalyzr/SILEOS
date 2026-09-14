"""Recording-to-lesson jobs: atomic claims, bounded retries, private drafts and source excerpts."""
from datetime import datetime, timedelta, timezone
import html
from pathlib import Path
import re
from sqlalchemy import func
from app.models.recording_lesson import RecordingLesson
from app.models.live_class import LiveClass
from app.models.live_class_report import ClassReport
from app.models.course import Lesson
from app.models.mastery import ConceptLink, CourseOutcome
from app.services import transcription_provider as provider
from app.services.live_recording_service import validate_recording_path
from app.services.mastery_service import clean_concepts


def utcnow():
    return datetime.now(timezone.utc)


def source_for(lc, saved=""):
    if lc.deleted_at or lc.recording_deleted_at:
        raise ValueError("This recording has been deleted.")
    if saved:
        path = validate_recording_path(saved, lc)
        if path.is_file():
            return path
    from app.core.config import get_settings
    root = Path(get_settings().JITSI_RECORDINGS_DIR)
    # Discovery is restricted to this class's exact opaque room directory.
    folder = validate_recording_path(str(root.resolve() / lc.room_name / "candidate.mp4"), lc).parent
    candidates = sorted(folder.glob("*.mp4")) if folder.is_dir() else []
    candidates = [validate_recording_path(str(p), lc) for p in candidates]
    if len(candidates) != 1:
        raise ValueError("A single local recording is required. Let the recording finalizer register its source file first.")
    return candidates[0]


def register(db, lc, path):
    """Called AFTER ingest commits. Idempotent; never resets reviewed or failed work."""
    path = validate_recording_path(str(path), lc)
    if not db.query(RecordingLesson.id).filter_by(class_id=lc.id).first():
        db.add(RecordingLesson(class_id=lc.id, source_path=str(path), title=lc.title))
        db.commit()


def build_chapters(segments):
    chapters = []
    for segment in segments:
        if not chapters or segment["start"] - chapters[-1]["start"] >= 180:
            chapters.append({"start": segment["start"], "title": segment["text"][:100]})
    return chapters


def apply_transcript(db, row, result):
    from math import isfinite
    segments = result.get("segments", [])
    if not segments or len(segments) > 20000:
        raise ValueError("No speech was detected, or the transcript is too large. Check the recording and language.")
    cleaned, previous = [], -1
    for s in segments:
        start, end = float(s["start"]), float(s["end"])
        text = str(s["text"]).strip()
        if not isfinite(start) or not isfinite(end) or start < previous or end < start or start < 0 or end > 86400 or len(text) > 5000:
            raise ValueError("The transcription returned invalid timestamps or text.")
        previous = start
        if text:
            cleaned.append({"start": start, "end": end, "text": text})
    if not cleaned or sum(len(s["text"]) for s in cleaned) > 400000:
        raise ValueError("No usable speech was found, or the transcript exceeds the supported size.")
    row.segments = cleaned
    row.language = result.get("language", row.language)[:12]
    row.chapters = build_chapters(cleaned)
    row.notes = "\n\n".join(s["text"] for s in cleaned[:12])[:20000]
    lc = db.get(LiveClass, row.class_id)
    outcome = db.query(CourseOutcome).filter_by(course_id=lc.course_id).first()
    text = " ".join(s["text"] for s in cleaned).lower()
    known = list(outcome.target_concepts or []) if outcome else []
    known += [c for (c,) in db.query(ConceptLink.concept).filter_by(course_id=lc.course_id).distinct()]
    row.concepts = clean_concepts(c for c in known if c.lower() in text)
    row.status, row.error = "draft", None


def run_one(factory):
    """Separate worker process: CAS claim prevents two workers processing one job.
    Crashed jobs become failed after the bounded subprocess lifetime; retry is explicit.
    """
    with factory() as db:
        db.query(RecordingLesson).filter(RecordingLesson.status == "processing", RecordingLesson.started_at < utcnow() - timedelta(seconds=provider.TIMEOUT + 120)).update(
            {"status": "failed", "error": "Worker interrupted. Retry transcription.", "version": RecordingLesson.version + 1}, synchronize_session=False)
        db.commit()
        row = db.query(RecordingLesson).join(ClassReport, ClassReport.class_id == RecordingLesson.class_id).filter(RecordingLesson.status == "queued").order_by(RecordingLesson.id).first()
        if not row or not provider.configuration()["configured"]:
            return False
        ident, version = row.id, row.version
        claimed = db.query(RecordingLesson).filter_by(id=ident, status="queued", version=version).update(
            {"status": "processing", "started_at": utcnow(), "attempts": RecordingLesson.attempts + 1, "version": version + 1}, synchronize_session=False)
        db.commit()
        if not claimed:
            return False
        db.expire_all()
        row = db.get(RecordingLesson, ident)
        try:
            path = source_for(db.get(LiveClass, row.class_id), row.source_path)
            language = row.language
            # No database transaction stays open during the expensive subprocess.
            db.rollback()
            result = provider.transcribe(path, language)
            row = db.query(RecordingLesson).filter_by(id=ident, version=version + 1, status="processing").with_for_update().first()
            if not row:
                return True
            source_for(db.get(LiveClass, row.class_id), row.source_path)
            apply_transcript(db, row, result)
            row.version += 1
            db.commit()
        except Exception as exc:
            db.rollback()
            message = str(exc) if isinstance(exc, ValueError) else "Processing failed. Check the local recording and retry."
            db.query(RecordingLesson).filter_by(id=ident, version=version + 1, status="processing").update(
                {"status": "failed", "error": message[:500], "version": version + 2}, synchronize_session=False)
            db.commit()
        return True


def create_lesson(db, row, lc, user):
    if row.lesson_id:
        return db.get(Lesson, row.lesson_id)
    order = db.query(func.max(Lesson.menu_order)).filter_by(post_parent=lc.course_id).scalar() or 0
    paragraphs = "".join("<p>" + html.escape(p) + "</p>" for p in row.notes.split("\n") if p.strip())
    chapters = "".join(f'<li><a href="/recordings/{lc.id}?start={c["start"]}">{html.escape(c["title"])}</a></li>' for c in row.chapters)
    report = db.query(ClassReport).filter_by(class_id=lc.id).one()
    lesson = Lesson(post_author=user.id, post_parent=lc.course_id, post_title=row.title,
                    post_content=paragraphs + '<h2>Recording chapters</h2><ul>' + chapters + '</ul>',
                    post_excerpt=f"Source: class_report:{report.id}. Reviewed recording notes.",
                    post_status="draft", menu_order=order + 1, lesson_video_duration=str(round(row.segments[-1]["end"])))
    db.add(lesson); db.flush()
    for concept in row.concepts:
        db.add(ConceptLink(kind="lesson", ref_id=str(lesson.id), course_id=lc.course_id, concept=concept, created_by=user.id))
    row.lesson_id, row.reviewed_by, row.status = lesson.id, user.id, "lesson_created"
    return lesson


def question_suggestions(row):
    out = []
    for concept in row.concepts:
        pattern = re.compile(r"(?<!\w)" + re.escape(concept) + r"(?!\w)", re.IGNORECASE)
        segment = next((s for s in row.segments if pattern.search(s["text"]) and len(s["text"]) < 2000), None)
        if segment:
            out.append({"concept": concept, "title": "Complete the recording excerpt: " + pattern.sub("_____", segment["text"]),
                        "type": "short_answer", "options": [], "answer": concept,
                        "explanation": f'Recording at {segment["start"]:.0f}s: {segment["text"]}', "difficulty": "easy"})
    return out


def serialize(db, row, lc):
    lesson = db.get(Lesson, row.lesson_id) if row.lesson_id else None
    return {"id": row.id, "class_id": row.class_id, "course_id": lc.course_id, "status": row.status,
            "version": row.version, "language": row.language, "attempts": row.attempts, "error": row.error,
            "title": row.title, "notes": row.notes, "segments": row.segments, "chapters": row.chapters,
            "concepts": row.concepts, "question_ids": row.question_ids, "suggestions": question_suggestions(row),
            "lesson_id": row.lesson_id, "lesson_status": lesson.post_status if lesson else None,
            "updated_at": row.updated_at}
