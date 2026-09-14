"""Pure data builder + CSV/PDF renderers for attendance reports."""
from dataclasses import dataclass
from datetime import date
from io import BytesIO, StringIO
from typing import Iterable, Optional
import csv

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.internship import Internship, InternshipAttendance, InternshipVoucher
from app.models.company import Company


@dataclass
class ReportRow:
    log_date: date
    student_name: str
    student_email: str
    internship_title: str
    reporting_manager: str
    status: str
    hours: float
    note: str
    marked_by_name: str


def build_rows(
    db: Session,
    *,
    voucher_ids: Iterable[int],
    from_date: date,
    to_date: date,
    student_ids: Optional[list[int]] = None,
    internship_ids: Optional[list[int]] = None,
    manager_ids: Optional[list[int]] = None,
) -> list[ReportRow]:
    vouchers = (
        db.query(InternshipVoucher)
        .filter(InternshipVoucher.id.in_(list(voucher_ids) or [-1]))
        .all()
    )
    if internship_ids:
        vouchers = [v for v in vouchers if v.internship_id in set(internship_ids)]
    if manager_ids:
        s = set(manager_ids)
        vouchers = [v for v in vouchers if v.reporting_manager_user_id in s]
    if student_ids:
        s = set(student_ids)
        vouchers = [v for v in vouchers if v.buyer_user_id in s]

    sids = [v.buyer_user_id for v in vouchers]
    iids = list({v.internship_id for v in vouchers})

    students = {u.id: u for u in db.query(User).filter(User.id.in_(sids or [-1])).all()}
    interns = {i.id: i for i in db.query(Internship).filter(Internship.id.in_(iids or [-1])).all()}
    mgrs = {u.id: u for u in db.query(User).filter(
        User.id.in_({v.reporting_manager_user_id for v in vouchers if v.reporting_manager_user_id} or [-1])
    ).all()}

    att = (
        db.query(InternshipAttendance)
        .filter(
            InternshipAttendance.user_id.in_(sids or [-1]),
            InternshipAttendance.attended_at >= from_date,
            InternshipAttendance.attended_at <= to_date,
        )
        .order_by(InternshipAttendance.attended_at.asc())
        .all()
    )
    markers = {u.id: u for u in db.query(User).filter(
        User.id.in_({a.marked_by for a in att if a.marked_by} or [-1])
    ).all()}
    voucher_by_user = {v.buyer_user_id: v for v in vouchers}

    rows: list[ReportRow] = []
    for a in att:
        v = voucher_by_user.get(a.user_id)
        s = students.get(a.user_id)
        i = interns.get(a.internship_id)
        if not (v and s and i):
            continue
        rows.append(ReportRow(
            log_date=a.attended_at,
            student_name=s.display_name,
            student_email=s.user_email,
            internship_title=i.title,
            reporting_manager=(
                mgrs[v.reporting_manager_user_id].display_name
                if v.reporting_manager_user_id and v.reporting_manager_user_id in mgrs
                else ""
            ),
            status=a.status,
            hours=float(a.hours_worked or 0),
            note=a.notes or "",
            marked_by_name=(markers[a.marked_by].display_name
                            if a.marked_by and a.marked_by in markers else ""),
        ))
    return rows


def render_csv(rows: list[ReportRow]) -> bytes:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Student", "Email", "Internship", "Manager",
                "Status", "Hours", "Note", "Marked by"])
    for r in rows:
        w.writerow([r.log_date.isoformat(), r.student_name, r.student_email,
                    r.internship_title, r.reporting_manager, r.status,
                    f"{r.hours:.2f}", r.note, r.marked_by_name])
    # Footer summary
    total_days = len({(r.student_email, r.log_date) for r in rows})
    total_hours = sum(r.hours for r in rows)
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    w.writerow([])
    w.writerow(["Total entries", total_days])
    w.writerow(["Total hours", f"{total_hours:.2f}"])
    for s, c in by_status.items():
        w.writerow([f"Status {s}", c])
    return buf.getvalue().encode("utf-8")


def render_pdf(rows: list[ReportRow], *, title: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    head = ["Date", "Student", "Email", "Internship", "Manager", "Status", "Hours", "Note"]
    body = [[
        r.log_date.isoformat(), r.student_name, r.student_email,
        r.internship_title, r.reporting_manager, r.status, f"{r.hours:.2f}", r.note,
    ] for r in rows]
    table = Table([head, *body], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()
