"""Invoice PDF rendering — reportlab platypus, simple and deterministic.

Mirrors the canvas/platypus patterns used in certificate_service.py, but
kept intentionally plain: A4, seller block top-left, buyer block top-right,
an items table, right-aligned totals, tax note, notes, and a footer. No
logos, no external network calls, nothing that can vary between renders of
the same invoice besides the timestamp implicit in reportlab's own PDF
metadata.
"""
import os
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)

INVOICES_DIR = "invoices"


def ensure_invoice_pdf(db, invoice) -> str | None:
    """Return a path to `invoice`'s PDF that actually exists on disk, or None.

    The rendered file lives on a bind-mounted host directory; if that mount is
    missing (or the volume was recreated) the row still carries a pdf_path but
    the file is gone, which would 404 both PDF endpoints forever for a legal
    document. Rendering is deterministic from the invoice's own snapshot
    fields (number/amounts/tax note + the company billing block), so a lost
    file can simply be re-rendered on demand.

    Only ISSUED/PAID invoices are re-rendered: a DRAFT has no invoice number
    and no PDF is expected, and a CANCELLED invoice must not have a fresh
    document minted for it. Callers commit — this only mutates
    invoice.pdf_path when the re-render lands somewhere new.
    """
    from app.models.company_invoice import InvoiceStatus

    path = invoice.pdf_path or ""
    if path and os.path.isfile(path):
        return path
    # A blank pdf_path is not a lost file: the invoice was issued without one
    # (renderer disabled/failed), so there is nothing to reconstruct a path
    # for and the endpoint's 404 is the honest answer.
    if not path:
        return None
    if invoice.status not in (InvoiceStatus.ISSUED, InvoiceStatus.PAID):
        return None
    new_path = render_invoice_pdf(db, invoice)
    if new_path != invoice.pdf_path:
        invoice.pdf_path = new_path
    return new_path if os.path.isfile(new_path) else None


