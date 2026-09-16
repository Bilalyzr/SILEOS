"""
Export/Import Router for Admin Data Management

Provides CSV/Excel/PDF export/import functionality for:
- users, students, instructors, spocs, companies, courses, blogs, dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, Date
from typing import Optional, List
from datetime import datetime, timedelta
import io
import csv
from decimal import Decimal

from app.core.database import get_db
from app.models.user import User, UserProfile, InstructorProfile
from app.services.auth_service import AuthService
from app.models.course import Course
from app.models.blog import BlogPost
from app.models.company import Company
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderStatus, Payment, PaymentStatus
from app.models.certificate import Certificate, IssuedCertificate
from app.models.coupon import Coupon
from app.models.cohort import Cohort
from app.models.internship import Internship, InternshipVoucher, InternshipAttendance

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_STYLES_AVAILABLE = True
except ImportError:
    OPENPYXL_STYLES_AVAILABLE = False

router = APIRouter()

# Company/Brand info for exports
BRAND_INFO = {
    "name": "SashaInfinity LMS",
    # Kept in step with the report footer (app/services/report_theme.BRAND).
    "website": "https://lms.sashainfinity.com",
    "logo_text": "SashaInfinity"
}

# CSV Schema definitions for each section (Enhanced with additional columns)
CSV_SCHEMAS = {
    "users": {
        "columns": ["id", "user_login", "user_email", "display_name", "role", "is_active", "is_verified", "last_login", "created_at"],
        "example": ["1", "johndoe", "john@example.com", "John Doe", "student", "True", "False", "2024-01-01 12:00:00", "2024-01-01 12:00:00"]
    },
    "students": {
        "columns": ["id", "user_login", "user_email", "display_name", "first_name", "last_name", "phone", "city", "last_login", "enrollment_count", "is_active", "created_at"],
        "example": ["1", "johndoe", "john@example.com", "John Doe", "John", "Doe", "+1234567890", "Chennai", "2024-01-15 10:30:00", "5", "True", "2024-01-01 12:00:00"]
    },
    "instructors": {
        "columns": ["id", "user_login", "user_email", "display_name", "first_name", "last_name", "designation", "bio", "expertise", "course_count", "average_rating", "is_active", "created_at"],
        "example": ["1", "janesmith", "jane@example.com", "Jane Smith", "Jane", "Smith", "Senior Instructor", "Expert in Python with 10+ years experience", "Python, Data Science, ML", "12", "4.5", "True", "2024-01-01 12:00:00"]
    },
    "spocs": {
        "columns": ["id", "user_login", "user_email", "display_name", "first_name", "last_name", "college_name", "designation", "phone", "city", "is_active", "created_at"],
        "example": ["1", "spoc1", "spoc@example.com", "SPOC User", "SPOC", "User", "ABC Engineering College", "Manager", "+1234567890", "Chennai", "True", "2024-01-01 12:00:00"]
    },
    "companies": {
        "columns": ["id", "name", "slug", "website", "industry", "team_size", "contact_email", "contact_phone", "approval_status", "intern_count", "active_internships", "created_at"],
        "example": ["1", "Tech Corp", "tech-corp", "https://techcorp.com", "Technology", "51-200", "contact@techcorp.com", "+1234567890", "Approved", "25", "8", "2024-01-01 12:00:00"]
    },
    "courses": {
        "columns": ["id", "post_title", "post_author", "author_name", "course_price", "sale_price", "course_price_type", "course_level", "course_category", "post_status", "total_enrollments", "average_rating", "review_count", "course_language", "created_at"],
        "example": ["1", "Python Basics", "2", "Jane Smith", "999.00", "499.00", "paid", "beginner", "Programming", "published", "150", "4.5", "45", "English", "2024-01-01 12:00:00"]
    },
    "blogs": {
        "columns": ["id", "title", "slug", "author_id", "author_email", "status", "category", "view_count", "published_at", "created_at"],
        "example": ["1", "Getting Started with Python", "getting-started-python", "2", "jane@example.com", "PUBLISHED", "Programming", "500", "2024-01-05 10:00:00", "2024-01-01 12:00:00"]
    },
    "orders": {
        "columns": ["id", "order_id", "user_id", "user_email", "total_amount", "currency", "payment_method", "payment_status", "transaction_id", "coupon_used", "created_at"],
        "example": ["1", "ORD-001", "5", "user@example.com", "999.00", "INR", "razorpay", "completed", "pay_1234567890", "SAVE20", "2024-01-01 12:00:00"]
    },
    "certificates": {
        "columns": ["id", "certificate_id", "user_id", "user_email", "course_id", "course_title", "issued_at", "expiry_date", "created_at"],
        "example": ["1", "CERT-001", "5", "user@example.com", "10", "Python Basics", "2024-01-15 10:00:00", "2025-01-15 10:00:00", "2024-01-15 10:00:00"]
    },
    "coupons": {
        "columns": ["id", "code", "discount_type", "discount_value", "max_uses", "used_count", "is_active", "valid_from", "valid_until", "created_at"],
        "example": ["1", "SAVE20", "percentage", "20", "1000", "150", "True", "2024-01-01", "2024-12-31", "2024-01-01 12:00:00"]
    },
    "enrollments": {
        "columns": ["id", "user_id", "student_name", "student_email", "course_id", "course_title", "enrollment_status", "course_progress_percentage", "enrollment_date", "completion_date", "created_at"],
        "example": ["1", "5", "John Doe", "john@example.com", "10", "Python Basics", "enrolled", "45", "2024-01-01 12:00:00", "", "2024-01-01 12:00:00"]
    },
    "reviews": {
        "columns": ["id", "course_id", "course_title", "instructor_id", "instructor_name", "student_id", "student_name", "student_email", "rating", "review_title", "review_content", "is_private", "created_at"],
        "example": ["1", "10", "Python Basics", "2", "Jane Smith", "5", "John Doe", "john@example.com", "5", "Great course", "Very helpful and clear", "True", "2024-01-01 12:00:00"]
    },
    "cohorts": {
        "columns": ["id", "name", "slug", "college_id", "college_name", "course_id", "course_title", "spoc_user_id", "spoc_name", "max_students", "student_count", "starts_on", "ends_on", "is_active", "created_at"],
        "example": ["1", "Cohort A", "cohort-a", "3", "ABC College", "10", "Python Basics", "7", "SPOC User", "50", "25", "2024-01-01", "2024-06-01", "True", "2024-01-01 12:00:00"]
    },
    "lessons": {
        "columns": ["id", "post_title", "course_id", "course_title", "menu_order", "post_type", "lesson_video_duration", "lesson_video_source", "post_status", "created_at"],
        "example": ["1", "Introduction to Python", "10", "Python Basics", "1", "lesson", "00:12:30", "youtube", "publish", "2024-01-01 12:00:00"]
    },
    "quizzes": {
        "columns": ["id", "post_title", "course_id", "course_title", "question_count", "quiz_passing_grade", "quiz_time_limit", "post_status", "created_at"],
        "example": ["1", "Python Basics Quiz", "10", "Python Basics", "15", "80", "30", "publish", "2024-01-01 12:00:00"]
    },
    "internship_requests": {
        "columns": ["id", "title", "company_id", "company_name", "requested_by", "requester_name", "intern_count", "start_date", "end_date", "status", "reviewed_at", "created_at"],
        "example": ["1", "Full Stack Developer Internship", "4", "Tech Corp", "8", "Manager User", "5", "2024-02-01", "2024-05-01", "pending", "", "2024-01-01 12:00:00"]
    },
    "dashboard": {
        "columns": ["metric", "value", "label"],
        "example": ["total_courses", "10", "Total Courses"]
    },
    "internships": {
        "columns": ["id", "title", "slug", "price", "is_published", "student_count", "student_names", "student_emails", "spoc_name", "spoc_email", "cohort_name", "description", "created_at", "updated_at"],
        "example": ["1", "Full Stack Developer Internship", "fsd-internship", "15000", "Yes", "5", "John | Jane | Bob", "john@email.com | jane@email.com", "Abirama R", "abirama@example.com", "Cohort A", "Full stack development program", "2024-01-01", "2024-01-01"]
    },
    "internship_roster": {
        "columns": ["student_name", "student_email", "voucher_code", "voucher_status", "internship_title", "course_progress", "completed_status", "certificates_issued", "attendance_days", "hired_by_company", "enrollment_date", "redeemed_date"],
        "example": ["Janani R", "janani@email.com", "INTR-ABC123", "redeemed", "Full Stack Internship", "45%", "In Progress", "0", "12", "Tech Corp", "2024-01-01", "2024-01-05"]
    },
    # Role-specific export sections
    "instructor_courses": {
        "columns": ["id", "post_title", "course_category", "course_level", "course_price", "sale_price", "total_enrollments", "average_rating", "review_count", "post_status", "course_language", "created_at"],
        "example": ["1", "Python Basics", "Programming", "beginner", "999.00", "499.00", "150", "4.5", "45", "published", "English", "2024-01-01 12:00:00"]
    },
    "instructor_students": {
        "columns": ["id", "student_name", "student_email", "course_title", "enrollment_date", "course_progress", "completion_status", "last_accessed"],
        "example": ["1", "John Doe", "john@example.com", "Python Basics", "2024-01-15", "75", "in_progress", "2024-01-20 10:30:00"]
    },
    "instructor_quiz_results": {
        "columns": ["id", "student_name", "student_email", "course_title", "quiz_title", "score", "total_marks", "percentage", "completed_at"],
        "example": ["1", "John Doe", "john@example.com", "Python Basics", "Python Quiz 1", "8", "10", "80", "2024-01-20 14:30:00"]
    },
    "instructor_assignment_results": {
        "columns": ["id", "student_name", "student_email", "course_title", "assignment_title", "status", "grade", "submitted_at", "reviewed_at"],
        "example": ["1", "John Doe", "john@example.com", "Python Basics", "Assignment 1", "submitted", "A", "2024-01-20 14:30:00", "2024-01-21 10:00:00"]
    },
    # Student ("my learning") sections — the learner's own records only.
    "student_courses": {
        "columns": ["id", "course_title", "instructor_name", "enrollment_date", "course_progress", "status", "completion_date"],
        "example": ["1", "Python Basics", "Jane Smith", "Jan 15, 2024", "75%", "Enrolled", "—"]
    },
    "student_certificates": {
        "columns": ["id", "certificate_id", "course_title", "completion_date", "issued_at", "verification_code", "status"],
        "example": ["1", "SI-CERT-0001", "Python Basics", "Mar 02, 2024", "Mar 02, 2024", "a1b2c3d4", "Valid"]
    },
    "student_quiz_results": {
        "columns": ["id", "course_title", "quiz_title", "score", "total_marks", "percentage", "result", "completed_at"],
        "example": ["1", "Python Basics", "Python Quiz 1", "8", "10", "80.0%", "Passed", "2024-01-20 14:30:00"]
    },
    "student_assignment_results": {
        "columns": ["id", "course_title", "assignment_title", "status", "grade", "submitted_at", "reviewed_at"],
        "example": ["1", "Python Basics", "Assignment 1", "Submitted", "A", "2024-01-20 14:30:00", "2024-01-21 10:00:00"]
    },
    "spoc_students": {
        "columns": ["id", "student_name", "student_email", "phone", "city", "enrolled_courses", "enrollment_count", "is_active", "created_at"],
        "example": ["1", "John Doe", "john@example.com", "+1234567890", "Chennai", "Python Basics, Data Science", "2", "True", "2024-01-01 12:00:00"]
    },
    "spoc_internships": {
        "columns": ["id", "internship_title", "company_name", "stipend", "assigned_students", "status", "created_at"],
        "example": ["1", "Full Stack Developer", "Tech Corp", "15000", "5", "active", "2024-01-01 12:00:00"]
    },
    "spoc_placements": {
        "columns": ["id", "student_name", "student_email", "company_name", "position", "stipend", "placed_date"],
        "example": ["1", "John Doe", "john@example.com", "Tech Corp", "Developer", "18000", "2024-03-15"]
    },
    # B3 (2026-09-04): the SPOC blog page's Export button called the admin-only
    # GET /admin/export/blogs; no SPOC-scoped equivalent existed. Same column
    # shape as the admin "blogs" section, scoped to the SPOC's own posts only
    # (get_role_section_query / serialize_item below).
    "spoc_blogs": {
        "columns": ["id", "title", "slug", "author_id", "author_email", "status", "category", "view_count", "published_at", "created_at"],
        "example": ["1", "Getting Started with Python", "getting-started-python", "2", "spoc@example.com", "PUBLISHED", "Programming", "500", "2024-01-05 10:00:00", "2024-01-01 12:00:00"]
    },
    "company_positions": {
        "columns": ["id", "title", "stipend", "required_skills", "applicants_count", "status", "posted_date"],
        "example": ["1", "Full Stack Developer", "15000", "Python, React", "25", "active", "2024-01-01 12:00:00"]
    },
    "company_interns": {
        "columns": ["id", "intern_name", "intern_email", "college_name", "position_title", "join_date", "attendance_percentage", "status"],
        "example": ["1", "John Doe", "john@example.com", "ABC Engineering", "Developer", "2024-01-15", "85", "active"]
    },
    "company_performance": {
        "columns": ["id", "intern_name", "intern_email", "position_title", "rating", "feedback", "review_date", "reviewer_name"],
        "example": ["1", "John Doe", "john@example.com", "Developer", "4.5", "Excellent performance", "2024-03-15", "Jane Manager"]
    }
}


def datetime_serializer(obj):
    """Serialize datetime/date objects to ISO format string."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return str(float(obj))
    return obj


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime(format_str)


