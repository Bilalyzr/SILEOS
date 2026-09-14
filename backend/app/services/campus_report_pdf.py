"""Branded, in-memory campus report cards with no public file exposure."""

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ORANGE = colors.HexColor("#F97316")
PALE_ORANGE = colors.HexColor("#FFF1E7")
INK = colors.HexColor("#512B18")
MUTED = colors.HexColor("#8A5B42")


def build_report_card_pdf(report, branding=None):
    """Return one polished PDF as bytes; callers keep authorization at the route."""
    stream = BytesIO()
    doc = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=31 * mm,
        bottomMargin=18 * mm,
        title=f"{report['student_name']} - {report['term_name']} report card",
        author=report["institution_name"],
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CampusTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=INK,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    lead = ParagraphStyle(
        "CampusLead",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
    body = ParagraphStyle(
        "CampusBody", parent=styles["BodyText"], fontSize=9, leading=13, textColor=INK
    )

    banner_title = branding.title if branding else report["institution_name"]
    banner_subtitle = branding.subtitle if branding else "Learning progress report"
    story = [
        Paragraph(escape(banner_title), title),
        Paragraph(escape(banner_subtitle), lead),
        Spacer(1, 8 * mm),
        Table(
            [
                ["Learner", report["student_name"]],
                ["Academic term", report["term_name"]],
                ["Report status", report["status"].title()],
            ],
            colWidths=[42 * mm, 120 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), PALE_ORANGE),
                    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FFD0AE")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        ),
        Spacer(1, 7 * mm),
    ]
    rows = [["Assessment", "Score", "Grade", "Teacher feedback"]]
    for row in report["rows"]:
        score = (
            "Pending"
            if row["score"] is None
            else f"{row['score']:g} / {row['max_score']:g}"
        )
        rows.append(
            [
                Paragraph(escape(row["subject"]), body),
                score,
                row["grade"],
                Paragraph(escape(row["comment"] or "-"), body),
            ]
        )
    if len(rows) == 1:
        rows.append(["No graded assessments yet", "-", "Pending", "-"])
    scores = Table(
        rows,
        colWidths=[49 * mm, 28 * mm, 25 * mm, 60 * mm],
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F2C3A2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_ORANGE]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )
    story.extend([scores, Spacer(1, 7 * mm)])
    summary = [
        [
            "Overall",
            f"{report['overall_percent']}%"
            if report["overall_percent"] is not None
            else "Pending",
        ],
        ["Grade", report["overall_grade"]],
        [
            "Attendance",
            f"{report['attendance_percent']}%"
            if report["attendance_percent"] is not None
            else "Not recorded",
        ],
    ]
    story.append(
        Table(
            summary,
            colWidths=[42 * mm, 50 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), PALE_ORANGE),
                    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FFD0AE")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        )
    )
    story.extend(
        [
            Spacer(1, 7 * mm),
            Paragraph("Teacher comment", styles["Heading3"]),
            Paragraph(
                escape(report["overall_comment"] or "No comment added yet."), body
            ),
        ]
    )

    def decorate(canvas, document):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(PALE_ORANGE)
        canvas.rect(0, height - 24 * mm, width, 24 * mm, fill=1, stroke=0)
        canvas.setFillColor(ORANGE)
        canvas.rect(0, height - 5 * mm, width, 5 * mm, fill=1, stroke=0)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            18 * mm, 10 * mm, "Generated securely by SashaInfinity Campus"
        )
        canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return stream.getvalue()


