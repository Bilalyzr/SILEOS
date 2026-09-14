"""Campus examination APIs: schedule, marks, results, hall tickets, PDFs."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campus_operations import CampusBranding
from app.schemas.campus_exams import (
    ExamCreate,
    ExamUpdate,
    MarksPut,
    PaperCreate,
    PaperUpdate,
)
from app.services import campus_exams as service
from app.services.auth_service import AuthService
from app.services.campus_report_pdf import build_hall_ticket_pdf, build_marksheet_pdf


router = APIRouter()
Current = Depends(AuthService.get_current_active_user)


def _pdf(content: bytes, filename: str):
    return Response(
        content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{institution_id}/exams")
def exams(
    institution_id: int,
    term_id: int | None = Query(default=None, gt=0),
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.list_exams(db, institution_id, user, term_id, student_user_id)


@router.post("/{institution_id}/exams", status_code=201)
def exam_create(institution_id: int, data: ExamCreate, db: Session = Depends(get_db), user=Current):
    return service.create_exam(db, institution_id, user, data)


@router.patch("/{institution_id}/exams/{exam_id}")
def exam_update(
    institution_id: int, exam_id: int, data: ExamUpdate, db: Session = Depends(get_db), user=Current
):
    return service.update_exam(db, institution_id, user, exam_id, data)


@router.post("/{institution_id}/exams/{exam_id}/publish")
def exam_publish(institution_id: int, exam_id: int, db: Session = Depends(get_db), user=Current):
    return service.publish_exam(db, institution_id, user, exam_id)


@router.post("/{institution_id}/exams/{exam_id}/unpublish")
def exam_unpublish(institution_id: int, exam_id: int, db: Session = Depends(get_db), user=Current):
    return service.unpublish_exam(db, institution_id, user, exam_id)


@router.post("/{institution_id}/exams/{exam_id}/papers", status_code=201)
def paper_create(
    institution_id: int, exam_id: int, data: PaperCreate, db: Session = Depends(get_db), user=Current
):
    return service.create_paper(db, institution_id, user, exam_id, data)


@router.patch("/{institution_id}/exams/{exam_id}/papers/{paper_id}")
def paper_update(
    institution_id: int,
    exam_id: int,
    paper_id: int,
    data: PaperUpdate,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.update_paper(db, institution_id, user, exam_id, paper_id, data)


@router.delete("/{institution_id}/exams/{exam_id}/papers/{paper_id}", status_code=204)
def paper_delete(
    institution_id: int, exam_id: int, paper_id: int, db: Session = Depends(get_db), user=Current
):
    service.delete_paper(db, institution_id, user, exam_id, paper_id)
    return Response(status_code=204)


@router.get("/{institution_id}/exams/{exam_id}/papers/{paper_id}/marks")
def marks(
    institution_id: int, exam_id: int, paper_id: int, db: Session = Depends(get_db), user=Current
):
    return service.roster(db, institution_id, user, exam_id, paper_id)


@router.put("/{institution_id}/exams/{exam_id}/papers/{paper_id}/marks")
def marks_put(
    institution_id: int,
    exam_id: int,
    paper_id: int,
    data: MarksPut,
    db: Session = Depends(get_db),
    user=Current,
):
    return service.put_marks(db, institution_id, user, exam_id, paper_id, data.entries)


@router.get("/{institution_id}/exams/{exam_id}/hall-tickets")
def hall_tickets(
    institution_id: int,
    exam_id: int,
    batch_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.ensure_hall_tickets(db, institution_id, user, exam_id, batch_id)


@router.get("/{institution_id}/exams/{exam_id}/hall-tickets/me/pdf")
def my_hall_ticket_pdf(
    institution_id: int,
    exam_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    ticket = service.hall_ticket(db, institution_id, user, exam_id, None, student_user_id)
    branding = db.get(CampusBranding, institution_id)
    return _pdf(build_hall_ticket_pdf(ticket, branding), f"hall-ticket-{ticket['roll_number']}.pdf")


@router.get("/{institution_id}/exams/{exam_id}/hall-tickets/{member_id:int}/pdf")
def hall_ticket_pdf(
    institution_id: int,
    exam_id: int,
    member_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    ticket = service.hall_ticket(db, institution_id, user, exam_id, member_id, student_user_id)
    branding = db.get(CampusBranding, institution_id)
    return _pdf(build_hall_ticket_pdf(ticket, branding), f"hall-ticket-{ticket['roll_number']}.pdf")


@router.get("/{institution_id}/exams/{exam_id}/results")
def results(
    institution_id: int,
    exam_id: int,
    batch_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.results(db, institution_id, user, exam_id, batch_id)


@router.get("/{institution_id}/exams/{exam_id}/results/me")
def my_results(
    institution_id: int,
    exam_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    return service.my_results(db, institution_id, user, exam_id, student_user_id)


@router.get("/{institution_id}/exams/{exam_id}/results/{member_id:int}/marksheet.pdf")
def marksheet_pdf(
    institution_id: int,
    exam_id: int,
    member_id: int,
    student_user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    user=Current,
):
    sheet = service.marksheet(db, institution_id, user, exam_id, member_id, student_user_id)
    branding = db.get(CampusBranding, institution_id)
    return _pdf(build_marksheet_pdf(sheet, branding), f"marksheet-{sheet['roll_number']}.pdf")