def format_date_readable(dt: Optional[datetime]) -> str:
    """Format datetime to readable date format (e.g., May 01, 2026)."""
    if dt is None:
        return "N/A"
    return dt.strftime("%b %d, %Y")




def generate_pdf(data: List[dict], columns: List[str], title: str,
                 filters: Optional[dict] = None, role: str = "admin") -> bytes:
    """Generate a branded PDF report using reportlab.

    `role` selects the report design — see app/services/report_theme.py. Admin,
    instructor and student reports are deliberately distinguishable: different
    masthead treatment, palette and row density.
    """
    from app.services.report_theme import (
        get_theme, make_page_decorator, register_fonts, top_margin_for, PALETTE,
    )

    theme = get_theme(role)
    font, font_bold = register_fonts()

    output = io.BytesIO()
    # Landscape gives wide data tables room to breathe (portrait A4 is only
    # ~7.5in usable, which crams multi-column exports and forces overlap).
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        topMargin=top_margin_for(theme),
        bottomMargin=0.75*inch,
        leftMargin=0.4*inch,
        rightMargin=0.4*inch,
        title=f"{title} — {theme.label}",
        author=BRAND_INFO['name'],
    )
    decorate = make_page_decorator(theme, subtitle=title)

    elements = []

    # Styles
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=19,
        textColor=theme.primary,
        spaceAfter=2,
        alignment=TA_LEFT,
        fontName=font_bold
    )

    eyebrow_style = ParagraphStyle(
        'Eyebrow',
        parent=styles['Normal'],
        fontSize=7.5,
        textColor=theme.accent,
        fontName=font_bold,
        spaceAfter=3
    )

    # Summary section style
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName=font,
        textColor=colors.HexColor(PALETTE['body']),
        spaceAfter=12,
        leftIndent=0
    )

    # Title block. The brand lockup itself is painted on the canvas masthead by
    # the page decorator, so it repeats on every page instead of only page one.
    elements.append(Paragraph(theme.eyebrow, eyebrow_style))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(0, 0.12*inch))

    # Executive Summary Section
    exec_style = ParagraphStyle(
        'ExecSummary',
        parent=styles['Normal'],
        fontSize=9,
        textColor=theme.primary,
        spaceAfter=4,
        leftIndent=0,
        fontName=font_bold
    )
    elements.append(Paragraph("EXECUTIVE SUMMARY", exec_style))

    # Summary section
    summary_parts = [
        f"<b>Total Records:</b> {len(data)}",
    ]

    if filters:
        filter_parts = []
        if filters.get('status'):
            filter_parts.append(f"Status: {filters['status']}")
        if filters.get('date_from'):
            filter_parts.append(f"From: {format_datetime(filters['date_from'])}")
        if filters.get('date_to'):
            filter_parts.append(f"To: {format_datetime(filters['date_to'])}")
        if filters.get('search'):
            filter_parts.append(f"Search: {filters['search']}")
        if filter_parts:
            summary_parts.append(f"<b>Filters Applied:</b> {', '.join(filter_parts)}")

    summary_parts.append(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_parts.append(f"<b>Source:</b> {BRAND_INFO['website']}")

    elements.append(Paragraph(" | ".join(summary_parts), summary_style))
    elements.append(Spacer(0, 0.15*inch))

    # Add key statistics for specific sections
    if data and len(data) > 0:
        stats_style = ParagraphStyle(
            'StatsStyle',
            parent=styles['Normal'],
            fontSize=8.5,
            fontName=font,
            textColor=colors.HexColor(PALETTE['body']),
            spaceAfter=3
        )

        # Calculate basic stats
        elements.append(Paragraph("<b>Key Insights:</b>", stats_style))

        # Generic stats that work for most data
        numeric_cols = [col for col in columns if any(
            isinstance(d.get(col), (int, float)) and d.get(col) is not None
            for d in data[:100])]

        insight_lines = [f"• Data contains {len(columns)} columns with {len(data)} records"]

        # Add specific insights based on column names
        if 'price' in columns or 'amount' in columns or 'total_amount' in columns:
            price_col = next((c for c in columns if 'price' in c or 'amount' in c), None)
            if price_col:
                prices = [float(d.get(price_col, 0) or 0) for d in data if d.get(price_col)]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    insight_lines.append(f"• Average {price_col.replace('_', ' ')}: ₹{avg_price:,.2f}")

        if 'is_published' in columns:
            published = sum(1 for d in data if d.get('is_published') in ['Yes', 'True', 'yes', True])
            pct = (published / len(data) * 100) if data else 0
            insight_lines.append(f"• Published: {published}/{len(data)} ({pct:.1f}%)")

        if 'is_active' in columns:
            active = sum(1 for d in data if d.get('is_active') in ['True', 'yes', True])
            pct = (active / len(data) * 100) if data else 0
            insight_lines.append(f"• Active: {active}/{len(data)} ({pct:.1f}%)")

        if 'student_count' in columns:
            total_students = sum(int(d.get('student_count', 0) or 0) for d in data)
            insight_lines.append(f"• Total Students: {total_students:,}")

        # Internship roster specific insights
        if 'voucher_status' in columns:
            redeemed = sum(1 for d in data if d.get('voucher_status') == 'Redeemed')
            issued = len(data) - redeemed
            pct = (redeemed / len(data) * 100) if data else 0
            insight_lines.append(f"• Redeemed: {redeemed}/{len(data)} ({pct:.1f}%) | Issued: {issued}")

        if 'course_progress' in columns:
            # Calculate average progress (parse "45%" format)
            progress_values = []
            for d in data:
                prog_str = d.get('course_progress', '0%')
                if prog_str and prog_str != 'N/A':
                    try:
                        prog_val = float(prog_str.replace('%', ''))
                        progress_values.append(prog_val)
                    except:
                        pass
            if progress_values:
                avg_progress = sum(progress_values) / len(progress_values)
                insight_lines.append(f"• Average Course Progress: {avg_progress:.1f}%")

        if 'certificates_issued' in columns:
            # Parse certificates (remove "days" suffix if present and convert to int)
            total_certs = 0
            for d in data:
                cert_str = d.get('certificates_issued', '0')
                try:
                    cert_val = int(cert_str)
                    total_certs += cert_val
                except:
                    pass
            insight_lines.append(f"• Total Certificates: {total_certs}")

        if 'hired_by_company' in columns:
            hired = sum(1 for d in data if d.get('hired_by_company') and d.get('hired_by_company') != 'N/A')
            pct = (hired / len(data) * 100) if data else 0
            insight_lines.append(f"• Hired: {hired}/{len(data)} ({pct:.1f}%)")

        for line in insight_lines[:5]:  # Limit to 5 insights
            elements.append(Paragraph(line, stats_style))

        elements.append(Spacer(0, 0.1*inch))

    # Handle empty data
    if not data:
        no_data_style = ParagraphStyle(
            'NoDataStyle',
            parent=styles['Normal'],
            fontSize=13,
            fontName=font,
            textColor=colors.HexColor(PALETTE['muted']),
            alignment=TA_CENTER,
            spaceAfter=30
        )
        elements.append(Paragraph("No data available for the selected criteria.", no_data_style))
        doc.build(elements, onFirstPage=decorate, onLaterPages=decorate)
        return output.getvalue()

    # Build table data with proper text wrapping and formatting
    table_data = []

    # Header row
    # Cell paragraph styles so long values WRAP inside their column. Plain
    # strings in reportlab table cells don't wrap — they overflow and overlap
    # the next column. wordWrap='CJK' also breaks long unbroken tokens
    # (emails, slugs, URLs) instead of running off the edge.
    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'], fontSize=theme.body_size,
        leading=theme.body_size + 2.5, fontName=font,
        textColor=colors.HexColor(PALETTE['body']), wordWrap='CJK'
    )
    header_cell_style = ParagraphStyle(
        'HeaderCell', parent=styles['Normal'], fontSize=theme.body_size + 1,
        leading=theme.body_size + 3, textColor=colors.whitesmoke,
        fontName=font_bold, wordWrap='CJK'
    )

    header_data = [
        Paragraph(col.replace('_', ' ').title(), header_cell_style)
        for col in columns
    ]
    table_data.append(header_data)

    # Data rows (limit to 200 rows for PDF performance)
    max_rows = min(len(data), 200)
    for i, row in enumerate(data[:max_rows]):
        row_data = []
        for col in columns:
            value = row.get(col, '')
            if value is None:
                value = 'N/A'

            # Format values for better readability
            value_str = str(value)

            # Format datetime strings to shorter format
            if col.endswith('_date') or col.endswith('_at'):
                try:
                    dt = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
                    value_str = dt.strftime('%Y-%m-%d')
                except:
                    pass  # Keep original if parsing fails

            # Fix specific formatting issues
            if col == 'course_progress':
                # Add space between % and next text if concatenated
                if '%N' in value_str or '%' in value_str and not value_str.endswith('%'):
                    value_str = value_str.replace('%', '% ')
                # Add % sign if it's just a number
                elif value_str.isdigit() or (value_str.replace('.', '', 1).isdigit()):
                    value_str = f"{value_str}%"

            elif col == 'attendance_days':
                # Already formatted with space, just ensure consistency
                if value_str == '0':
                    value_str = '0 days'
                elif not value_str.endswith(' days'):
                    # Handle old format "0days"
                    value_str = value_str.replace('days', ' days')

            # Cap only extreme lengths; Paragraph wrapping handles the rest
            # (no more mid-value truncation at 50 chars).
            if len(value_str) > 300:
                value_str = value_str[:297] + "..."
            safe = value_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            row_data.append(Paragraph(safe, cell_style))
        table_data.append(row_data)

    # Calculate column widths with better proportions
    col_widths = []
    total_width = 10.8  # inches (landscape A4 width minus margins)

    # Special width allocation based on column type
    for idx, col in enumerate(columns):
        if 'email' in col:
            col_width = 2.0  # Emails need more space
        elif 'name' in col and 'student' not in col:
            col_width = 1.5
        elif 'title' in col or 'description' in col:
            col_width = 1.8
        elif col in ['course_progress', 'completed_status']:
            col_width = 0.9
        elif col.endswith('_date') or col.endswith('_at'):
            col_width = 0.9  # Dates are shorter now
        elif 'voucher_code' in col or 'code' in col:
            col_width = 1.2
        elif col in ['certificates_issued', 'attendance_days']:
            col_width = 0.7
        else:
            col_width = 1.1
        col_widths.append(col_width)

    # Normalize widths so the table always spans the full usable page width
    # (scale down when too wide, up when too narrow — no half-empty tables).
    total_col_width = sum(col_widths)
    if total_col_width > 0:
        scale_factor = total_width / total_col_width
        col_widths = [w * scale_factor for w in col_widths]

    # Values above are in inches — convert to points (reportlab treats bare
    # numbers as points, which is what made every column ~1pt wide before).
    col_widths = [w * inch for w in col_widths]

    # Create table with repeatRows=1 to show header on each page
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Enhanced table styling with better spacing
    table.setStyle(TableStyle([
        # Header row — carries the role's primary colour.
        ('BACKGROUND', (0, 0), (-1, 0), theme.table_header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), theme.body_size + 1),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        # Accent hairline separating the header from the data.
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, theme.accent),

        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), font),
        ('FONTSIZE', (0, 1), (-1, -1), theme.body_size),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), theme.row_padding),
        ('BOTTOMPADDING', (0, 1), (-1, -1), theme.row_padding),
        ('LEFTPADDING', (0, 1), (-1, -1), 5),
        ('RIGHTPADDING', (0, 1), (-1, -1), 5),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(PALETTE['hairline'])),
        ('INNERGRID', (0, 1), (-1, -1), 0.25, colors.HexColor(PALETTE['zebra'])),

        # Alternating row colors — zebra tinted with the role's own hue.
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, theme.tint]),
    ]))

    elements.append(table)

    # Add note if data was truncated
    if len(data) > max_rows:
        elements.append(Spacer(0.2*inch, 0.2*inch))
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=styles['Normal'],
            fontSize=8.5,
            fontName=font,
            textColor=colors.HexColor(PALETTE['muted']),
            alignment=TA_CENTER
        )
        note = Paragraph(
            f"Showing first {max_rows} of {len(data)} records. "
            f"Export to Excel/CSV for complete data.",
            note_style
        )
        elements.append(note)

    # Build PDF
    doc.build(elements, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()


def generate_excel(data: List[dict], columns: List[str], title: str,
                   sheet_name: str, filters: Optional[dict] = None) -> bytes:
    """Generate enhanced Excel file from data using pandas/openpyxl."""
    output = io.BytesIO()

    # Create DataFrame
    df = pd.DataFrame(data)

    # Reorder columns according to schema
    available_columns = [col for col in columns if col in df.columns]
    df = df[available_columns]

    # Format column names for display
    df.columns = [col.replace('_', ' ').title() for col in df.columns]

    # Write to Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Main data sheet
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Sheet names max 31 chars

        if OPENPYXL_STYLES_AVAILABLE:
            workbook = writer.book
            worksheet = writer.sheets[sheet_name[:31]]

            # Define styles
            header_font = Font(bold=True, color='FFFFFF', size=11)
            header_fill = PatternFill(start_color='1E40AF', end_color='1E40AF', fill_type='solid')
            header_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            cell_alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            border = Border(
                left=Side(style='thin', color='D3D3D3'),
                right=Side(style='thin', color='D3D3D3'),
                top=Side(style='thin', color='D3D3D3'),
                bottom=Side(style='thin', color='D3D3D3')
            )

            # Apply header styling
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border

            # Apply cell styling and auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)

                for cell in column:
                    if cell.row > 1:  # Skip header
                        cell.alignment = cell_alignment
                        cell.border = border
                        # Format numbers
                        if isinstance(cell.value, (int, float)):
                            if cell.value == int(cell.value):
                                cell.number_format = '0'
                            else:
                                cell.number_format = '0.00'

                    # Calculate max length for column width
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))

                # Set column width (with bounds)
                adjusted_width = min(max(max_length * 1.2, 10), 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        # Summary sheet with enhanced metadata
        summary_data = {
            'Metric': [],
            'Value': []
        }

        summary_data['Metric'].extend([
            BRAND_INFO['name'],
            BRAND_INFO['website'],
            '',
            '='*50,
            'EXPORT SUMMARY',
            '='*50,
            '',
            'Report Type',
            'Data Sheet',
            'Total Records',
            'Total Columns',
            'Generated At',
            'Export Format',
            '',
        ])

        summary_data['Value'].extend([
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            title,
            sheet_name[:31],
            len(data),
            len(available_columns),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Microsoft Excel (.xlsx)',
            '',
        ])

        # Add filter information
        if filters:
            summary_data['Metric'].append('='*30)
            summary_data['Value'].append('='*30)
            summary_data['Metric'].append('FILTERS APPLIED')
            summary_data['Value'].append('')
            if filters.get('status'):
                summary_data['Metric'].append('  • Status')
                summary_data['Value'].append(filters['status'])
            if filters.get('date_from'):
                summary_data['Metric'].append('  • From Date')
                summary_data['Value'].append(format_datetime(filters['date_from']))
            if filters.get('date_to'):
                summary_data['Metric'].append('  To Date')
                summary_data['Value'].append(format_datetime(filters['date_to']))
            if filters.get('search'):
                summary_data['Metric'].append('  Search Term')
                summary_data['Value'].append(filters['search'])

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Column Descriptions sheet
        col_desc_data = {
            'Column': [],
            'Display Name': [],
            'Description': []
        }

        # Column descriptions mapping
        column_descriptions = {
            'id': 'Unique identifier',
            'title': 'Title or name',
            'slug': 'URL-friendly identifier',
            'price': 'Price in INR',
            'is_published': 'Published status',
            'is_active': 'Active status',
            'created_at': 'Creation timestamp',
            'updated_at': 'Last update timestamp',
            'user_login': 'Username',
            'user_email': 'Email address',
            'display_name': 'Full display name',
            'role': 'User role',
            'student_count': 'Number of students',
            'student_names': 'Student names separated by |',
            'student_emails': 'Student emails separated by |',
            'spoc_id': 'SPOC user ID',
            'spoc_name': 'SPOC name',
            'spoc_email': 'SPOC email',
            'cohort_id': 'Cohort ID',
            'cohort_name': 'Cohort name',
            'description': 'Description text',
            # Internship roster specific
            'student_name': 'Student full name',
            'student_email': 'Student email address',
            'voucher_code': 'Unique voucher code (e.g., INTR-ABC123)',
            'voucher_status': 'Voucher status (issued/redeemed)',
            'internship_title': 'Internship program name',
            'course_progress': 'Course completion percentage',
            'completed_status': 'Enrollment completion status',
            'certificates_issued': 'Number of certificates issued',
            'attendance_days': 'Attendance count in days',
            'hired_by_company': 'Company that hired the student',
            'enrollment_date': 'Date of enrollment/purchase',
            'redeemed_date': 'Date voucher was redeemed',
        }

        for col in available_columns:
            display_name = col.replace('_', ' ').title()
            desc = column_descriptions.get(col, f'{display_name} field')
            col_desc_data['Column'].append(col)
            col_desc_data['Display Name'].append(display_name)
            col_desc_data['Description'].append(desc)

        col_desc_df = pd.DataFrame(col_desc_data)
        col_desc_df.to_excel(writer, sheet_name='Column_Info', index=False)

        if OPENPYXL_STYLES_AVAILABLE:
            summary_sheet = writer.sheets['Summary']
            # Style summary sheet
            summary_sheet.column_dimensions['A'].width = 25
            summary_sheet.column_dimensions['B'].width = 40

            for row in summary_sheet.iter_rows(min_row=1, max_row=summary_sheet.max_row):
                for cell in row:
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                    if cell.row == 1 or cell.value == '':
                        cell.font = Font(bold=True, size=12, color='1E40AF')
                    elif cell.column == 1 and cell.value.startswith('  '):
                        cell.font = Font(italic=True, color='64748B')

            # Style column info sheet
            col_info_sheet = writer.sheets['Column_Info']
            col_info_sheet.column_dimensions['A'].width = 20
            col_info_sheet.column_dimensions['B'].width = 20
            col_info_sheet.column_dimensions['C'].width = 40

            for cell in col_info_sheet[1]:  # Header row
                cell.font = Font(bold=True, color='FFFFFF', size=11)
                cell.fill = PatternFill(start_color='1E40AF', end_color='1E40AF', fill_type='solid')
                cell.alignment = Alignment(horizontal='left', vertical='center')

    output.seek(0)
    return output.getvalue()


def generate_csv(data: List[dict], columns: List[str], title: str,
                 filters: Optional[dict] = None) -> bytes:
    """Generate enhanced CSV with BOM for Excel compatibility."""
    output = io.StringIO()

    # Enhanced header comments with rich metadata
    output.write(f"# =============================================================================\n")
    output.write(f"# {BRAND_INFO['name']} Data Export\n")
    output.write(f"# {BRAND_INFO['website']}\n")
    output.write(f"# =============================================================================\n")
    output.write(f"# Report Type: {title}\n")
    output.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.write(f"# Total Records: {len(data):,}\n")
    output.write(f"# Total Columns: {len(columns)}\n")
    output.write(f"# =============================================================================\n")

    # Add filter information
    if filters:
        output.write(f"# FILTERS APPLIED:\n")
        if filters.get('status'):
            output.write(f"#   - Status: {filters['status']}\n")
        if filters.get('date_from'):
            output.write(f"#   - From Date: {format_datetime(filters['date_from'])}\n")
        if filters.get('date_to'):
            output.write(f"#   - To Date: {format_datetime(filters['date_to'])}\n")
        if filters.get('search'):
            output.write(f"#   - Search: {filters['search']}\n")
        output.write(f"# =============================================================================\n")

    # Column descriptions
    output.write(f"# COLUMN DESCRIPTIONS:\n")
    column_descriptions = {
        'id': 'Unique identifier',
        'title': 'Title or name',
        'slug': 'URL-friendly identifier',
        'price': 'Price in INR',
        'is_published': 'Published status (Yes/No)',
        'is_active': 'Active status (True/False)',
        'created_at': 'Creation timestamp (YYYY-MM-DD HH:MM:SS)',
        'updated_at': 'Last update timestamp',
        'user_login': 'Username',
        'user_email': 'Email address',
        'display_name': 'Full display name',
        'role': 'User role (student/instructor/admin/etc)',
        'student_count': 'Number of enrolled students',
        'student_names': 'Student names (separated by |)',
        'student_emails': 'Student emails (separated by |)',
        'spoc_name': 'SPOC name',
        'spoc_email': 'SPOC email address',
        'cohort_name': 'Cohort name',
        'description': 'Full description text',
        # Internship roster specific
        'student_name': 'Student full name',
        'student_email': 'Student email address',
        'voucher_code': 'Unique voucher code (e.g., INTR-ABC123)',
        'voucher_status': 'Voucher status (Issued/Redeemed)',
        'internship_title': 'Internship program name',
        'course_progress': 'Course completion percentage (0-100%)',
        'completed_status': 'Enrollment status (Not Started/In Progress/Completed)',
        'certificates_issued': 'Number of certificates issued to student',
        'attendance_days': 'Number of days present (format: Xdays)',
        'hired_by_company': 'Company name if hired, or N/A',
        'enrollment_date': 'Date student enrolled/purchased internship',
        'redeemed_date': 'Date voucher was redeemed for course access',
    }

    for col in columns:
        display_name = col.replace('_', ' ').title()
        desc = column_descriptions.get(col, f'{display_name} field')
        output.write(f"#   - {col}: {desc}\n")

    output.write(f"# =============================================================================\n")
    output.write(f"# DATA STARTS BELOW\n")
    output.write(f"\n")

    # Create CSV writer
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()

    for row in data:
        # Format values for CSV
        formatted_row = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                formatted_row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            elif value is None:
                formatted_row[key] = ''
            else:
                formatted_row[key] = value
        writer.writerow(formatted_row)

    # Get the CSV content and add BOM
    csv_content = output.getvalue()
    output_bytes = io.BytesIO()
    # UTF-8 BOM for Excel compatibility
    output_bytes.write(b'\xef\xbb\xbf')
    output_bytes.write(csv_content.encode('utf-8'))
    output_bytes.seek(0)
    return output_bytes.getvalue()


def get_section_query(db: Session, section: str, status: Optional[str] = None,
                      date_from: Optional[datetime] = None,
                      date_to: Optional[datetime] = None,
                      search: Optional[str] = None):
    """Build query for the specified section with filters."""

    if section == "users":
        query = db.query(User)
        if status:
            if status == "active":
                query = query.filter(User.is_active == True)
            elif status == "inactive":
                query = query.filter(User.is_active == False)
        if date_from:
            query = query.filter(User.created_at >= date_from)
        if date_to:
            query = query.filter(User.created_at <= date_to)
        if search:
            query = query.filter(
                (User.user_email.ilike(f"%{search}%")) |
                (User.display_name.ilike(f"%{search}%")) |
                (User.user_login.ilike(f"%{search}%"))
            )
        return query.all()

    elif section == "students":
        query = db.query(User).join(UserProfile).filter(User.role == "student")
        if status:
            if status == "active":
                query = query.filter(User.is_active == True)
            elif status == "inactive":
                query = query.filter(User.is_active == False)
        if date_from:
            query = query.filter(User.created_at >= date_from)
        if date_to:
            query = query.filter(User.created_at <= date_to)
        if search:
            query = query.filter(
                (User.user_email.ilike(f"%{search}%")) |
                (User.display_name.ilike(f"%{search}%"))
            )
        return query.all()

    elif section == "instructors":
        # OUTER join — instructors without an instructor_profiles row must still
        # export (inner join silently dropped them). serialize_item handles a
        # missing profile, and course_count/avg_rating are computed separately.
        query = db.query(User).outerjoin(InstructorProfile).filter(User.role == "instructor")
        if status:
            if status == "active":
                query = query.filter(User.is_active == True)
            elif status == "inactive":
                query = query.filter(User.is_active == False)
        if date_from:
            query = query.filter(User.created_at >= date_from)
        if date_to:
            query = query.filter(User.created_at <= date_to)
        if search:
            query = query.filter(
                (User.user_email.ilike(f"%{search}%")) |
                (User.display_name.ilike(f"%{search}%"))
            )
        return query.all()

    elif section == "spocs":
        query = db.query(User).filter(User.role == "spoc")
        if status:
            if status == "active":
                query = query.filter(User.is_active == True)
            elif status == "inactive":
                query = query.filter(User.is_active == False)
        if date_from:
            query = query.filter(User.created_at >= date_from)
        if date_to:
            query = query.filter(User.created_at <= date_to)
        if search:
            query = query.filter(
                (User.user_email.ilike(f"%{search}%")) |
                (User.display_name.ilike(f"%{search}%"))
            )
        return query.all()

    elif section == "companies":
        query = db.query(Company)
        if status:
            if status == "approved":
                query = query.filter(Company.is_approved == True)
            elif status == "pending":
                query = query.filter(Company.is_approved == False)
        if date_from:
            query = query.filter(Company.created_at >= date_from)
        if date_to:
            query = query.filter(Company.created_at <= date_to)
        if search:
            query = query.filter(
                (Company.name.ilike(f"%{search}%")) |
                (Company.contact_email.ilike(f"%{search}%"))
            )
        return query.all()

    elif section == "courses":
        query = db.query(Course)
        if status:
            query = query.filter(Course.post_status == status)
        if date_from:
            query = query.filter(Course.created_at >= date_from)
        if date_to:
            query = query.filter(Course.created_at <= date_to)
        if search:
            query = query.filter(Course.post_title.ilike(f"%{search}%"))
        return query.all()

    elif section == "blogs":
        query = db.query(BlogPost)
        if status:
            query = query.filter(BlogPost.status == status.upper())
        if date_from:
            query = query.filter(BlogPost.created_at >= date_from)
        if date_to:
            query = query.filter(BlogPost.created_at <= date_to)
        if search:
            query = query.filter(BlogPost.title.ilike(f"%{search}%"))
        return query.all()

    elif section == "orders":
        query = db.query(Order)
        if status:
            # Orders carry `order_status` (OrderStatus); `payment_status` lives on
            # the Payment row, not the Order.
            order_status = {
                "completed": OrderStatus.COMPLETED,
                "pending": OrderStatus.PENDING,
                "processing": OrderStatus.PROCESSING,
                "failed": OrderStatus.FAILED,
                "cancelled": OrderStatus.CANCELLED,
                "refunded": OrderStatus.REFUNDED,
            }.get(status.lower())
            if order_status is not None:
                query = query.filter(Order.order_status == order_status)
        if date_from:
            query = query.filter(Order.created_at >= date_from)
        if date_to:
            query = query.filter(Order.created_at <= date_to)
        return query.all()

    elif section == "certificates":
        query = db.query(IssuedCertificate)
        if date_from:
            query = query.filter(IssuedCertificate.created_at >= date_from)
        if date_to:
            query = query.filter(IssuedCertificate.created_at <= date_to)
        return query.all()

    elif section == "coupons":
        query = db.query(Coupon)
        if status:
            if status == "active":
                query = query.filter(Coupon.is_active == True)
            elif status == "inactive":
                query = query.filter(Coupon.is_active == False)
        if date_from:
            query = query.filter(Coupon.created_at >= date_from)
        if date_to:
            query = query.filter(Coupon.created_at <= date_to)
        if search:
            query = query.filter(Coupon.code.ilike(f"%{search}%"))
        return query.all()

    elif section == "internships":
        query = db.query(Internship)
        if status:
            if status == "active":
                query = query.filter(Internship.is_published == True)
            elif status == "inactive":
                query = query.filter(Internship.is_published == False)
        if date_from:
            query = query.filter(Internship.created_at >= date_from)
        if date_to:
            query = query.filter(Internship.created_at <= date_to)
        if search:
            query = query.filter(Internship.title.ilike(f"%{search}%"))
        return query.all()

    elif section == "internship_roster":
        # Return all vouchers with student details - one row per student
        from app.models.company import Company

        # Build query with joins
        query = db.query(InternshipVoucher)

        # Filter by status (issued/redeemed)
        if status:
            if status == "issued":
                query = query.filter(InternshipVoucher.status == "issued")
            elif status == "redeemed":
                query = query.filter(InternshipVoucher.status == "redeemed")

        # Filter by date (voucher created date)
        if date_from:
            query = query.filter(InternshipVoucher.created_at >= date_from)
        if date_to:
            query = query.filter(InternshipVoucher.created_at <= date_to)

        # Search by student name or voucher code
        if search:
            # Subquery to find matching user IDs
            matching_users = db.query(User.id).filter(
                (User.display_name.ilike(f"%{search}%")) |
                (User.user_email.ilike(f"%{search}%"))
            ).all()
            user_ids = [u[0] for u in matching_users]
            # Filter by voucher code OR matching users
            query = query.filter(
                (InternshipVoucher.code.ilike(f"%{search}%")) |
                (InternshipVoucher.buyer_user_id.in_(user_ids))
            )

        return query.all()

    elif section == "enrollments":
        query = db.query(Enrollment)
        if status:
            query = query.filter(Enrollment.enrollment_status == status)
        if date_from:
            query = query.filter(Enrollment.enrollment_date >= date_from)
        if date_to:
            query = query.filter(Enrollment.enrollment_date <= date_to)
        if search:
            matching_users = db.query(User.id).filter(
                (User.display_name.ilike(f"%{search}%")) |
                (User.user_email.ilike(f"%{search}%"))
            ).all()
            user_ids = [u[0] for u in matching_users]
            query = query.filter(Enrollment.user_id.in_(user_ids))
        return query.all()

    elif section == "reviews":
        from app.models.instructor_review import InstructorReview
        query = db.query(InstructorReview)
        if date_from:
            query = query.filter(InstructorReview.created_at >= date_from)
        if date_to:
            query = query.filter(InstructorReview.created_at <= date_to)
        if search:
            query = query.filter(
                (InstructorReview.review_title.ilike(f"%{search}%")) |
                (InstructorReview.review_content.ilike(f"%{search}%"))
            )
        return query.all()

    elif section == "cohorts":
        query = db.query(Cohort)
        if status:
            if status == "active":
                query = query.filter(Cohort.is_active == True)
            elif status == "inactive":
                query = query.filter(Cohort.is_active == False)
        if date_from:
            query = query.filter(Cohort.created_at >= date_from)
        if date_to:
            query = query.filter(Cohort.created_at <= date_to)
        if search:
            query = query.filter(Cohort.name.ilike(f"%{search}%"))
        return query.all()

    elif section == "lessons":
        from app.models.course import Lesson
        query = db.query(Lesson)
        if status:
            query = query.filter(Lesson.post_status == status)
        if date_from:
            query = query.filter(Lesson.created_at >= date_from)
        if date_to:
            query = query.filter(Lesson.created_at <= date_to)
        if search:
            query = query.filter(Lesson.post_title.ilike(f"%{search}%"))
        return query.all()

    elif section == "quizzes":
        from app.models.quiz import Quiz
        query = db.query(Quiz)
        if status:
            query = query.filter(Quiz.post_status == status)
        if date_from:
            query = query.filter(Quiz.created_at >= date_from)
        if date_to:
            query = query.filter(Quiz.created_at <= date_to)
        if search:
            query = query.filter(Quiz.post_title.ilike(f"%{search}%"))
        return query.all()

    elif section == "internship_requests":
        from app.models.internship_request import InternshipRequest
        query = db.query(InternshipRequest)
        if status:
            query = query.filter(InternshipRequest.status == status)
        if date_from:
            query = query.filter(InternshipRequest.created_at >= date_from)
        if date_to:
            query = query.filter(InternshipRequest.created_at <= date_to)
        if search:
            query = query.filter(InternshipRequest.title.ilike(f"%{search}%"))
        return query.all()

    raise HTTPException(status_code=400, detail=f"Invalid section: {section}")


def get_role_section_query(db: Session, section: str, current_user: User,
                          status: Optional[str] = None,
                          date_from: Optional[datetime] = None,
                          date_to: Optional[datetime] = None,
                          search: Optional[str] = None):
    """Build query for role-scoped sections with user filtering."""

    # Instructor sections
    if section == "instructor_courses":
        query = db.query(Course).filter(Course.post_author == current_user.id)
        if status:
            query = query.filter(Course.post_status == status)
        if date_from:
            query = query.filter(Course.created_at >= date_from)
        if date_to:
            query = query.filter(Course.created_at <= date_to)
        if search:
            query = query.filter(Course.post_title.ilike(f"%{search}%"))
        return query.all()

    elif section == "instructor_students":
        # Students enrolled in instructor's courses
        query = db.query(Enrollment).join(Course).filter(Course.post_author == current_user.id)
        if date_from:
            query = query.filter(Enrollment.enrollment_date >= date_from)
        if date_to:
            query = query.filter(Enrollment.enrollment_date <= date_to)
        if search:
            query = query.join(User).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    elif section == "instructor_quiz_results":
        from app.models.quiz import Quiz, QuizAttempt
        # QuizAttempt links straight to the course; the finish timestamp column is
        # attempt_ended_at (there is no `completed_at`).
        query = db.query(QuizAttempt).join(
            Course, Course.id == QuizAttempt.course_id
        ).filter(Course.post_author == current_user.id)
        if date_from:
            query = query.filter(QuizAttempt.attempt_ended_at >= date_from)
        if date_to:
            query = query.filter(QuizAttempt.attempt_ended_at <= date_to)
        if search:
            query = query.join(User, User.id == QuizAttempt.user_id).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    elif section == "instructor_assignment_results":
        from app.models.assignment import Assignment, AssignmentSubmission
        query = db.query(AssignmentSubmission).join(
            Assignment, Assignment.id == AssignmentSubmission.assignment_id
        ).join(
            Course, Course.id == Assignment.course_id
        ).filter(Course.post_author == current_user.id)
        if date_from:
            query = query.filter(AssignmentSubmission.submitted_at >= date_from)
        if date_to:
            query = query.filter(AssignmentSubmission.submitted_at <= date_to)
        if search:
            query = query.join(User, User.id == AssignmentSubmission.user_id).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    # Student sections — always scoped to the caller's own records.
    elif section == "student_courses":
        query = db.query(Enrollment).filter(Enrollment.user_id == current_user.id)
        if status:
            query = query.filter(Enrollment.enrollment_status == status)
        if date_from:
            query = query.filter(Enrollment.enrollment_date >= date_from)
        if date_to:
            query = query.filter(Enrollment.enrollment_date <= date_to)
        if search:
            query = query.join(Course, Course.id == Enrollment.course_id).filter(
                Course.post_title.ilike(f"%{search}%")
            )
        return query.all()

    elif section == "student_certificates":
        query = db.query(IssuedCertificate).filter(IssuedCertificate.user_id == current_user.id)
        if date_from:
            query = query.filter(IssuedCertificate.created_at >= date_from)
        if date_to:
            query = query.filter(IssuedCertificate.created_at <= date_to)
        return query.all()

    elif section == "student_quiz_results":
        from app.models.quiz import QuizAttempt
        query = db.query(QuizAttempt).filter(QuizAttempt.user_id == current_user.id)
        if date_from:
            query = query.filter(QuizAttempt.attempt_ended_at >= date_from)
        if date_to:
            query = query.filter(QuizAttempt.attempt_ended_at <= date_to)
        return query.all()

    elif section == "student_assignment_results":
        from app.models.assignment import AssignmentSubmission
        query = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.user_id == current_user.id
        )
        if date_from:
            query = query.filter(AssignmentSubmission.submitted_at >= date_from)
        if date_to:
            query = query.filter(AssignmentSubmission.submitted_at <= date_to)
        return query.all()

    # SPOC sections
    # Note: SPOC role users are identified via their role and spoc_user_id on Internship
    elif section == "spoc_students":
        # Get internships where this user is the SPOC, then get students from vouchers
        spoc_internship_ids = db.query(Internship.id).filter(
            Internship.spoc_user_id == current_user.id
        ).all()
        spoc_internship_ids = [i[0] for i in spoc_internship_ids]

        if not spoc_internship_ids:
            return []

        # Get students who purchased vouchers for these internships
        query = db.query(User).join(InternshipVoucher, InternshipVoucher.buyer_user_id == User.id).filter(
            InternshipVoucher.internship_id.in_(spoc_internship_ids)
        ).distinct()
        if status:
            if status == "active":
                query = query.filter(User.is_active == True)
            elif status == "inactive":
                query = query.filter(User.is_active == False)
        if date_from:
            query = query.filter(User.created_at >= date_from)
        if date_to:
            query = query.filter(User.created_at <= date_to)
        if search:
            query = query.filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    elif section == "spoc_internships":
        # Get internships where this user is the SPOC
        query = db.query(Internship).filter(Internship.spoc_user_id == current_user.id)
        if status:
            if status == "active":
                query = query.filter(Internship.is_published == True)
            elif status == "inactive":
                query = query.filter(Internship.is_published == False)
        if date_from:
            query = query.filter(Internship.created_at >= date_from)
        if date_to:
            query = query.filter(Internship.created_at <= date_to)
        if search:
            query = query.filter(Internship.title.ilike(f"%{search}%"))
        return query.all()

    elif section == "spoc_placements":
        # Get vouchers for internships where this user is SPOC and student was hired
        spoc_internship_ids = db.query(Internship.id).filter(
            Internship.spoc_user_id == current_user.id
        ).all()
        spoc_internship_ids = [i[0] for i in spoc_internship_ids]

        if not spoc_internship_ids:
            return []

        query = db.query(InternshipVoucher).filter(
            InternshipVoucher.internship_id.in_(spoc_internship_ids),
            InternshipVoucher.hired_by_company_id.isnot(None)
        )
        if date_from:
            query = query.filter(InternshipVoucher.hired_by_override_at >= date_from)
        if date_to:
            query = query.filter(InternshipVoucher.hired_by_override_at <= date_to)
        if search:
            matching_users = db.query(User.id).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            ).all()
            user_ids = [u[0] for u in matching_users]
            query = query.filter(InternshipVoucher.buyer_user_id.in_(user_ids))
        return query.all()

    elif section == "spoc_blogs":
        # Scoped identically to GET /blog/spoc/my-posts (blog.py) — the
        # SPOC's own authored posts only.
        query = db.query(BlogPost).filter(BlogPost.author_id == current_user.id)
        if status:
            query = query.filter(BlogPost.status == status.upper())
        if date_from:
            query = query.filter(BlogPost.created_at >= date_from)
        if date_to:
            query = query.filter(BlogPost.created_at <= date_to)
        if search:
            query = query.filter(BlogPost.title.ilike(f"%{search}%"))
        return query.all()

    # Company sections
    elif section == "company_positions":
        # Get company from current user (company role users own companies via owner_user_id)
        company = db.query(Company).filter(Company.owner_user_id == current_user.id).first()
        if not company:
            return []
        # Return company's expressed interests in candidates
        from app.models.company import CompanyInterest
        query = db.query(CompanyInterest).filter(CompanyInterest.company_id == company.id)
        if status:
            query = query.filter(CompanyInterest.status == status)
        if date_from:
            query = query.filter(CompanyInterest.created_at >= date_from)
        if date_to:
            query = query.filter(CompanyInterest.created_at <= date_to)
        if search:
            matching_users = db.query(User.id).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            ).all()
            user_ids = [u[0] for u in matching_users]
            query = query.filter(CompanyInterest.candidate_user_id.in_(user_ids))
        return query.all()

    elif section == "company_interns":
        # Vouchers where hired_by_company_id matches this company
        company = db.query(Company).filter(Company.owner_user_id == current_user.id).first()
        if not company:
            return []
        query = db.query(InternshipVoucher).filter(InternshipVoucher.hired_by_company_id == company.id)
        if status:
            query = query.filter(InternshipVoucher.status == status)
        if date_from:
            query = query.filter(InternshipVoucher.created_at >= date_from)
        if date_to:
            query = query.filter(InternshipVoucher.created_at <= date_to)
        if search:
            matching_users = db.query(User.id).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            ).all()
            user_ids = [u[0] for u in matching_users]
            query = query.filter(InternshipVoucher.buyer_user_id.in_(user_ids))
        return query.all()

    elif section == "company_performance":
        # Attendance records for interns hired by this company
        company = db.query(Company).filter(Company.owner_user_id == current_user.id).first()
        if not company:
            return []
        # Get vouchers hired by this company
        hired_voucher_ids = db.query(InternshipVoucher.id).filter(
            InternshipVoucher.hired_by_company_id == company.id
        ).all()
        hired_voucher_ids = [v[0] for v in hired_voucher_ids]

        if not hired_voucher_ids:
            return []

        # Get attendance for these voucher users
        query = db.query(InternshipAttendance).filter(
            InternshipAttendance.user_id.in_(
                db.query(InternshipVoucher.buyer_user_id).filter(
                    InternshipVoucher.id.in_(hired_voucher_ids)
                )
            )
        )
        if date_from:
            query = query.filter(InternshipAttendance.attended_at >= date_from.date() if hasattr(date_from, 'date') else date_from)
        if date_to:
            query = query.filter(InternshipAttendance.attended_at <= date_to.date() if hasattr(date_to, 'date') else date_to)
        return query.all()

    raise HTTPException(status_code=400, detail=f"Invalid section: {section}")


