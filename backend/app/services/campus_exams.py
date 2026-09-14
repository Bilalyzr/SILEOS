"""Campus examinations: scheduling, marks, results, hall tickets.

Authorization lives here so every route enforces the same rules:
staff schedule and grade, managers publish, learners and approved guardians
read only what has been published.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func

from app.models.campus_exams import (
    CampusExam,
    CampusExamMark,
    CampusExamPaper,
    CampusHallTicket,
)
from app.models.campus_operations import CampusTerm, ParentLinkRequest
from app.models.campus_pilot import CampusEvent
from app.models.institution import InstitutionBatchMember, InstitutionMember
from app.models.user import User
from app.services import campus_pilot as pilot_svc
from app.services import institution_service as institution_svc


VISIBLE_TO_LEARNERS = ("scheduled", "published")


# ---------------------------------------------------------------- lookups


def _exam(db, institution, exam_id, *, lock=False):
    query = db.query(CampusExam).filter_by(id=exam_id, institution_id=institution.id)
    row = query.with_for_update().first() if lock else query.first()
    if not row:
        raise HTTPException(404, "Exam not found.")
    return row


def _paper(db, exam, paper_id):
    row = db.query(CampusExamPaper).filter_by(id=paper_id, exam_id=exam.id).first()
    if not row:
        raise HTTPException(404, "Exam paper not found.")
    return row


def _term(db, institution, term_id):
    row = db.query(CampusTerm).filter_by(id=term_id, institution_id=institution.id).first()
    if not row:
        raise HTTPException(404, "Academic term not found.")
    return row


def _batch_student_ids(db, batch_id):
    return [
        member_id
        for member_id, in db.query(InstitutionBatchMember.member_id)
        .join(InstitutionMember, InstitutionMember.id == InstitutionBatchMember.member_id)
        .filter(
            InstitutionBatchMember.batch_id == batch_id,
            InstitutionMember.role == "student",
            InstitutionMember.status == "active",
        )
    ]


def _students(db, member_ids):
    if not member_ids:
        return {}
    rows = (
        db.query(InstitutionMember, User)
        .join(User, User.id == InstitutionMember.user_id)
        .filter(InstitutionMember.id.in_(member_ids))
        .all()
    )
    return {member.id: (member, user) for member, user in rows}


def _learner_member(db, institution, user, student_user_id=None):
    """Resolve the student member a learner or approved guardian may read."""
    if user.role == "parent":
        if not student_user_id:
            raise HTTPException(422, "Choose an approved student account.")
        approved = (
            db.query(ParentLinkRequest)
            .filter_by(parent_user_id=user.id, student_user_id=student_user_id, status="approved")
            .first()
        )
        if not approved:
            raise HTTPException(404, "Approved student account not found.")
        target_user_id = student_user_id
    else:
        if student_user_id and student_user_id != user.id:
            raise HTTPException(404, "Student account not found.")
        target_user_id = user.id
    member = (
        db.query(InstitutionMember)
        .filter_by(institution_id=institution.id, user_id=target_user_id, role="student", status="active")
        .first()
    )
    if not member:
        raise HTTPException(404, "Active student account not found in this institution.")
    return member


def _actor(db, institution_id, user, roles=None, *, lock=False):
    """Scope for members. Parents are not members; they pass through separately."""
    return institution_svc.scope(db, institution_id, user, roles, lock=lock)


def _reader(db, institution_id, user):
    """Return (institution, member|None). Guardians get institution with member None."""
    if user.role == "parent":
        from app.models.institution import Institution

        institution = db.get(Institution, institution_id)
        if not institution:
            raise HTTPException(404, "Institution not found.")
        return institution, None
    return institution_svc.scope(db, institution_id, user)


# ------------------------------------------------------------- serializers


def paper_dict(db, paper):
    starts = institution_svc.utc(paper.starts_at)
    students = _batch_student_ids(db, paper.batch_id)
    entered = (
        db.query(func.count(CampusExamMark.id))
        .filter(CampusExamMark.paper_id == paper.id, CampusExamMark.member_id.in_(students))
        .scalar()
        if students
        else 0
    )
    return {
        "id": paper.id,
        "exam_id": paper.exam_id,
        "batch_id": paper.batch_id,
        "batch_name": pilot_svc.batch_name(db, paper.batch_id),
        "subject": paper.subject,
        "max_marks": paper.max_marks,
        "pass_marks": paper.pass_marks,
        "starts_at": starts.isoformat(),
        "ends_at": (starts + timedelta(minutes=paper.duration_minutes)).isoformat(),
        "duration_minutes": paper.duration_minutes,
        "room": paper.room,
        "event_id": paper.event_id,
        "marks_entered": int(entered or 0),
        "students": len(students),
    }


def exam_dict(db, exam, *, papers=None):
    rows = (
        papers
        if papers is not None
        else db.query(CampusExamPaper).filter_by(exam_id=exam.id).order_by(CampusExamPaper.starts_at, CampusExamPaper.id).all()
    )
    term = db.get(CampusTerm, exam.term_id)
    return {
        "id": exam.id,
        "term_id": exam.term_id,
        "term_name": term.name if term else None,
        "name": exam.name,
        "kind": exam.kind,
        "status": exam.status,
        "published_at": institution_svc.utc(exam.published_at).isoformat() if exam.published_at else None,
        "papers": [paper_dict(db, row) for row in rows],
    }


# ------------------------------------------------------------------ exams


def list_exams(db, institution_id, user, term_id=None, student_user_id=None):
    institution, member = _reader(db, institution_id, user)
    query = db.query(CampusExam).filter_by(institution_id=institution.id)
    if term_id:
        query = query.filter_by(term_id=term_id)
    staff = member is not None and member.role in institution_svc.STAFF
    if not staff:
        learner = member if member is not None else _learner_member(db, institution, user, student_user_id)
        batch_ids = [b for b, in db.query(InstitutionBatchMember.batch_id).filter_by(member_id=learner.id)]
        query = query.filter(CampusExam.status.in_(VISIBLE_TO_LEARNERS))
        exams = query.order_by(CampusExam.id.desc()).all()
        out = []
        for exam in exams:
            papers = (
                db.query(CampusExamPaper)
                .filter(CampusExamPaper.exam_id == exam.id, CampusExamPaper.batch_id.in_(batch_ids))
                .order_by(CampusExamPaper.starts_at)
                .all()
                if batch_ids
                else []
            )
            if papers:
                out.append(exam_dict(db, exam, papers=papers))
        return out
    return [exam_dict(db, exam) for exam in query.order_by(CampusExam.id.desc()).all()]


def create_exam(db, institution_id, user, data):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    _term(db, institution, data.term_id)
    exam = CampusExam(
        institution_id=institution.id,
        term_id=data.term_id,
        name=data.name.strip(),
        kind=data.kind,
        status="draft",
        created_by=user.id,
    )
    db.add(exam)
    institution_svc.audit(db, institution.id, user, "exam.created", data.name.strip())
    institution_svc.save(db)
    db.refresh(exam)
    return exam_dict(db, exam)


def update_exam(db, institution_id, user, exam_id, data):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    if data.name is not None:
        exam.name = data.name.strip()
    if data.kind is not None:
        exam.kind = data.kind
    institution_svc.save(db)
    return exam_dict(db, exam)


def publish_exam(db, institution_id, user, exam_id):
    institution, _ = _actor(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    if not db.query(CampusExamPaper).filter_by(exam_id=exam.id).count():
        raise HTTPException(422, "Add at least one paper before publishing results.")
    exam.status = "published"
    exam.published_at = datetime.now(timezone.utc)
    institution_svc.audit(db, institution.id, user, "exam.published", exam.name)
    institution_svc.save(db)
    return exam_dict(db, exam)


def unpublish_exam(db, institution_id, user, exam_id):
    institution, _ = _actor(db, institution_id, user, institution_svc.MANAGERS, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    exam.status = "scheduled"
    exam.published_at = None
    institution_svc.audit(db, institution.id, user, "exam.unpublished", exam.name)
    institution_svc.save(db)
    return exam_dict(db, exam)


# ----------------------------------------------------------------- papers


def _schedule_event(db, institution, exam, paper, *, exclude_event_id=None):
    starts = institution_svc.utc(paper.starts_at)
    ends = starts + timedelta(minutes=paper.duration_minutes)
    conflicts = [
        row
        for row in pilot_svc._conflicts(db, institution.id, starts, ends, paper.batch_id, None, paper.room)
        if row.id != exclude_event_id
    ]
    if conflicts:
        labels = ", ".join(sorted({row.title for row in conflicts})[:3])
        raise HTTPException(409, f"Timetable conflict with: {labels}.")
    title = f"{exam.name} · {paper.subject}"
    if exclude_event_id:
        event = db.get(CampusEvent, exclude_event_id)
    else:
        event = None
    if event is None:
        event = CampusEvent(
            institution_id=institution.id,
            created_by=paper.created_by,
            series=f"exam:{secrets.token_hex(8)}",
        )
        db.add(event)
    event.batch_id = paper.batch_id
    event.teacher_id = None
    event.title = title
    event.kind = "exam"
    event.room = paper.room.strip()
    event.description = f"{exam.kind.title()} examination"
    event.starts_at = starts
    event.ends_at = ends
    db.flush()
    paper.event_id = event.id


def _refresh_status(db, exam):
    if exam.status == "published":
        return
    has_papers = db.query(CampusExamPaper).filter_by(exam_id=exam.id).count() > 0
    exam.status = "scheduled" if has_papers else "draft"


def create_paper(db, institution_id, user, exam_id, data):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    if exam.status == "published":
        raise HTTPException(409, "Unpublish the exam before changing its papers.")
    institution_svc.batch_scope(db, institution.id, data.batch_id)
    paper = CampusExamPaper(
        exam_id=exam.id,
        batch_id=data.batch_id,
        subject=data.subject.strip(),
        max_marks=data.max_marks,
        pass_marks=data.pass_marks,
        starts_at=data.starts_at.astimezone(timezone.utc),
        duration_minutes=data.duration_minutes,
        room=data.room.strip(),
        created_by=user.id,
    )
    if (
        db.query(CampusExamPaper)
        .filter_by(exam_id=exam.id, batch_id=paper.batch_id, subject=paper.subject)
        .first()
    ):
        raise HTTPException(409, "This batch already has a paper for that subject.")
    db.add(paper)
    _schedule_event(db, institution, exam, paper)
    _refresh_status(db, exam)
    institution_svc.save(db)
    db.refresh(paper)
    return paper_dict(db, paper)


def update_paper(db, institution_id, user, exam_id, paper_id, data):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    if exam.status == "published":
        raise HTTPException(409, "Unpublish the exam before changing its papers.")
    paper = _paper(db, exam, paper_id)
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "starts_at":
            value = value.astimezone(timezone.utc)
        if isinstance(value, str):
            value = value.strip()
        setattr(paper, key, value)
    if paper.pass_marks > paper.max_marks:
        raise HTTPException(422, "Pass marks cannot exceed maximum marks.")
    if paper.max_marks < (
        db.query(func.max(CampusExamMark.marks)).filter_by(paper_id=paper.id).scalar() or 0
    ):
        raise HTTPException(422, "Maximum marks cannot be lower than marks already entered.")
    _schedule_event(db, institution, exam, paper, exclude_event_id=paper.event_id)
    institution_svc.save(db)
    return paper_dict(db, paper)


def delete_paper(db, institution_id, user, exam_id, paper_id):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    if exam.status == "published":
        raise HTTPException(409, "Unpublish the exam before changing its papers.")
    paper = _paper(db, exam, paper_id)
    if db.query(CampusExamMark).filter_by(paper_id=paper.id).count():
        raise HTTPException(409, "Marks have been entered for this paper. Clear them first.")
    event_id = paper.event_id
    db.delete(paper)
    db.flush()
    if event_id:
        event = db.get(CampusEvent, event_id)
        if event:
            db.delete(event)
    _refresh_status(db, exam)
    institution_svc.save(db)


# ------------------------------------------------------------------ marks


def roster(db, institution_id, user, exam_id, paper_id):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF)
    exam = _exam(db, institution, exam_id)
    paper = _paper(db, exam, paper_id)
    ids = _batch_student_ids(db, paper.batch_id)
    people = _students(db, ids)
    marks = {
        row.member_id: row
        for row in db.query(CampusExamMark).filter(CampusExamMark.paper_id == paper.id, CampusExamMark.member_id.in_(ids))
    } if ids else {}
    tickets = {
        row.member_id: row.roll_number
        for row in db.query(CampusHallTicket).filter_by(exam_id=exam.id)
    }
    out = []
    for member_id in ids:
        member, account = people[member_id]
        mark = marks.get(member_id)
        out.append(
            {
                "member_id": member_id,
                "name": account.display_name,
                "roll_number": tickets.get(member_id, _roll_number(paper.batch_id, member_id)),
                "marks": mark.marks if mark else None,
                "absent": bool(mark.absent) if mark else False,
                "remarks": mark.remarks if mark else "",
            }
        )
    out.sort(key=lambda row: row["roll_number"])
    return out


def put_marks(db, institution_id, user, exam_id, paper_id, entries):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    exam = _exam(db, institution, exam_id, lock=True)
    if exam.status == "published":
        raise HTTPException(409, "Results are published. Unpublish the exam to change marks.")
    paper = _paper(db, exam, paper_id)
    allowed = set(_batch_student_ids(db, paper.batch_id))
    seen = set()
    for entry in entries:
        if entry.member_id in seen:
            raise HTTPException(422, "Each student may appear once per submission.")
        seen.add(entry.member_id)
        if entry.member_id not in allowed:
            raise HTTPException(422, "Every student must belong to the paper's batch.")
        if not entry.absent:
            if entry.marks is None:
                raise HTTPException(422, "Enter marks or mark the student absent.")
            if entry.marks < 0 or entry.marks > paper.max_marks:
                raise HTTPException(422, f"Marks must be between 0 and {paper.max_marks:g}.")
    existing = {
        row.member_id: row
        for row in db.query(CampusExamMark).filter(CampusExamMark.paper_id == paper.id, CampusExamMark.member_id.in_(seen))
    }
    for entry in entries:
        row = existing.get(entry.member_id)
        if row is None:
            row = CampusExamMark(paper_id=paper.id, member_id=entry.member_id)
            db.add(row)
        row.absent = entry.absent
        row.marks = None if entry.absent else float(entry.marks)
        row.remarks = entry.remarks.strip()
        row.graded_by = user.id
    institution_svc.audit(db, institution.id, user, "exam.marks_saved", f"{exam.name} · {paper.subject}: {len(entries)} row(s)")
    institution_svc.save(db)
    return roster(db, institution_id, user, exam_id, paper_id)


# ---------------------------------------------------------------- results


def _compute_results(db, exam, batch_id, member_ids):
    papers = (
        db.query(CampusExamPaper)
        .filter_by(exam_id=exam.id, batch_id=batch_id)
        .order_by(CampusExamPaper.starts_at, CampusExamPaper.id)
        .all()
    )
    paper_ids = [p.id for p in papers]
    marks = {}
    if paper_ids and member_ids:
        for row in db.query(CampusExamMark).filter(
            CampusExamMark.paper_id.in_(paper_ids), CampusExamMark.member_id.in_(member_ids)
        ):
            marks[(row.paper_id, row.member_id)] = row
    people = _students(db, member_ids)
    tickets = {row.member_id: row.roll_number for row in db.query(CampusHallTicket).filter_by(exam_id=exam.id)}
    max_total = sum(p.max_marks for p in papers)
    rows = []
    for member_id in member_ids:
        member, account = people[member_id]
        per_paper = {}
        total = 0.0
        passed = bool(papers)
        for paper in papers:
            mark = marks.get((paper.id, member_id))
            if mark is None:
                per_paper[paper.id] = {"marks": None, "absent": False, "remarks": ""}
                passed = False
                continue
            per_paper[paper.id] = {"marks": mark.marks, "absent": bool(mark.absent), "remarks": mark.remarks}
            if mark.absent or mark.marks is None:
                passed = False
            else:
                total += mark.marks
                if mark.marks < paper.pass_marks:
                    passed = False
        rows.append(
            {
                "member_id": member_id,
                "name": account.display_name,
                "roll_number": tickets.get(member_id, _roll_number(batch_id, member_id)),
                "marks": per_paper,
                "total": round(total, 2),
                "max_total": max_total,
                "percent": round(total * 100 / max_total, 1) if max_total else None,
                "passed": passed,
                "rank": None,
            }
        )
    rows.sort(key=lambda row: (-row["total"], row["roll_number"]))
    rank = 0
    previous = None
    for index, row in enumerate(rows, start=1):
        if row["total"] != previous:
            rank = index
            previous = row["total"]
        row["rank"] = rank
    return {
        "exam": {"id": exam.id, "name": exam.name, "status": exam.status},
        "batch_id": batch_id,
        "batch_name": pilot_svc.batch_name(db, batch_id),
        "papers": [
            {"id": p.id, "subject": p.subject, "max_marks": p.max_marks, "pass_marks": p.pass_marks}
            for p in papers
        ],
        "rows": rows,
    }


def results(db, institution_id, user, exam_id, batch_id):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF)
    exam = _exam(db, institution, exam_id)
    institution_svc.batch_scope(db, institution.id, batch_id)
    return _compute_results(db, exam, batch_id, _batch_student_ids(db, batch_id))


def _learner_batch_for_exam(db, exam, member):
    batch_ids = [b for b, in db.query(InstitutionBatchMember.batch_id).filter_by(member_id=member.id)]
    paper = (
        db.query(CampusExamPaper)
        .filter(CampusExamPaper.exam_id == exam.id, CampusExamPaper.batch_id.in_(batch_ids))
        .first()
        if batch_ids
        else None
    )
    if not paper:
        raise HTTPException(404, "Exam not found.")
    return paper.batch_id


def _student_result(db, exam, member):
    batch_id = _learner_batch_for_exam(db, exam, member)
    table = _compute_results(db, exam, batch_id, _batch_student_ids(db, batch_id))
    mine = next((row for row in table["rows"] if row["member_id"] == member.id), None)
    if mine is None:
        raise HTTPException(404, "Exam not found.")
    return {
        "exam": table["exam"],
        "batch_id": batch_id,
        "batch_name": table["batch_name"],
        "papers": table["papers"],
        "students": len(table["rows"]),
        **mine,
    }


def my_results(db, institution_id, user, exam_id, student_user_id=None):
    institution, member = _reader(db, institution_id, user)
    if member is not None and member.role in institution_svc.STAFF:
        raise HTTPException(404, "Staff read results per batch.")
    learner = member if member is not None else _learner_member(db, institution, user, student_user_id)
    exam = _exam(db, institution, exam_id)
    if exam.status != "published":
        raise HTTPException(404, "Results are not published yet.")
    return _student_result(db, exam, learner)


def _authorized_learner(db, institution, user, member, member_id, student_user_id):
    """Return the student member a caller may read: staff any, learner self, guardian approved.

    `member_id=None` means "me": the caller's own student membership (or the
    approved child for a guardian).
    """
    if member is not None and member.role in institution_svc.STAFF:
        if member_id is None:
            raise HTTPException(404, "Staff read tickets per student.")
        return pilot_svc.member_scope(db, institution.id, member_id, students_only=True)
    learner = member if member is not None else _learner_member(db, institution, user, student_user_id)
    if member_id is not None and learner.id != member_id:
        raise HTTPException(404, "Campus member not found.")
    return learner


def marksheet(db, institution_id, user, exam_id, member_id, student_user_id=None):
    institution, member = _reader(db, institution_id, user)
    exam = _exam(db, institution, exam_id)
    learner = _authorized_learner(db, institution, user, member, member_id, student_user_id)
    staff = member is not None and member.role in institution_svc.STAFF
    if not staff and exam.status != "published":
        raise HTTPException(404, "Results are not published yet.")
    account = db.get(User, learner.user_id)
    term = db.get(CampusTerm, exam.term_id)
    result = _student_result(db, exam, learner)
    return {
        "institution_name": institution.name,
        "student_name": account.display_name,
        "exam_name": exam.name,
        "exam_kind": exam.kind,
        "term_name": term.name if term else "",
        "status": exam.status,
        **result,
    }


# ----------------------------------------------------------- hall tickets


def _roll_number(batch_id, member_id):
    return f"{batch_id:02d}-{member_id:04d}"


def _issue_tickets(db, exam, user, wanted):
    """Insert missing tickets for (batch_id, member_id) pairs; idempotent under races.

    Two identical requests can both observe "missing" and insert. The unique
    constraint rejects the loser; it rolls back and re-reads the winner's rows.
    """
    from sqlalchemy.exc import IntegrityError

    existing = {row.member_id: row for row in db.query(CampusHallTicket).filter_by(exam_id=exam.id)}
    for bid, member_id in wanted:
        if member_id not in existing:
            ticket = CampusHallTicket(
                exam_id=exam.id,
                member_id=member_id,
                roll_number=_roll_number(bid, member_id),
                token=secrets.token_hex(16),
                issued_by=user.id,
            )
            db.add(ticket)
            existing[member_id] = ticket
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = {row.member_id: row for row in db.query(CampusHallTicket).filter_by(exam_id=exam.id)}
        if any(member_id not in existing for _, member_id in wanted):
            raise HTTPException(409, "Hall tickets are being issued. Refresh and try again.")
    return existing


def ensure_hall_tickets(db, institution_id, user, exam_id, batch_id=None):
    institution, _ = _actor(db, institution_id, user, institution_svc.STAFF, lock=True)
    exam = _exam(db, institution, exam_id)
    batch_ids = [
        b
        for b, in db.query(CampusExamPaper.batch_id).filter_by(exam_id=exam.id).distinct()
    ]
    if batch_id is not None:
        institution_svc.batch_scope(db, institution.id, batch_id)
        batch_ids = [b for b in batch_ids if b == batch_id]
    wanted = [(bid, member_id) for bid in batch_ids for member_id in _batch_student_ids(db, bid)]
    existing = _issue_tickets(db, exam, user, wanted)
    people = _students(db, [m for _, m in wanted])
    out = []
    for bid, member_id in wanted:
        ticket = existing[member_id]
        out.append(
            {
                "id": ticket.id,
                "member_id": member_id,
                "batch_id": bid,
                "name": people[member_id][1].display_name,
                "roll_number": ticket.roll_number,
                "token": ticket.token,
                "issued_at": institution_svc.utc(ticket.issued_at).isoformat() if ticket.issued_at else None,
            }
        )
    out.sort(key=lambda row: row["roll_number"])
    return out


def hall_ticket(db, institution_id, user, exam_id, member_id, student_user_id=None):
    institution, member = _reader(db, institution_id, user)
    exam = _exam(db, institution, exam_id)
    learner = _authorized_learner(db, institution, user, member, member_id, student_user_id)
    staff = member is not None and member.role in institution_svc.STAFF
    if not staff and exam.status not in VISIBLE_TO_LEARNERS:
        raise HTTPException(404, "Exam not found.")
    batch_id = _learner_batch_for_exam(db, exam, learner)
    ticket = _issue_tickets(db, exam, user, [(batch_id, learner.id)])[learner.id]
    account = db.get(User, learner.user_id)
    term = db.get(CampusTerm, exam.term_id)
    papers = (
        db.query(CampusExamPaper)
        .filter_by(exam_id=exam.id, batch_id=batch_id)
        .order_by(CampusExamPaper.starts_at, CampusExamPaper.id)
        .all()
    )
    return {
        "institution_name": institution.name,
        "student_name": account.display_name,
        "exam_name": exam.name,
        "exam_kind": exam.kind,
        "term_name": term.name if term else "",
        "batch_name": pilot_svc.batch_name(db, batch_id),
        "roll_number": ticket.roll_number,
        "token": ticket.token,
        "papers": [
            {
                "subject": p.subject,
                "starts_at": institution_svc.utc(p.starts_at),
                "ends_at": institution_svc.utc(p.starts_at) + timedelta(minutes=p.duration_minutes),
                "room": p.room,
                "max_marks": p.max_marks,
            }
            for p in papers
        ],
        "timezone": institution.timezone,
    }


# --------------------------------------------------------- report card hook


def report_card_rows(db, institution, member, term):
    """Rows for published exams in a term, for `campus_pilot.report_card`."""
    batch_ids = [b for b, in db.query(InstitutionBatchMember.batch_id).filter_by(member_id=member.id)]
    if not batch_ids:
        return []
    papers = (
        db.query(CampusExamPaper, CampusExam)
        .join(CampusExam, CampusExam.id == CampusExamPaper.exam_id)
        .filter(
            CampusExam.institution_id == institution.id,
            CampusExam.term_id == term.id,
            CampusExam.status == "published",
            CampusExamPaper.batch_id.in_(batch_ids),
        )
        .order_by(CampusExam.id, CampusExamPaper.starts_at)
        .all()
    )
    rows = []
    for paper, exam in papers:
        mark = db.query(CampusExamMark).filter_by(paper_id=paper.id, member_id=member.id).first()
        rows.append(
            {
                "subject": f"{exam.name} · {paper.subject}",
                "max_score": paper.max_marks,
                "score": (0.0 if mark.absent else mark.marks) if mark else None,
                "absent": bool(mark.absent) if mark else False,
                "comment": mark.remarks if mark else "",
            }
        )
    return rows