def render_invoice_pdf(db, invoice) -> str:
    """Render `invoice` to a PDF under `<cwd>/invoices/` and return the path
    relative to the backend cwd (e.g. "invoices/INV-2627-0001.pdf").

    `invoice` must already carry its final invoice_number/subtotal/tax
    fields (i.e. this is called from issue_invoice, after those are set).
    """
    from app.models.company import Company
    from app.models.company_invoice import CompanyInvoiceItem
    from app.core.config import get_settings

    settings = get_settings()
    # .first() + name fallback: a deleted/missing company row used to raise
    # NoResultFound and fail the whole invoice render with a 500.
    company = db.query(Company).filter(Company.id == invoice.company_id).first()
    items = db.query(CompanyInvoiceItem).filter(
        CompanyInvoiceItem.invoice_id == invoice.id).all()

    os.makedirs(INVOICES_DIR, exist_ok=True)
    number = invoice.invoice_number or f"DRAFT-{invoice.id}"
    filename = f"{number}.pdf"
    file_path = os.path.join(INVOICES_DIR, filename)

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=colors.HexColor("#666666"))
    heading = ParagraphStyle("heading", parent=normal, fontSize=18, fontName="Helvetica-Bold")
    label = ParagraphStyle("label", parent=normal, fontSize=9, textColor=colors.HexColor("#888888"))

    doc = SimpleDocTemplate(
        file_path, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    story = []

    # ── Header: brand band (2026-09-05 orange theme) + title ────────
    brand = ParagraphStyle("brand", parent=normal, fontSize=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#f97316"))
    heading = ParagraphStyle("heading", parent=heading, textColor=colors.HexColor("#1f2937"))
    story.append(Paragraph(_xml_escape(settings.SELLER_LEGAL_NAME or "SashaInfinity"), brand))
    story.append(Paragraph("TAX INVOICE", heading))
    story.append(Spacer(1, 4 * mm))

    # Every free-text value below (seller settings, company billing fields,
    # invoice notes) is user/admin-supplied and gets concatenated into
    # reportlab Paragraph markup, which parses it as a small XML dialect. An
    # unescaped "<" (e.g. a billing address like "123 Main St <Suite 4B")
    # makes the paraparser raise, 400-ing /issue and stranding the invoice in
    # DRAFT. Escape each value with saxutils before it enters any Paragraph.
    # (item.description below lands in a plain Table cell, not a Paragraph,
    # so it is not parsed as markup and needs no escaping.)
    seller_lines = [_xml_escape(settings.SELLER_LEGAL_NAME or "SashaInfinity")]
    if settings.SELLER_ADDRESS:
        seller_lines.append(_xml_escape(settings.SELLER_ADDRESS))
    if settings.SELLER_GSTIN:
        seller_lines.append(f"GSTIN: {_xml_escape(settings.SELLER_GSTIN)}")
    seller_html = "<br/>".join(seller_lines)

    buyer_name = (company.legal_name or company.name) if company else "Company (record removed)"
    buyer_lines = [_xml_escape(buyer_name)]
    if company and company.billing_address:
        buyer_lines.append(_xml_escape(company.billing_address))
    if company and company.gstin:
        buyer_lines.append(f"GSTIN: {_xml_escape(company.gstin)}")
    # Place-of-supply state code: what decides CGST+SGST vs IGST on this
    # invoice, so it belongs on the printed document next to the buyer GSTIN.
    if company and (company.state_code or "").strip():
        buyer_lines.append(
            f"State code: {_xml_escape(company.state_code.strip())}")
    buyer_html = "<br/>".join(buyer_lines)

    meta_lines = [f"Invoice #: {number}"]
    if invoice.issued_at:
        meta_lines.append(f"Date: {invoice.issued_at.strftime('%Y-%m-%d')}")
    if invoice.due_date:
        meta_lines.append(f"Due: {invoice.due_date.strftime('%Y-%m-%d')}")
    meta_html = "<br/>".join(meta_lines)

    header_table = Table(
        [
            [Paragraph("<b>From</b>", label), Paragraph("<b>Bill To</b>", label)],
            [Paragraph(seller_html, normal), Paragraph(buyer_html, normal)],
            [Paragraph(meta_html, small), ""],
        ],
        colWidths=[85 * mm, 85 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    # ── Items table ──────────────────────────────────────────────────
    rows = [["#", "Description", "Qty", "Unit Price", "Line Total"]]
    for idx, item in enumerate(items, start=1):
        rows.append([
            str(idx),
            item.description,
            str(item.quantity),
            f"{float(item.unit_price):,.2f}",
            f"{float(item.line_total):,.2f}",
        ])
    items_table = Table(rows, colWidths=[10 * mm, 85 * mm, 15 * mm, 30 * mm, 30 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # ── Totals (right-aligned) ───────────────────────────────────────
    totals_rows = [["Subtotal", f"{float(invoice.subtotal):,.2f}"]]
    if float(invoice.cgst or 0):
        totals_rows.append(["CGST", f"{float(invoice.cgst):,.2f}"])
    if float(invoice.sgst or 0):
        totals_rows.append(["SGST", f"{float(invoice.sgst):,.2f}"])
    if float(invoice.igst or 0):
        totals_rows.append(["IGST", f"{float(invoice.igst):,.2f}"])
    totals_rows.append(["Total", f"{float(invoice.total):,.2f}"])

    totals_table = Table(totals_rows, colWidths=[30 * mm, 30 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.HexColor("#333333")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(totals_table)

    if invoice.tax_note:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(_xml_escape(invoice.tax_note), small))

    if invoice.notes:
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph("<b>Notes</b>", label))
        story.append(Paragraph(_xml_escape(invoice.notes), normal))

    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("This is a system-generated invoice.", small))

    doc.build(story)
    return file_path.replace(os.sep, "/")