def serialize_item(item, section: str, db: Session) -> dict:
    """Serialize a database item to a dictionary for export (enhanced with more columns)."""
    if section == "users":
        return {
            "id": item.id,
            "user_login": item.user_login,
            "user_email": item.user_email,
            "display_name": item.display_name,
            "role": item.role,
            "is_active": item.is_active,
            "is_verified": item.is_verified,
            "last_login": datetime_serializer(item.last_login) if hasattr(item, 'last_login') and item.last_login else "N/A",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "students":
        profile = item.profile if hasattr(item, 'profile') else None
        # Get enrollment count
        enrollment_count = db.query(Enrollment).filter(Enrollment.user_id == item.id).count()
        return {
            "id": item.id,
            "user_login": item.user_login,
            "user_email": item.user_email,
            "display_name": item.display_name,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "phone": profile.phone if profile else "",
            "city": profile.city if profile else "",
            "last_login": datetime_serializer(item.last_login) if hasattr(item, 'last_login') and item.last_login else "N/A",
            "enrollment_count": enrollment_count,
            "is_active": item.is_active,
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "instructors":
        instructor_profile = item.instructor_profile if hasattr(item, 'instructor_profile') else None
        # Get course count and average rating
        course_count = db.query(Course).filter(Course.post_author == item.id).count()
        courses = db.query(Course).filter(Course.post_author == item.id).all()
        avg_rating = sum(c.average_rating or 0 for c in courses) / len(courses) if courses else 0
        avg_rating = round(avg_rating, 2) if avg_rating else 0

        # Get profile bio and designation from InstructorProfile
        bio = ""
        designation = ""
        if instructor_profile:
            bio = getattr(instructor_profile, 'instructor_bio', '')
            designation = getattr(instructor_profile, 'instructor_designation', '')

        return {
            "id": item.id,
            "user_login": item.user_login,
            "user_email": item.user_email,
            "display_name": item.display_name,
            "first_name": instructor_profile.first_name if instructor_profile and hasattr(instructor_profile, 'first_name') else "",
            "last_name": instructor_profile.last_name if instructor_profile and hasattr(instructor_profile, 'last_name') else "",
            "designation": designation,
            "bio": bio,
            "expertise": "",  # Would need a separate expertise table or field
            "course_count": course_count,
            "average_rating": avg_rating,
            "is_active": item.is_active,
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "spocs":
        profile = item.profile if hasattr(item, 'profile') else None
        return {
            "id": item.id,
            "user_login": item.user_login,
            "user_email": item.user_email,
            "display_name": item.display_name,
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "college_name": "",  # Would need a separate field or relationship
            "designation": profile.designation if profile else "",
            "phone": profile.phone if profile else "",
            "city": profile.city if profile else "",
            "is_active": item.is_active,
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "companies":
        # Get intern count (vouchers hired by this company)
        intern_count = db.query(InternshipVoucher).filter(
            InternshipVoucher.hired_by_company_id == item.id
        ).count()
        # Get active interest count
        from app.models.company import CompanyInterest
        active_interests = db.query(CompanyInterest).filter(
            CompanyInterest.company_id == item.id,
            CompanyInterest.status == 'interested'
        ).count()
        return {
            "id": item.id,
            "name": item.name,
            "slug": item.slug,
            "website": item.website,
            "industry": item.industry,
            "team_size": item.team_size,
            "contact_email": item.contact_email,
            "contact_phone": item.contact_phone,
            "approval_status": "Approved" if item.is_approved else "Pending",
            "intern_count": intern_count,
            "active_internships": active_interests,  # Using active interests as proxy
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "courses":
        # Get author name
        author = db.query(User).filter(User.id == item.post_author).first()
        return {
            "id": item.id,
            "post_title": item.post_title,
            "post_author": item.post_author,
            "author_name": author.display_name if author else "N/A",
            "course_price": datetime_serializer(item.course_price),
            "sale_price": datetime_serializer(item.course_sale_price) if hasattr(item, 'course_sale_price') and item.course_sale_price else "0",
            "course_price_type": item.course_price_type,
            "course_level": item.course_level,
            "course_category": item.course_category,
            "post_status": item.post_status,
            "total_enrollments": item.total_enrollments or 0,
            "average_rating": round(item.average_rating, 2) if item.average_rating else 0,
            "review_count": item.total_reviews if hasattr(item, 'total_reviews') else 0,
            "course_language": item.course_language,
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "blogs":
        author = item.author if hasattr(item, 'author') else None
        return {
            "id": item.id,
            "title": item.title,
            "slug": item.slug,
            "author_id": item.author_id,
            "author_email": author.user_email if author else "",
            "status": item.status,
            "category": item.category or "",
            "view_count": item.view_count,
            "published_at": datetime_serializer(item.post_date) if hasattr(item, 'post_date') and item.post_date else "",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "orders":
        user = db.query(User).filter(User.id == item.user_id).first()
        # Get payment info
        payment = db.query(Payment).filter(Payment.order_id == item.id).first()

        # The Order row has no payment_status column — the settlement state lives
        # on its Payment; fall back to the order's own workflow status.
        def _enum_value(value):
            return str(value.value) if hasattr(value, "value") else str(value or "")

        payment_status = (
            _enum_value(payment.payment_status) if payment is not None
            else _enum_value(item.order_status)
        )

        return {
            "id": item.id,
            "order_id": item.order_key or f"ORD-{item.id}",
            "user_id": item.user_id,
            "user_email": user.user_email if user else "",
            "total_amount": str(item.total_amount),
            "currency": item.currency or "INR",
            "payment_method": item.payment_method or (payment.payment_method if payment else "") or "razorpay",
            "payment_status": payment_status,
            "transaction_id": item.transaction_id or (payment.gateway_payment_id if payment else "") or "",
            "coupon_used": "",  # Would need to join with coupon usage
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "certificates":
        # Get user and course info for IssuedCertificate
        user = db.query(User).filter(User.id == item.user_id).first()
        course = db.query(Course).filter(Course.id == item.course_id).first()
        return {
            "id": item.id,
            "certificate_id": item.secure_certificate_id or str(item.certificate_id),
            "user_id": item.user_id,
            "user_email": user.user_email if user else "",
            "course_id": item.course_id,
            "course_title": course.post_title if course else "N/A",
            "issued_at": datetime_serializer(item.completion_date) if hasattr(item, 'completion_date') and item.completion_date else datetime_serializer(item.created_at),
            "expiry_date": datetime_serializer(item.expires_at) if hasattr(item, 'expires_at') and item.expires_at else "",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "enrollments":
        student = db.query(User).filter(User.id == item.user_id).first()
        course = db.query(Course).filter(Course.id == item.course_id).first()
        return {
            "id": item.id,
            "user_id": item.user_id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "course_id": item.course_id,
            "course_title": course.post_title if course else "N/A",
            "enrollment_status": item.enrollment_status or "",
            "course_progress_percentage": item.course_progress_percentage or 0,
            "enrollment_date": datetime_serializer(item.enrollment_date) if item.enrollment_date else "",
            "completion_date": datetime_serializer(item.completion_date) if item.completion_date else "",
            "created_at": datetime_serializer(item.created_at) if item.created_at else ""
        }

    elif section == "reviews":
        course = db.query(Course).filter(Course.id == item.course_id).first()
        instructor = db.query(User).filter(User.id == item.instructor_id).first()
        student = db.query(User).filter(User.id == item.student_id).first()
        return {
            "id": item.id,
            "course_id": item.course_id,
            "course_title": course.post_title if course else "N/A",
            "instructor_id": item.instructor_id,
            "instructor_name": instructor.display_name if instructor else "N/A",
            "student_id": item.student_id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "rating": item.rating,
            "review_title": item.review_title or "",
            "review_content": item.review_content or "",
            "is_private": item.is_private,
            "created_at": datetime_serializer(item.created_at) if item.created_at else ""
        }

    elif section == "cohorts":
        from app.models.cohort import College, CohortMembership
        college = db.query(College).filter(College.id == item.college_id).first() if item.college_id else None
        course = db.query(Course).filter(Course.id == item.course_id).first() if item.course_id else None
        spoc = db.query(User).filter(User.id == item.spoc_user_id).first()
        student_count = db.query(CohortMembership).filter(CohortMembership.cohort_id == item.id).count()
        return {
            "id": item.id,
            "name": item.name,
            "slug": item.slug or "",
            "college_id": item.college_id,
            "college_name": college.name if college else "N/A",
            "course_id": item.course_id,
            "course_title": course.post_title if course else "N/A",
            "spoc_user_id": item.spoc_user_id,
            "spoc_name": spoc.display_name if spoc else "N/A",
            "max_students": item.max_students or 0,
            "student_count": student_count,
            "starts_on": datetime_serializer(item.starts_on) if item.starts_on else "",
            "ends_on": datetime_serializer(item.ends_on) if item.ends_on else "",
            "is_active": item.is_active,
            "created_at": datetime_serializer(item.created_at) if item.created_at else ""
        }

    elif section == "lessons":
        course = db.query(Course).filter(Course.id == item.post_parent).first()
        return {
            "id": item.id,
            "post_title": item.post_title,
            "course_id": item.post_parent,
            "course_title": course.post_title if course else "N/A",
            "menu_order": item.menu_order or 0,
            "post_type": item.post_type or "lesson",
            "lesson_video_duration": item.lesson_video_duration or "",
            "lesson_video_source": item.lesson_video_source or "",
            "post_status": item.post_status or "",
            "created_at": datetime_serializer(item.created_at) if item.created_at else ""
        }

    elif section == "quizzes":
        from app.models.quiz import QuizQuestion
        course = db.query(Course).filter(Course.id == item.post_parent).first()
        question_count = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == item.id).count()
        return {
            "id": item.id,
            "post_title": item.post_title,
            "course_id": item.post_parent,
            "course_title": course.post_title if course else "N/A",
            "question_count": question_count,
            "quiz_passing_grade": item.quiz_passing_grade or 0,
            "quiz_time_limit": item.quiz_time_limit or 0,
            "post_status": item.post_status or "",
            "created_at": datetime_serializer(item.created_at) if item.created_at else ""
        }

    elif section == "internship_requests":
        company = db.query(Company).filter(Company.id == item.company_id).first()
        requester = db.query(User).filter(User.id == item.requested_by).first()
        return {
            "id": item.id,
            "title": item.title,
            "company_id": item.company_id,
            "company_name": company.name if company else "N/A",
            "requested_by": item.requested_by,
            "requester_name": requester.display_name if requester else "N/A",
            "intern_count": item.intern_count or 0,
            "start_date": datetime_serializer(item.start_date) if item.start_date else "",
            "end_date": datetime_serializer(item.end_date) if item.end_date else "",
            "status": item.status or "",
            "reviewed_at": datetime_serializer(item.reviewed_at) if item.reviewed_at else "",
            "created_at": datetime_serializer(item.created_at) if item.created_at else ""
        }

    elif section == "coupons":
        # Get usage count from the model
        used_count = item.usage_count if hasattr(item, 'usage_count') else 0
        usage_limit = item.usage_limit if hasattr(item, 'usage_limit') else "Unlimited"
        return {
            "id": item.id,
            "code": item.code,
            "discount_type": item.discount_type,
            "discount_value": str(item.discount_value),
            "max_uses": str(usage_limit) if usage_limit != "Unlimited" else "Unlimited",
            "used_count": used_count,
            "is_active": item.is_active,
            "valid_from": datetime_serializer(item.valid_from) if item.valid_from else "",
            "valid_until": datetime_serializer(item.valid_until) if item.valid_until else "",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "internships":
        spoc = db.query(User).filter(User.id == item.spoc_user_id).first()
        cohort = db.query(Cohort).filter(Cohort.id == item.cohort_id).first()

        # Get students enrolled via vouchers
        vouchers = db.query(InternshipVoucher).filter(InternshipVoucher.internship_id == item.id).all()
        student_count = len(vouchers)

        # Get student details
        student_names = []
        student_emails = []
        for v in vouchers:
            student = db.query(User).filter(User.id == v.buyer_user_id).first()
            if student:
                student_names.append(student.display_name)
                student_emails.append(student.user_email)

        return {
            "id": item.id,
            "title": item.title,
            "slug": item.slug,
            "price": str(item.price) if item.price else "0",
            "is_published": "Yes" if item.is_published else "No",
            "student_count": student_count,
            "student_names": " | ".join(student_names) if student_names else "No students",
            "student_emails": " | ".join(student_emails) if student_emails else "No emails",
            "spoc_id": item.spoc_user_id,
            "spoc_name": spoc.display_name if spoc else "N/A",
            "spoc_email": spoc.user_email if spoc else "N/A",
            "cohort_id": item.cohort_id,
            "cohort_name": cohort.name if cohort else "N/A",
            "description": item.description[:300] + "..." if item.description and len(item.description) > 300 else (item.description or ""),
            "created_at": datetime_serializer(item.created_at),
            "updated_at": datetime_serializer(item.updated_at)
        }

    elif section == "internship_roster":
        """Export individual student enrollment records from vouchers."""
        # Get student
        student = db.query(User).filter(User.id == item.buyer_user_id).first()
        if not student:
            return None  # Skip if student not found

        # Get internship
        internship = db.query(Internship).filter(Internship.id == item.internship_id).first()

        # Get course enrollment if redeemed
        course_progress = "0%"
        completed_status = "Not Started"
        enrollment_date = None

        if item.redeemed_on_course_id:
            enrollment = db.query(Enrollment).filter(
                Enrollment.user_id == item.buyer_user_id,
                Enrollment.course_id == item.redeemed_on_course_id
            ).first()
            if enrollment:
                course_progress = f"{enrollment.course_progress_percentage or 0}"
                completed_status = enrollment.enrollment_status.replace('_', ' ').title()
                enrollment_date = datetime_serializer(enrollment.enrollment_date) if enrollment.enrollment_date else "N/A"

        # Count certificates issued
        cert_count = db.query(IssuedCertificate).filter(
            IssuedCertificate.user_id == item.buyer_user_id
        ).count()

        # Count attendance days
        attendance_days = 0
        attendance_records = db.query(InternshipAttendance).filter(
            InternshipAttendance.internship_id == item.internship_id,
            InternshipAttendance.user_id == item.buyer_user_id
        ).all()
        if attendance_records:
            # Count present days
            attendance_days = sum(1 for a in attendance_records if a.status == "present")
        attendance_display = f"{attendance_days} days"

        # Get hired by company
        hired_by = "N/A"
        if item.hired_by_company_id:
            company = db.query(Company).filter(Company.id == item.hired_by_company_id).first()
            if company:
                hired_by = company.name

        return {
            "student_name": student.display_name,
            "student_email": student.user_email,
            "voucher_code": item.code,
            "voucher_status": item.status.title(),
            "internship_title": internship.title if internship else "N/A",
            "course_progress": course_progress,
            "completed_status": completed_status,
            "certificates_issued": str(cert_count),
            "attendance_days": attendance_display,
            "hired_by_company": hired_by,
            "enrollment_date": enrollment_date or format_date_readable(item.created_at),
            "redeemed_date": format_date_readable(item.redeemed_at) if item.redeemed_at else "Not redeemed"
        }

    # Role-scoped sections
    elif section == "instructor_courses":
        return {
            "id": item.id,
            "post_title": item.post_title,
            "course_category": item.course_category or "",
            "course_level": item.course_level,
            "course_price": str(item.course_price) if item.course_price else "0",
            "sale_price": str(item.course_sale_price) if hasattr(item, 'course_sale_price') and item.course_sale_price else "0",
            "total_enrollments": item.total_enrollments or 0,
            "average_rating": round(item.average_rating, 2) if item.average_rating else 0,
            "review_count": item.total_reviews if hasattr(item, 'total_reviews') else 0,
            "post_status": item.post_status,
            "course_language": item.course_language or "English",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "instructor_students":
        student = db.query(User).filter(User.id == item.user_id).first()
        course = db.query(Course).filter(Course.id == item.course_id).first()
        return {
            "id": item.id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "course_title": course.post_title if course else "N/A",
            "enrollment_date": datetime_serializer(item.enrollment_date) if item.enrollment_date else "N/A",
            "course_progress": f"{item.course_progress_percentage or 0}%",
            "completion_status": item.enrollment_status.replace('_', ' ').title() if item.enrollment_status else "Not Started",
            "last_accessed": datetime_serializer(item.last_accessed) if hasattr(item, 'last_accessed') and item.last_accessed else "N/A"
        }

    elif section in ("instructor_quiz_results", "student_quiz_results"):
        # QuizAttempt columns: earned_marks / total_marks / attempt_ended_at, and
        # the quiz title lives on Quiz.post_title (WooCommerce-style naming).
        from app.models.quiz import Quiz as QuizModel

        student = db.query(User).filter(User.id == item.user_id).first()
        quiz = db.query(QuizModel).filter(QuizModel.id == item.quiz_id).first()
        course = db.query(Course).filter(Course.id == item.course_id).first()
        earned = float(item.earned_marks or 0)
        total = float(item.total_marks or 0)
        percentage = (earned / total * 100) if total > 0 else 0
        row = {
            "id": item.attempt_id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "course_title": course.post_title if course else "N/A",
            "quiz_title": quiz.post_title if quiz else "Quiz",
            "score": f"{earned:g}",
            "total_marks": f"{total:g}",
            "percentage": f"{percentage:.1f}%",
            "completed_at": datetime_serializer(item.attempt_ended_at) if item.attempt_ended_at else "N/A"
        }
        if section == "student_quiz_results":
            # A learner reading their own report doesn't need their own name back.
            for key in ("student_name", "student_email"):
                row.pop(key)
            row["result"] = "Passed" if percentage >= (quiz.quiz_passing_grade if quiz else 80) else "Not passed"
        return row

    elif section in ("instructor_assignment_results", "student_assignment_results"):
        from app.models.assignment import Assignment as AssignmentModel

        student = db.query(User).filter(User.id == item.user_id).first()
        assignment = db.query(AssignmentModel).filter(AssignmentModel.id == item.assignment_id).first()
        course = db.query(Course).filter(Course.id == assignment.course_id).first() if assignment else None
        status = item.status.value if hasattr(item.status, 'value') else str(item.status or "")
        row = {
            "id": item.id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "course_title": course.post_title if course else "N/A",
            "assignment_title": assignment.title if assignment else "Assignment",
            "status": status.replace('_', ' ').title(),
            "grade": str(item.grade) if item.grade is not None else "N/A",
            "submitted_at": datetime_serializer(item.submitted_at) if item.submitted_at else "N/A",
            # The model stores the review timestamp as graded_at.
            "reviewed_at": datetime_serializer(item.graded_at) if item.graded_at else "N/A"
        }
        if section == "student_assignment_results":
            for key in ("student_name", "student_email"):
                row.pop(key)
        return row

    elif section == "student_courses":
        course = db.query(Course).filter(Course.id == item.course_id).first()
        instructor = db.query(User).filter(User.id == course.post_author).first() if course else None
        return {
            "id": item.id,
            "course_title": course.post_title if course else "N/A",
            "instructor_name": instructor.display_name if instructor else "N/A",
            "enrollment_date": format_date_readable(item.enrollment_date),
            "course_progress": f"{item.course_progress_percentage or 0}%",
            "status": item.enrollment_status.replace('_', ' ').title() if item.enrollment_status else "Not Started",
            "completion_date": format_date_readable(item.completion_date) if item.completion_date else "—"
        }

    elif section == "student_certificates":
        course = db.query(Course).filter(Course.id == item.course_id).first()
        return {
            "id": item.id,
            "certificate_id": item.secure_certificate_id or str(item.certificate_id),
            "course_title": course.post_title if course else "N/A",
            "completion_date": format_date_readable(item.completion_date),
            "issued_at": format_date_readable(item.created_at),
            "verification_code": item.certificate_hash or "",
            "status": "Valid" if item.is_valid else "Revoked"
        }

    elif section == "spoc_students":
        profile = item.profile if hasattr(item, 'profile') else None
        # Get enrolled courses
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == item.id).all()
        enrolled_courses = [e.course.post_title for e in enrollments if e.course]
        return {
            "id": item.id,
            "student_name": item.display_name,
            "student_email": item.user_email,
            "phone": profile.phone if profile else "",
            "city": profile.city if profile else "",
            "enrolled_courses": ", ".join(enrolled_courses) if enrolled_courses else "None",
            "enrollment_count": len(enrollments),
            "is_active": item.is_active,
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "spoc_internships":
        vouchers = db.query(InternshipVoucher).filter(InternshipVoucher.internship_id == item.id).all()
        return {
            "id": item.id,
            "internship_title": item.title,
            "company_name": "Various",  # Internships aren't tied to a single company
            "stipend": str(item.price) if item.price else "0",
            "assigned_students": len(vouchers),
            "status": "Active" if item.is_published else "Inactive",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "spoc_placements":
        student = db.query(User).filter(User.id == item.buyer_user_id).first()
        company = db.query(Company).filter(Company.id == item.hired_by_company_id).first()
        internship = db.query(Internship).filter(Internship.id == item.internship_id).first()
        return {
            "id": item.id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "company_name": company.name if company else "N/A",
            "position": internship.title if internship else "N/A",
            "stipend": str(internship.price) if internship and internship.price else "N/A",
            "placed_date": datetime_serializer(item.hired_by_override_at) if item.hired_by_override_at else "N/A"
        }

    elif section == "spoc_blogs":
        author = item.author if hasattr(item, 'author') else None
        return {
            "id": item.id,
            "title": item.title,
            "slug": item.slug,
            "author_id": item.author_id,
            "author_email": author.user_email if author else "",
            "status": item.status,
            "category": item.category or "",
            "view_count": item.view_count,
            "published_at": datetime_serializer(item.post_date) if hasattr(item, 'post_date') and item.post_date else "",
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "company_positions":
        candidate = db.query(User).filter(User.id == item.candidate_user_id).first()
        return {
            "id": item.id,
            "title": "Position of Interest",  # CompanyInterest doesn't have title
            "stipend": "N/A",
            "required_skills": "N/A",
            "applicants_count": 1,
            "status": item.status.title(),
            "posted_date": datetime_serializer(item.created_at)
        }

    elif section == "company_interns":
        intern = db.query(User).filter(User.id == item.buyer_user_id).first()
        internship = db.query(Internship).filter(Internship.id == item.internship_id).first()
        # Get attendance percentage
        attendance_records = db.query(InternshipAttendance).filter(
            InternshipAttendance.internship_id == item.internship_id,
            InternshipAttendance.user_id == item.buyer_user_id
        ).all()
        present_days = sum(1 for a in attendance_records if a.status == "present")
        attendance_pct = (present_days / len(attendance_records) * 100) if attendance_records else 0
        return {
            "id": item.id,
            "intern_name": intern.display_name if intern else "N/A",
            "intern_email": intern.user_email if intern else "N/A",
            "college_name": "N/A",  # Would need profile join
            "position_title": internship.title if internship else "N/A",
            "join_date": datetime_serializer(item.created_at),
            "attendance_percentage": f"{attendance_pct:.1f}%",
            "status": item.status.title()
        }

    elif section == "company_performance":
        user = db.query(User).filter(User.id == item.user_id).first()
        internship = db.query(Internship).filter(Internship.id == item.internship_id).first()
        # Get company for this user
        voucher = db.query(InternshipVoucher).filter(
            InternshipVoucher.buyer_user_id == item.user_id,
            InternshipVoucher.internship_id == item.internship_id
        ).first()
        company = None
        reviewer_name = "N/A"
        if voucher and voucher.hired_by_company_id:
            company = db.query(Company).filter(Company.id == voucher.hired_by_company_id).first()
        if item.marked_by:
            marker = db.query(User).filter(User.id == item.marked_by).first()
            reviewer_name = marker.display_name if marker else "N/A"
        return {
            "id": item.id,
            "intern_name": user.display_name if user else "N/A",
            "intern_email": user.user_email if user else "N/A",
            "position_title": internship.title if internship else "N/A",
            "rating": "N/A",  # Attendance doesn't have rating
            "feedback": item.notes or "",
            "review_date": datetime_serializer(item.attended_at) if item.attended_at else "N/A",
            "reviewer_name": reviewer_name
        }

    return {}


# Public endpoints (no authentication required)
@router.get("/templates/{section}")
async def download_public_template(section: str):
    """
    Public endpoint to download Excel template file for import.

    Returns an Excel file with headers for the specified section.
    No authentication required - accessible to all users.
    """
    if not PANDAS_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Excel export requires pandas. Install with: pip install pandas openpyxl"
        )

    valid_sections = list(CSV_SCHEMAS.keys())
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    schema = CSV_SCHEMAS[section]

    # Create Excel file with headers and example row
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df = pd.DataFrame([schema["example"]], columns=schema["columns"])
        df.to_excel(writer, index=False, sheet_name='Template')

        # Get workbook and worksheet for styling
        workbook = writer.book
        worksheet = writer.sheets['Template']

        if OPENPYXL_STYLES_AVAILABLE:
            # Style header row
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            for col_num, column in enumerate(schema["columns"], 1):
                cell = worksheet.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = thin_border

            # Style example row
            for row_num in range(2, 3):
                for col_num in range(1, len(schema["columns"]) + 1):
                    cell = worksheet.cell(row=row_num, column=col_num)
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical='center')

            # Auto-adjust column widths
            for col_num, column in enumerate(schema["columns"], 1):
                max_length = max(len(str(column)), len(str(schema["example"][col_num - 1])))
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[get_column_letter(col_num)].width = adjusted_width

    output.seek(0)

    filename = f"{section}_template.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/admin/export/{section}")
async def export_data(
    section: str,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
    format: str = Query("csv", description="Export format: csv, excel, or pdf"),
    status: Optional[str] = Query(None, description="Filter by status (active/inactive, approved/pending, published/draft)"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in text fields")
):
    """
    Export data as CSV, Excel, or PDF file.

    Sections: users, students, instructors, spocs, companies, courses, blogs, dashboard
    Formats: csv, excel, pdf
    """
    valid_sections = admin_export_sections()
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    if format not in ["csv", "excel", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'csv', 'excel', or 'pdf'"
        )

    if format == "excel" and not PANDAS_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="Excel export requires pandas. Install: pip install pandas openpyxl"
        )

    if format == "pdf" and not REPORTLAB_AVAILABLE:
        raise HTTPException(
            status_code=400,
            detail="PDF export requires reportlab. Install: pip install reportlab"
        )

    try:
        # Handle dashboard export separately - use summary format
        if section == "dashboard":
            from app.models.user import User
            from app.models.course import Course
            from app.models.enrollment import Enrollment

            # Get dashboard stats
            total_users = db.query(User).count()
            total_students = db.query(User).filter(User.role == "student").count()
            total_instructors = db.query(User).filter(User.role == "instructor").count()
            total_courses = db.query(Course).count()
            published_courses = db.query(Course).filter(Course.post_status == "published").count()
            total_enrollments = db.query(Enrollment).count()

            # Format as horizontal summary data for better readability
            dashboard_summary = {
                "Total Users": total_users,
                "Total Students": total_students,
                "Total Instructors": total_instructors,
                "Total Courses": total_courses,
                "Published Courses": published_courses,
                "Total Enrollments": total_enrollments,
            }

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            if format == "pdf":
                # Custom portrait PDF for the dashboard — same brand furniture as
                # every other report, but a metric list rather than a data table.
                from app.services.report_theme import (
                    get_theme, make_page_decorator, register_fonts, top_margin_for,
                    PALETTE,
                )

                theme = get_theme("admin")
                font, font_bold = register_fonts()

                output = io.BytesIO()
                doc = SimpleDocTemplate(
                    output,
                    pagesize=A4,
                    topMargin=top_margin_for(theme),
                    bottomMargin=0.75*inch,
                    leftMargin=0.6*inch,
                    rightMargin=0.6*inch,
                    title="Dashboard Report",
                    author=BRAND_INFO['name'],
                )
                decorate = make_page_decorator(theme, subtitle="Dashboard Report")

                elements = []
                styles = getSampleStyleSheet()

                elements.append(Paragraph(theme.eyebrow, ParagraphStyle(
                    'DashEyebrow', parent=styles['Normal'], fontSize=7.5,
                    fontName=font_bold, textColor=theme.accent, spaceAfter=3,
                )))
                elements.append(Paragraph("Dashboard Report", ParagraphStyle(
                    'DashboardTitle', parent=styles['Heading1'], fontSize=22,
                    fontName=font_bold, textColor=theme.primary, spaceAfter=4,
                    alignment=TA_LEFT,
                )))
                elements.append(Paragraph(
                    f"Generated {datetime.now().strftime('%d %b %Y, %H:%M')}",
                    ParagraphStyle(
                        'DateStyle', parent=styles['Normal'], fontSize=9,
                        fontName=font, textColor=colors.HexColor(PALETTE['muted']),
                    )
                ))
                elements.append(Spacer(0, 0.3*inch))

                # Stats table with better formatting
                table_data = [["Metric", "Count"]]
                for label, value in dashboard_summary.items():
                    table_data.append([label, str(value)])

                table = Table(table_data, colWidths=[4.3*inch, 2.1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), theme.table_header_bg),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), font_bold),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('TOPPADDING', (0, 0), (-1, 0), 12),
                    ('LINEBELOW', (0, 0), (-1, 0), 1.5, theme.accent),
                    ('FONTNAME', (0, 1), (-1, -1), font),
                    ('FONTSIZE', (0, 1), (-1, -1), 10.5),
                    ('TOPPADDING', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(PALETTE['hairline'])),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, theme.tint]),
                ]))
                elements.append(table)

                doc.build(elements, onFirstPage=decorate, onLaterPages=decorate)

                filename = f"dashboard_report_{timestamp}.pdf"
                return StreamingResponse(
                    io.BytesIO(output.getvalue()),
                    media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

            elif format == "excel":
                # Excel with better formatting
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Summary sheet
                    df_summary = pd.DataFrame(list(dashboard_summary.items()), columns=['Metric', 'Count'])
                    df_summary.to_excel(writer, sheet_name='Dashboard', index=False)

                    if OPENPYXL_STYLES_AVAILABLE:
                        workbook = writer.book
                        worksheet = writer.sheets['Dashboard']

                        # Header styling
                        header_font = Font(bold=True, color='FFFFFF', size=12)
                        header_fill = PatternFill(start_color='1E40AF', end_color='1E40AF', fill_type='solid')
                        header_align = Alignment(horizontal='left', vertical='center')

                        for cell in worksheet[1]:
                            cell.font = header_font
                            cell.fill = header_fill
                            cell.alignment = header_align

                        # Column widths
                        worksheet.column_dimensions['A'].width = 25
                        worksheet.column_dimensions['B'].width = 15

                output.seek(0)
                filename = f"dashboard_report_{timestamp}.xlsx"
                return StreamingResponse(
                    output,
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

            else:  # csv - more readable format
                output = io.StringIO()
                output.write(f"SashaInfinity LMS - Dashboard Report\n")
                output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                output.write(f"\n{'='*50}\n")
                for label, value in dashboard_summary.items():
                    # Pad label to 30 chars for alignment
                    output.write(f"{label:<30} : {value}\n")
                output.write(f"{'='*50}\n")

                csv_bytes = io.BytesIO()
                csv_bytes.write(b'\xef\xbb\xbf')  # UTF-8 BOM
                csv_bytes.write(output.getvalue().encode('utf-8'))
                csv_bytes.seek(0)
                filename = f"dashboard_report_{timestamp}.csv"
                return StreamingResponse(
                    csv_bytes,
                    media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

        items = get_section_query(db, section, status, date_from, date_to, search)

        # Build filters dict for export functions
        filters = {}
        if status:
            filters['status'] = status
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if search:
            filters['search'] = search

        schema = CSV_SCHEMAS[section]
        columns = schema["columns"]
        section_label = section.capitalize()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Handle empty data gracefully
        if not items:
            if format == "pdf":
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters)
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(
                    io.BytesIO(pdf_bytes),
                    media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )
            elif format == "excel":
                # Create empty Excel with headers
                df = pd.DataFrame(columns=[col.replace('_', ' ').title() for col in columns])
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(
                    io.BytesIO(excel_bytes),
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )
            else:
                csv_bytes = generate_csv([], columns, f"{section_label} Export", filters)
                filename = f"{section}_export_{timestamp}.csv"
                return StreamingResponse(
                    io.BytesIO(csv_bytes),
                    media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

        # Serialize items to dict format (with db session for enhanced data)
        rows = []
        for item in items:
            serialized = serialize_item(item, section, db)
            if serialized is not None:  # Skip None values (e.g., deleted students in internship_roster)
                rows.append(serialized)

        if format == "pdf":
            # Generate enhanced PDF
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters)
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        elif format == "excel":
            # Generate enhanced Excel
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(
                io.BytesIO(excel_bytes),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            # Generate enhanced CSV
            csv_bytes = generate_csv(rows, columns, f"{section_label} Export", filters)
            filename = f"{section}_export_{timestamp}.csv"
            return StreamingResponse(
                io.BytesIO(csv_bytes),
                media_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# Role-specific export endpoints
@router.get("/instructor/export/{section}")
async def export_instructor_data(
    section: str,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
    format: str = Query("excel", description="Export format: excel or pdf"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in text fields")
):
    """Export instructor-scoped data as Excel or PDF."""
    valid_sections = ["instructor_courses", "instructor_students", "instructor_quiz_results", "instructor_assignment_results"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}")
    if format not in ["excel", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")
    if format == "excel" and not PANDAS_AVAILABLE:
        raise HTTPException(status_code=400, detail="Excel export requires pandas. Install: pip install pandas openpyxl")
    if format == "pdf" and not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=400, detail="PDF export requires reportlab. Install: pip install reportlab")

    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        filters = {}
        if status: filters['status'] = status
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if search: filters['search'] = search

        schema = CSV_SCHEMAS[section]
        columns = schema["columns"]
        section_label = section.replace('_', ' ').title()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Handle empty data
        if not items:
            if format == "pdf":
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters, role="instructor")
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
            else:
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

        # Serialize items
        rows = []
        for item in items:
            serialized = serialize_item(item, section, db)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters, role="instructor")
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
        else:
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/spoc/export/{section}")
async def export_spoc_data(
    section: str,
    current_user: User = Depends(AuthService.require_spoc),
    db: Session = Depends(get_db),
    format: str = Query("excel", description="Export format: excel or pdf"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in text fields")
):
    """Export SPOC-scoped data as Excel or PDF."""
    valid_sections = ["spoc_students", "spoc_internships", "spoc_placements", "spoc_blogs"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}")
    if format not in ["excel", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")
    if format == "excel" and not PANDAS_AVAILABLE:
        raise HTTPException(status_code=400, detail="Excel export requires pandas. Install: pip install pandas openpyxl")
    if format == "pdf" and not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=400, detail="PDF export requires reportlab. Install: pip install reportlab")

    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        filters = {}
        if status: filters['status'] = status
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if search: filters['search'] = search

        schema = CSV_SCHEMAS[section]
        columns = schema["columns"]
        section_label = section.replace('_', ' ').title()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if not items:
            if format == "pdf":
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters, role="spoc")
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
            else:
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

        rows = []
        for item in items:
            serialized = serialize_item(item, section, db)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters, role="spoc")
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
        else:
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


def admin_export_sections() -> List[str]:
    """Sections the admin endpoints can actually serve.

    CSV_SCHEMAS also carries the role-scoped sections (instructor_*, spoc_*,
    company_*, student_*), which only get_role_section_query knows how to build.
    Listing them as valid here made the endpoint advertise sections it then
    rejected with "Invalid section".
    """
    role_prefixes = ("instructor_", "spoc_", "company_", "student_")
    return [s for s in CSV_SCHEMAS if not s.startswith(role_prefixes)]


STUDENT_EXPORT_SECTIONS = [
    "student_courses",
    "student_certificates",
    "student_quiz_results",
    "student_assignment_results",
]


@router.get("/student/export/{section}")
async def export_student_data(
    section: str,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
    format: str = Query("pdf", description="Export format: excel or pdf"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in text fields")
):
    """Export the signed-in learner's own records as Excel or PDF.

    Every section here is scoped to `current_user`, so any authenticated role can
    call it and only ever sees their own learning data.
    """
    if section not in STUDENT_EXPORT_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid sections: {', '.join(STUDENT_EXPORT_SECTIONS)}")
    if format not in ["excel", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")
    if format == "excel" and not PANDAS_AVAILABLE:
        raise HTTPException(status_code=400, detail="Excel export requires pandas. Install: pip install pandas openpyxl")
    if format == "pdf" and not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=400, detail="PDF export requires reportlab. Install: pip install reportlab")

    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        filters = {}
        if status: filters['status'] = status
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if search: filters['search'] = search

        columns = CSV_SCHEMAS[section]["columns"]
        section_label = section.replace('student_', '').replace('_', ' ').title()
        # The learner's report is addressed to them by name.
        title = f"{section_label} — {current_user.display_name or current_user.user_login}"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        rows = []
        for item in items:
            serialized = serialize_item(item, section, db)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, title, filters, role="student")
            filename = f"{section}_{timestamp}.pdf"
            return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

        excel_bytes = generate_excel(rows, columns, title, section[:31], filters)
        filename = f"{section}_{timestamp}.xlsx"
        return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/company/export/{section}")
async def export_company_data(
    section: str,
    current_user: User = Depends(AuthService.require_company),
    db: Session = Depends(get_db),
    format: str = Query("excel", description="Export format: excel or pdf"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter to date (ISO format)"),
    search: Optional[str] = Query(None, description="Search in text fields")
):
    """Export company-scoped data as Excel or PDF."""
    valid_sections = ["company_positions", "company_interns", "company_performance"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}")
    if format not in ["excel", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")
    if format == "excel" and not PANDAS_AVAILABLE:
        raise HTTPException(status_code=400, detail="Excel export requires pandas. Install: pip install pandas openpyxl")
    if format == "pdf" and not REPORTLAB_AVAILABLE:
        raise HTTPException(status_code=400, detail="PDF export requires reportlab. Install: pip install reportlab")

    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        filters = {}
        if status: filters['status'] = status
        if date_from: filters['date_from'] = date_from
        if date_to: filters['date_to'] = date_to
        if search: filters['search'] = search

        schema = CSV_SCHEMAS[section]
        columns = schema["columns"]
        section_label = section.replace('_', ' ').title()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if not items:
            if format == "pdf":
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters, role="company")
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
            else:
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

        rows = []
        for item in items:
            serialized = serialize_item(item, section, db)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters, role="company")
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(io.BytesIO(pdf_bytes), media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
        else:
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(io.BytesIO(excel_bytes), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/admin/import/{section}")
async def import_data(
    section: str,
    file: UploadFile = File(...),
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
    update_by_id: bool = Query(False, description="Update existing records by ID instead of creating new ones")
):
    """
    Import data from CSV/Excel file.

    Returns: success_count, error_count, errors list
    """
    valid_sections = list(CSV_SCHEMAS.keys())
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    success_count = 0
    error_count = 0
    errors = []

    try:
        content = await file.read()
        filename = file.filename.lower()

        # Read file based on extension
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content)) if PANDAS_AVAILABLE else None
            if df is None:
                content_str = content.decode('utf-8')
                reader = csv.DictReader(io.StringIO(content_str))
                rows = list(reader)
            else:
                rows = df.to_dict('records')
        elif filename.endswith(('.xlsx', '.xls')):
            if not PANDAS_AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="Excel import requires pandas. Install: pip install pandas openpyxl"
                )
            df = pd.read_excel(io.BytesIO(content))
            rows = df.to_dict('records')
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use CSV or Excel (.xlsx, .xls)"
            )

        schema = CSV_SCHEMAS[section]
        required_columns = set(schema["columns"])

        # B7 (2026-09-04): the whole import is now ONE transaction. Every
        # row is processed in this loop (writes flushed, not committed) so
        # DB-uniqueness lookups within the loop still see earlier rows in
        # the same file; nothing is committed until every row has been
        # processed. If any row failed, the whole import is rolled back and
        # rejected with 400 listing every failing row — no partial writes.
        # A per-row failure still rolls back just that row's uncommitted
        # work (via db.rollback()) so a bad row's half-built object doesn't
        # poison the session for the rows after it, but the transaction as
        # a whole is abandoned once the loop finishes if any row failed.
        for idx, row in enumerate(rows, start=1):
            try:
                row = {k: v for k, v in row.items() if pd.notna(v)} if PANDAS_AVAILABLE else row

                if not required_columns.issubset(row.keys()):
                    missing = required_columns - set(row.keys())
                    errors.append({
                        "row": idx,
                        "error": f"Missing columns: {', '.join(missing)}"
                    })
                    error_count += 1
                    continue

                # Process based on section
                if section in ["users", "students", "instructors", "spocs"]:
                    user_id = row.get("id")
                    user = db.query(User).filter(User.id == user_id).first()

                    if update_by_id and user:
                        user.user_login = row.get("user_login", user.user_login)
                        user.user_email = row.get("user_email", user.user_email)
                        user.display_name = row.get("display_name", user.display_name)
                        user.is_active = row.get("is_active", user.is_active)
                        user.is_verified = row.get("is_verified", user.is_verified)
                    elif not user:
                        # Create new user
                        new_user = User(
                            user_login=row["user_login"],
                            user_email=row["user_email"],
                            display_name=row["display_name"],
                            role=section if section != "students" else "student",
                            is_active=row.get("is_active", True),
                            is_verified=row.get("is_verified", False),
                            user_pass="temp_password_123"  # Should be reset
                        )
                        db.add(new_user)
                        db.flush()
                        user = new_user

                    # Update profile for students/instructors/spocs
                    if section in ["students", "instructors", "spocs"]:
                        profile = user.profile
                        if not profile:
                            profile = UserProfile(user_id=user.id)
                            db.add(profile)
                            db.flush()

                        if "first_name" in row:
                            profile.first_name = row.get("first_name", "")
                        if "last_name" in row:
                            profile.last_name = row.get("last_name", "")
                        if "phone" in row:
                            profile.phone = row.get("phone", "")
                        if "city" in row:
                            profile.city = row.get("city", "")
                        if "designation" in row:
                            profile.designation = row.get("designation", "")
                        if "bio" in row and section == "instructors":
                            if hasattr(profile, 'bio'):
                                profile.bio = row.get("bio", "")

                    success_count += 1

                elif section == "companies":
                    company_id = row.get("id")
                    company = db.query(Company).filter(Company.id == company_id).first()

                    if update_by_id and company:
                        company.name = row.get("name", company.name)
                        company.slug = row.get("slug", company.slug)
                        company.website = row.get("website", company.website)
                        company.industry = row.get("industry", company.industry)
                        company.team_size = row.get("team_size", company.team_size)
                        company.contact_email = row.get("contact_email", company.contact_email)
                        company.contact_phone = row.get("contact_phone", company.contact_phone)
                        company.is_approved = row.get("is_approved", company.is_approved)
                    elif not company:
                        new_company = Company(
                            name=row["name"],
                            slug=row["slug"],
                            website=row.get("website", ""),
                            industry=row.get("industry", ""),
                            team_size=row.get("team_size", ""),
                            contact_email=row["contact_email"],
                            contact_phone=row.get("contact_phone", ""),
                            is_approved=row.get("is_approved", False),
                            owner_user_id=1  # Default to admin, should be overridden
                        )
                        db.add(new_company)
                        success_count += 1
                    else:
                        success_count += 1

                elif section == "courses":
                    course_id = row.get("id")
                    course = db.query(Course).filter(Course.id == course_id).first()

                    if update_by_id and course:
                        course.post_title = row.get("post_title", course.post_title)
                        course.course_price = row.get("course_price", course.course_price)
                        course.course_price_type = row.get("course_price_type", course.course_price_type)
                        course.course_level = row.get("course_level", course.course_level)
                        course.course_category = row.get("course_category", course.course_category)
                        course.post_status = row.get("post_status", course.post_status)
                    elif not course:
                        new_course = Course(
                            post_title=row["post_title"],
                            post_author=row.get("post_author", 1),
                            course_price=row.get("course_price", 0),
                            course_price_type=row.get("course_price_type", "free"),
                            course_level=row.get("course_level", "beginner"),
                            course_category=row.get("course_category", ""),
                            course_language=row.get("course_language", "English"),
                            post_status=row.get("post_status", "draft")
                        )
                        db.add(new_course)
                        success_count += 1
                    else:
                        success_count += 1

                elif section == "blogs":
                    blog_id = row.get("id")
                    blog = db.query(BlogPost).filter(BlogPost.id == blog_id).first()

                    if update_by_id and blog:
                        blog.title = row.get("title", blog.title)
                        blog.slug = row.get("slug", blog.slug)
                        blog.status = row.get("status", blog.status)
                        blog.category = row.get("category", blog.category)
                    elif not blog:
                        new_blog = BlogPost(
                            title=row["title"],
                            slug=row["slug"],
                            author_id=row.get("author_id", 1),
                            status=row.get("status", "DRAFT"),
                            category=row.get("category", ""),
                            content=row.get("content", "")
                        )
                        db.add(new_blog)
                        success_count += 1
                    else:
                        success_count += 1

                elif section == "coupons":
                    from app.models.coupon import DiscountType, CouponApplicability
                    coupon_id = row.get("id")
                    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()

                    # Validate required code field
                    code = row.get("code")
                    if not code or not str(code).strip():
                        errors.append({
                            "row": idx,
                            "error": "Missing required field: code"
                        })
                        error_count += 1
                        continue

                    # Parse discount_type safely
                    discount_type_str = row.get("discount_type", "percentage")
                    try:
                        discount_type = DiscountType(discount_type_str.lower())
                    except (ValueError, AttributeError):
                        discount_type = DiscountType.PERCENTAGE

                    # Parse applicability safely
                    applicability_str = row.get("applicability", "all_courses")
                    try:
                        applicability = CouponApplicability(applicability_str.lower())
                    except (ValueError, AttributeError):
                        applicability = CouponApplicability.ALL_COURSES

                    # Parse validity dates
                    from datetime import datetime
                    valid_from = None
                    valid_until = None
                    if row.get("valid_from"):
                        try:
                            valid_from = datetime.fromisoformat(str(row["valid_from"]).replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass
                    if row.get("valid_until"):
                        try:
                            valid_until = datetime.fromisoformat(str(row["valid_until"]).replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass

                    # Parse is_active
                    is_active = True
                    if row.get("is_active"):
                        is_active_str = str(row["is_active"]).lower()
                        is_active = is_active_str in ("true", "1", "yes", "active")

                    # Parse per_user_limit
                    per_user_limit = 1
                    if row.get("per_user_limit"):
                        try:
                            per_user_limit = int(row["per_user_limit"])
                            if per_user_limit < 1:
                                per_user_limit = 1
                        except (ValueError, TypeError):
                            per_user_limit = 1

                    # Parse minimum_purchase_amount
                    minimum_purchase_amount = 0
                    if row.get("minimum_purchase_amount"):
                        try:
                            minimum_purchase_amount = float(row["minimum_purchase_amount"])
                            if minimum_purchase_amount < 0:
                                minimum_purchase_amount = 0
                        except (ValueError, TypeError):
                            minimum_purchase_amount = 0

                    # Parse used_count
                    used_count = 0
                    if row.get("used_count"):
                        try:
                            used_count = int(row["used_count"])
                            if used_count < 0:
                                used_count = 0
                        except (ValueError, TypeError):
                            used_count = 0

                    if update_by_id and coupon:
                        coupon.code = code
                        coupon.discount_type = discount_type
                        coupon.discount_value = float(row.get("discount_value", coupon.discount_value))
                        coupon.applicability = applicability
                        coupon.usage_limit = int(row["max_uses"]) if row.get("max_uses") else coupon.usage_limit
                        coupon.per_user_limit = per_user_limit
                        coupon.minimum_purchase_amount = minimum_purchase_amount
                        coupon.usage_count = used_count
                        coupon.is_active = is_active
                        if valid_from:
                            coupon.valid_from = valid_from
                        if valid_until:
                            coupon.valid_until = valid_until
                        success_count += 1
                    elif not coupon:
                        new_coupon = Coupon(
                            code=code,
                            description=row.get("description", ""),
                            discount_type=discount_type,
                            discount_value=float(row.get("discount_value", 0)),
                            applicability=applicability,
                            usage_limit=int(row["max_uses"]) if row.get("max_uses") else None,
                            per_user_limit=per_user_limit,
                            minimum_purchase_amount=minimum_purchase_amount,
                            usage_count=used_count,
                            is_active=is_active,
                            valid_from=valid_from,
                            valid_until=valid_until,
                            created_by=row.get("created_by", 1)
                        )
                        db.add(new_coupon)
                        success_count += 1
                    else:
                        success_count += 1

                # Flush (not commit) — assigns PKs so later rows' uniqueness
                # lookups in this same file see earlier rows, without
                # finalizing anything until the whole file has validated.
                db.flush()

            except Exception as e:
                # db.rollback() resets the WHOLE session, discarding every
                # row flushed so far in this loop (not just this row's) —
                # that's fine: once any row fails, the import is rejected
                # in full regardless (see below), so there is nothing to
                # preserve. We keep scanning the remaining rows anyway
                # (each row's own flush is independent post-rollback) so
                # the error response lists every failing row in one pass
                # instead of forcing a fix-one-row-at-a-time retry loop.
                db.rollback()
                errors.append({
                    "row": idx,
                    "error": str(e)
                })
                error_count += 1

        if error_count:
            # No partial writes — nothing from this file was committed.
            return {
                "success_count": 0,
                "error_count": error_count,
                "errors": errors[:10],  # Limit errors in response
                "message": "Import rejected — no rows were written. Fix the listed row(s) and re-upload.",
            }

        db.commit()
        return {
            "success_count": success_count,
            "error_count": 0,
            "errors": [],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/admin/export/schema/{section}")
async def get_schema(section: str, current_user: User = Depends(AuthService.require_admin)):
    """
    Get CSV template/schema for a section.

    Returns column names and example data for building import files.
    """
    valid_sections = list(CSV_SCHEMAS.keys())
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    schema = CSV_SCHEMAS[section]

    return {
        "section": section,
        "columns": schema["columns"],
        "example": schema["example"],
        "description": f"CSV schema for {section} import/export",
        "formats": {
            "csv": ".csv files supported",
            "excel": ".xlsx, .xls files supported (requires pandas)"
        }
    }


@router.get("/admin/export/template/{section}")
async def download_template(section: str, current_user: User = Depends(AuthService.require_admin)):
    """
    Download Excel template file for import.

    Returns an Excel file with headers for the specified section.
    Users can fill this file and use it for import.
    """
    if not PANDAS_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="Excel export requires pandas. Install with: pip install pandas openpyxl"
        )

    valid_sections = list(CSV_SCHEMAS.keys())
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    schema = CSV_SCHEMAS[section]

    # Create Excel file with headers and example row
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df = pd.DataFrame([schema["example"]], columns=schema["columns"])
        df.to_excel(writer, index=False, sheet_name='Template')

        # Get workbook and worksheet for styling
        workbook = writer.book
        worksheet = writer.sheets['Template']

        if OPENPYXL_STYLES_AVAILABLE:
            # Style header row
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            for col_num, column in enumerate(schema["columns"], 1):
                cell = worksheet.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                cell.border = thin_border

            # Style example row
            for row_num in range(2, 3):
                for col_num in range(1, len(schema["columns"]) + 1):
                    cell = worksheet.cell(row=row_num, column=col_num)
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical='center')

            # Auto-adjust column widths
            for col_num, column in enumerate(schema["columns"], 1):
                max_length = max(len(str(column)), len(str(schema["example"][col_num - 1])))
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[get_column_letter(col_num)].width = adjusted_width

    output.seek(0)

    filename = f"{section}_template.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/admin/export/{section}/count")
async def get_export_count(
    section: str,
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get the count of records for a section with filters applied.
    Used to show record count before export.
    """
    valid_sections = admin_export_sections()
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    if section == "dashboard":
        return {"count": 6}  # Fixed number of metrics

    try:
        items = get_section_query(db, section, status, date_from, date_to, search)
        return {"count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get count: {str(e)}")


@router.get("/student/export/{section}/count")
async def get_student_export_count(
    section: str,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """Count the signed-in learner's own records for a section."""
    if section not in STUDENT_EXPORT_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid sections: {', '.join(STUDENT_EXPORT_SECTIONS)}")
    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        return {"count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get count: {str(e)}")


@router.get("/instructor/export/{section}/count")
async def get_instructor_export_count(
    section: str,
    current_user: User = Depends(AuthService.require_instructor),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get record count for instructor export section."""
    valid_sections = ["instructor_courses", "instructor_students", "instructor_quiz_results", "instructor_assignment_results"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section}")
    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        return {"count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get count: {str(e)}")


@router.get("/spoc/export/{section}/count")
async def get_spoc_export_count(
    section: str,
    current_user: User = Depends(AuthService.require_spoc),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get record count for SPOC export section."""
    valid_sections = ["spoc_students", "spoc_internships", "spoc_placements"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section}")
    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        return {"count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get count: {str(e)}")


@router.get("/company/export/{section}/count")
async def get_company_export_count(
    section: str,
    current_user: User = Depends(AuthService.require_company),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """Get record count for company export section."""
    valid_sections = ["company_positions", "company_interns", "company_performance"]
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section}")
    try:
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)
        return {"count": len(items)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get count: {str(e)}")