def _base_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "CampusTitle2",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=27,
        textColor=INK,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    lead = ParagraphStyle(
        "CampusLead2",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
    body = ParagraphStyle(
        "CampusBody2", parent=styles["BodyText"], fontSize=9, leading=13, textColor=INK
    )
    return styles, title, lead, body


def _key_value_table(rows):
    return Table(
        rows,
        colWidths=[42 * mm, 120 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PALE_ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FFD0AE")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )


def _grid(rows, widths):
    return Table(
        rows,
        colWidths=widths,
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F2C3A2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_ORANGE]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )


def _decorate(canvas, document):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(PALE_ORANGE)
    canvas.rect(0, height - 24 * mm, width, 24 * mm, fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.rect(0, height - 5 * mm, width, 5 * mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 10 * mm, "Generated securely by SashaInfinity Campus")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _document(stream, title, author):
    return SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=31 * mm,
        bottomMargin=18 * mm,
        title=title,
        author=author,
    )


def _local(value, tz_name):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        return value.astimezone(ZoneInfo(tz_name))
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        return value


def build_hall_ticket_pdf(ticket, branding=None):
    """Hall ticket: learner identity, roll number, timetable of papers, verification token."""
    stream = BytesIO()
    doc = _document(
        stream,
        f"{ticket['student_name']} - {ticket['exam_name']} hall ticket",
        ticket["institution_name"],
    )
    styles, title, lead, body = _base_styles()
    banner_title = branding.title if branding else ticket["institution_name"]
    story = [
        Paragraph(escape(banner_title), title),
        Paragraph(escape(f"Hall ticket - {ticket['exam_name']}"), lead),
        Spacer(1, 8 * mm),
        _key_value_table(
            [
                ["Candidate", ticket["student_name"]],
                ["Roll number", ticket["roll_number"]],
                ["Batch", ticket["batch_name"] or "-"],
                ["Academic term", ticket["term_name"] or "-"],
                ["Examination", f"{ticket['exam_name']} ({ticket['exam_kind']})"],
            ]
        ),
        Spacer(1, 7 * mm),
    ]
    rows = [["Subject", "Date", "Time", "Room", "Max marks"]]
    for paper in ticket["papers"]:
        start = _local(paper["starts_at"], ticket["timezone"])
        end = _local(paper["ends_at"], ticket["timezone"])
        rows.append(
            [
                Paragraph(escape(paper["subject"]), body),
                start.strftime("%d %b %Y"),
                f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}",
                Paragraph(escape(paper["room"] or "-"), body),
                f"{paper['max_marks']:g}",
            ]
        )
    if len(rows) == 1:
        rows.append(["No papers scheduled yet", "-", "-", "-", "-"])
    story.append(_grid(rows, [50 * mm, 28 * mm, 34 * mm, 34 * mm, 22 * mm]))
    story.extend(
        [
            Spacer(1, 7 * mm),
            Paragraph("Instructions", styles["Heading3"]),
            Paragraph(
                "Carry this hall ticket and a photo identity card to every paper. "
                "Arrive 15 minutes before the start time. Electronic devices are not permitted.",
                body,
            ),
            Spacer(1, 4 * mm),
            Paragraph(escape(f"Verification code: {ticket['token']}"), body),
        ]
    )
    doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
    return stream.getvalue()


def build_marksheet_pdf(sheet, branding=None):
    """Consolidated mark sheet for one learner and one examination."""
    stream = BytesIO()
    doc = _document(
        stream,
        f"{sheet['student_name']} - {sheet['exam_name']} mark sheet",
        sheet["institution_name"],
    )
    styles, title, lead, body = _base_styles()
    banner_title = branding.title if branding else sheet["institution_name"]
    status = "Published" if sheet["status"] == "published" else "Provisional"
    story = [
        Paragraph(escape(banner_title), title),
        Paragraph(escape(f"Mark sheet - {sheet['exam_name']}"), lead),
        Spacer(1, 8 * mm),
        _key_value_table(
            [
                ["Learner", sheet["student_name"]],
                ["Roll number", sheet["roll_number"]],
                ["Batch", sheet["batch_name"] or "-"],
                ["Academic term", sheet["term_name"] or "-"],
                ["Result status", status],
            ]
        ),
        Spacer(1, 7 * mm),
    ]
    rows = [["Subject", "Marks", "Max", "Pass", "Result", "Remarks"]]
    for paper in sheet["papers"]:
        mark = sheet["marks"].get(paper["id"]) or {}
        if mark.get("absent"):
            shown, verdict = "Absent", "Absent"
        elif mark.get("marks") is None:
            shown, verdict = "Pending", "-"
        else:
            shown = f"{mark['marks']:g}"
            verdict = "Pass" if mark["marks"] >= paper["pass_marks"] else "Fail"
        rows.append(
            [
                Paragraph(escape(paper["subject"]), body),
                shown,
                f"{paper['max_marks']:g}",
                f"{paper['pass_marks']:g}",
                verdict,
                Paragraph(escape(mark.get("remarks") or "-"), body),
            ]
        )
    if len(rows) == 1:
        rows.append(["No papers", "-", "-", "-", "-", "-"])
    story.append(_grid(rows, [44 * mm, 20 * mm, 18 * mm, 18 * mm, 20 * mm, 48 * mm]))
    summary = [
        ["Total", f"{sheet['total']:g} / {sheet['max_total']:g}"],
        ["Percentage", f"{sheet['percent']}%" if sheet["percent"] is not None else "Pending"],
        ["Overall", "Pass" if sheet["passed"] else "Fail"],
        ["Rank in batch", f"{sheet['rank']} of {sheet['students']}"],
    ]
    story.extend([Spacer(1, 7 * mm), _key_value_table(summary)])
    doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
    return stream.getvalue()


def _fee_header(document, branding, lead_text):
    styles, title, lead, body = _base_styles()
    banner_title = branding.title if branding else document["institution_name"]
    story = [
        Paragraph(escape(banner_title), title),
        Paragraph(escape(lead_text), lead),
        Spacer(1, 8 * mm),
    ]
    return styles, body, story


def _money(amount, currency):
    return f"{currency} {amount:,.2f}"


def build_fee_receipt_pdf(receipt, branding=None):
    """Fee receipt: student, plan, allocations, method, receiver and the
    verification stamp. Registered details stay blank until the institution
    record carries an address or tax number."""
    stream = BytesIO()
    doc = _document(
        stream,
        f"{receipt['student']['name']} - fee receipt {receipt['receipt_number']}",
        receipt["institution_name"],
    )
    styles, body, story = _fee_header(receipt, branding, f"Fee receipt {receipt['receipt_number']}")
    paid_at = _local(receipt["paid_at"], receipt["timezone"])
    verification = receipt.get("verification") or {"status": "not_required"}
    if verification["status"] == "verified":
        verified_at = _local(verification["verified_at"], receipt["timezone"]) if verification.get("verified_at") else None
        stamp = f"Verified by {(verification.get('verified_by') or {}).get('name', 'staff')}" + (
            f" on {verified_at.strftime('%d %b %Y %H:%M')}" if verified_at else ""
        )
    elif verification["status"] == "pending":
        stamp = "Awaiting verification by a second staff member"
    else:
        stamp = "Not required for this method"
    currency = receipt["currency"]
    story.append(
        _key_value_table(
            [
                ["Student", receipt["student"]["name"]],
                ["Fee plan", f"{receipt['plan']['name']} ({receipt['plan']['academic_year']})"],
                ["Academic year", receipt.get("academic_year") or "-"],
                ["Paid at", paid_at.strftime("%d %b %Y %H:%M")],
                ["Method", receipt["method"].replace("_", " ").title()],
                ["Reference", receipt["reference"] or "-"],
                ["Received by", (receipt.get("received_by") or {}).get("name", "-")],
                ["Verification", stamp],
            ]
        )
    )
    story.append(Spacer(1, 7 * mm))
    rows = [["Installment", "Amount"]]
    for line in receipt.get("allocations") or []:
        rows.append([Paragraph(escape(line["installment"]), body), _money(line["amount"], currency)])
    if len(rows) == 1:
        rows.append(["Fee account", _money(receipt["amount"], currency)])
    rows.append(["Total received", _money(receipt["amount"], currency)])
    story.append(_grid(rows, [110 * mm, 52 * mm]))
    story.extend(
        [
            Spacer(1, 6 * mm),
            _key_value_table([["Balance after payment", _money(receipt["balance_after"], currency)]]),
            Spacer(1, 6 * mm),
            Paragraph("Registered details: -", body),
            Paragraph("This is a computer-generated receipt and does not need a signature.", body),
        ]
    )
    doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
    return stream.getvalue()


def build_fee_invoice_pdf(invoice, branding=None):
    """Demand invoice: what was owed on the listed installments when issued."""
    stream = BytesIO()
    doc = _document(
        stream,
        f"{invoice['student']['name']} - fee invoice {invoice['invoice_number']}",
        invoice["institution_name"],
    )
    styles, body, story = _fee_header(invoice, branding, f"Fee invoice {invoice['invoice_number']}")
    issued_at = _local(invoice["issued_at"], invoice["timezone"])
    currency = invoice["currency"]
    story.append(
        _key_value_table(
            [
                ["Student", invoice["student"]["name"]],
                ["Fee plan", f"{invoice['plan']['name']} ({invoice['plan']['academic_year']})"],
                ["Issued on", issued_at.strftime("%d %b %Y")],
                ["Due on", invoice["due_on"].strftime("%d %b %Y")],
                ["Status", "Settled" if invoice["status"] == "settled" else "Open"],
            ]
        )
    )
    story.append(Spacer(1, 7 * mm))
    rows = [["Installment", "Due", "Amount due", "Credited", "Balance"]]
    for line in invoice["lines"]:
        rows.append(
            [
                Paragraph(escape(line["name"]), body),
                line["due_on"],
                _money(line["amount_due"], currency),
                _money(line["credited"], currency),
                _money(line["balance"], currency),
            ]
        )
    rows.append(["Total payable", "", "", "", _money(invoice["amount"], currency)])
    story.append(_grid(rows, [52 * mm, 24 * mm, 30 * mm, 28 * mm, 30 * mm]))
    story.extend(
        [
            Spacer(1, 6 * mm),
            Paragraph("Pay at the campus office (cash, cheque, UPI, card) or online where enabled. "
                      "Bring or quote this invoice number.", body),
            Paragraph("Registered details: -", body),
            Paragraph("This is a computer-generated invoice and does not need a signature.", body),
        ]
    )
    doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)
    return stream.getvalue()
