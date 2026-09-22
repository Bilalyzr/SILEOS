# Role-Based Export/Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Export/Import panels to Instructor, SPOC, and Company dashboards with role-scoped data filtering.

**Architecture:** Extend existing `export_import.py` router with role-specific endpoints. Add role prop to `ExportImportPanel` component. Each role sees only their own data via WHERE clause filtering.

**Tech Stack:** FastAPI (backend), React/TypeScript (frontend), pandas/openpyxl/reportlab (exports)

---

## Task 1: Add role-scoped CSV schemas to backend

**Files:**
- Modify: `backend/app/routers/export_import.py`

- [ ] **Step 1: Add CSV schemas for role-specific sections**

Add to `CSV_SCHEMAS` dictionary after line 117:

```python
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
},
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/export_import.py
git commit -m "feat: add CSV schemas for role-based export sections"
```

---

## Task 2: Add role-scoped query functions to backend

**Files:**
- Modify: `backend/app/routers/export_import.py`

- [ ] **Step 1: Add role-specific query function**

Add after `get_section_query` function (after line 1015):

```python
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
        query = db.query(QuizAttempt).join(Quiz).join(Course).filter(Course.post_author == current_user.id)
        if date_from:
            query = query.filter(QuizAttempt.completed_at >= date_from)
        if date_to:
            query = query.filter(QuizAttempt.completed_at <= date_to)
        if search:
            query = query.join(User).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    elif section == "instructor_assignment_results":
        from app.models.assignment import Assignment, AssignmentSubmission
        query = db.query(AssignmentSubmission).join(Assignment).join(Course).filter(Course.post_author == current_user.id)
        if date_from:
            query = query.filter(AssignmentSubmission.submitted_at >= date_from)
        if date_to:
            query = query.filter(AssignmentSubmission.submitted_at <= date_to)
        if search:
            query = query.join(User).filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    # SPOC sections
    elif section == "spoc_students":
        from app.models.user import SPOCProfile
        spoc_profile = db.query(SPOCProfile).filter(SPOCProfile.user_id == current_user.id).first()
        if not spoc_profile or not spoc_profile.college_id:
            return []
        query = db.query(User).filter(User.role == "student").join(UserProfile).filter(
            UserProfile.college_id == spoc_profile.college_id
        )
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
        from app.models.user import SPOCProfile
        spoc_profile = db.query(SPOCProfile).filter(SPOCProfile.user_id == current_user.id).first()
        if not spoc_profile or not spoc_profile.college_id:
            return []
        query = db.query(Internship).filter(Internship.college_id == spoc_profile.college_id)
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
        from app.models.user import SPOCProfile
        spoc_profile = db.query(SPOCProfile).filter(SPOCProfile.user_id == current_user.id).first()
        if not spoc_profile or not spoc_profile.college_id:
            return []
        # Students from this college who were hired
        query = db.query(InternshipVoucher).join(User, User.id == InternshipVoucher.buyer_user_id).join(
            UserProfile, UserProfile.user_id == User.id
        ).filter(
            UserProfile.college_id == spoc_profile.college_id,
            InternshipVoucher.hired_by_company_id.isnot(None)
        )
        if date_from:
            query = query.filter(InternshipVoucher.hired_at >= date_from)
        if date_to:
            query = query.filter(InternshipVoucher.hired_at <= date_to)
        if search:
            query = query.filter(
                User.display_name.ilike(f"%{search}%") | User.user_email.ilike(f"%{search}%")
            )
        return query.all()

    # Company sections
    elif section == "company_positions":
        # Get company from current user
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        if not company:
            return []
        # Internships created by this company
        query = db.query(Internship).filter(Internship.company_id == company.id)
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

    elif section == "company_interns":
        # Users assigned to this company's internships
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        if not company:
            return []
        query = db.query(InternshipVoucher).join(Internship).filter(Internship.company_id == company.id)
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
        # Performance reviews for this company's interns
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        if not company:
            return []
        # This would need a performance review model - for now return internship attendance data
        query = db.query(InternshipAttendance).join(Internship).filter(Internship.company_id == company.id)
        if date_from:
            query = query.filter(InternshipAttendance.date >= date_from.date() if hasattr(date_from, 'date') else date_from)
        if date_to:
            query = query.filter(InternshipAttendance.date <= date_to.date() if hasattr(date_to, 'date') else date_to)
        return query.all()

    raise HTTPException(status_code=400, detail=f"Invalid section: {section}")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/export_import.py
git commit -m "feat: add role-scoped query functions for export"
```

---

## Task 3: Add role-scoped serialization functions

**Files:**
- Modify: `backend/app/routers/export_import.py`

- [ ] **Step 1: Add role-specific serialization function**

Add after `serialize_item` function (after line 1309):

```python
def serialize_role_item(item, section: str, db: Session, current_user: User) -> dict:
    """Serialize role-scoped items for export."""
    from app.models.quiz import Quiz
    from app.models.assignment import Assignment

    if section == "instructor_courses":
        return {
            "id": item.id,
            "post_title": item.post_title,
            "course_category": item.course_category or "",
            "course_level": item.course_level or "",
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
            "last_accessed": datetime_serializer(item.last_accessed_at) if hasattr(item, 'last_accessed_at') and item.last_accessed_at else "N/A"
        }

    elif section == "instructor_quiz_results":
        student = db.query(User).filter(User.id == item.user_id).first()
        quiz = db.query(Quiz).filter(Quiz.id == item.quiz_id).first()
        course = db.query(Course).filter(Course.id == quiz.course_id).first() if quiz else None
        percentage = round((item.score / item.total_marks * 100), 1) if item.total_marks > 0 else 0
        return {
            "id": item.id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "course_title": course.post_title if course else "N/A",
            "quiz_title": quiz.title if quiz else "N/A",
            "score": item.score,
            "total_marks": item.total_marks,
            "percentage": percentage,
            "completed_at": datetime_serializer(item.completed_at) if item.completed_at else "N/A"
        }

    elif section == "instructor_assignment_results":
        student = db.query(User).filter(User.id == item.user_id).first()
        assignment = db.query(Assignment).filter(Assignment.id == item.assignment_id).first()
        course = db.query(Course).filter(Course.id == assignment.course_id).first() if assignment else None
        return {
            "id": item.id,
            "student_name": student.display_name if student else "N/A",
            "student_email": student.user_email if student else "N/A",
            "course_title": course.post_title if course else "N/A",
            "assignment_title": assignment.title if assignment else "N/A",
            "status": item.status.replace('_', ' ').title() if item.status else "N/A",
            "grade": item.grade or "Not graded",
            "submitted_at": datetime_serializer(item.submitted_at) if item.submitted_at else "N/A",
            "reviewed_at": datetime_serializer(item.reviewed_at) if item.reviewed_at else "N/A"
        }

    elif section == "spoc_students":
        profile = item.profile if hasattr(item, 'profile') else None
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == item.id).all()
        courses = [db.query(Course).filter(Course.id == e.course_id).first() for e in enrollments]
        course_titles = [c.post_title for c in courses if c]
        return {
            "id": item.id,
            "student_name": item.display_name,
            "student_email": item.user_email,
            "phone": profile.phone if profile else "",
            "city": profile.city if profile else "",
            "enrolled_courses": ", ".join(course_titles) if course_titles else "None",
            "enrollment_count": len(enrollments),
            "is_active": item.is_active,
            "created_at": datetime_serializer(item.created_at)
        }

    elif section == "spoc_internships":
        company = db.query(Company).filter(Company.id == item.company_id).first()
        vouchers = db.query(InternshipVoucher).filter(InternshipVoucher.internship_id == item.id).count()
        return {
            "id": item.id,
            "internship_title": item.title,
            "company_name": company.name if company else "N/A",
            "stipend": str(item.price) if item.price else "0",
            "assigned_students": vouchers,
            "status": "active" if item.is_published else "inactive",
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
            "stipend": str(internship.price) if internship and internship.price else "0",
            "placed_date": format_date_readable(item.hired_at) if item.hired_at else "N/A"
        }

    elif section == "company_positions":
        vouchers = db.query(InternshipVoucher).filter(InternshipVoucher.internship_id == item.id).count()
        return {
            "id": item.id,
            "title": item.title,
            "stipend": str(item.price) if item.price else "0",
            "required_skills": item.required_skills if hasattr(item, 'required_skills') and item.required_skills else "",
            "applicants_count": vouchers,
            "status": "active" if item.is_published else "inactive",
            "posted_date": datetime_serializer(item.created_at)
        }

    elif section == "company_interns":
        student = db.query(User).filter(User.id == item.buyer_user_id).first()
        internship = db.query(Internship).filter(Internship.id == item.internship_id).first()
        # Calculate attendance
        attendance_records = db.query(InternshipAttendance).filter(
            InternshipAttendance.internship_id == item.internship_id,
            InternshipAttendance.user_id == item.buyer_user_id
        ).all()
        total_days = len(attendance_records)
        present_days = sum(1 for a in attendance_records if a.status == "present")
        attendance_pct = round((present_days / total_days * 100), 1) if total_days > 0 else 0
        return {
            "id": item.id,
            "intern_name": student.display_name if student else "N/A",
            "intern_email": student.user_email if student else "N/A",
            "college_name": student.profile.college.name if student and hasattr(student.profile, 'college') and hasattr(student.profile.college, 'name') else "N/A",
            "position_title": internship.title if internship else "N/A",
            "join_date": format_date_readable(item.created_at),
            "attendance_percentage": f"{attendance_pct}%",
            "status": item.status.title()
        }

    elif section == "company_performance":
        user = db.query(User).filter(User.id == item.user_id).first()
        internship = db.query(Internship).filter(Internship.id == item.internship_id).first()
        return {
            "id": item.id,
            "intern_name": user.display_name if user else "N/A",
            "intern_email": user.user_email if user else "N/A",
            "position_title": internship.title if internship else "N/A",
            "rating": "N/A",  # Would come from review model
            "feedback": item.notes if hasattr(item, 'notes') and item.notes else "",
            "review_date": datetime_serializer(item.date) if hasattr(item, 'date') and item.date else datetime_serializer(item.created_at),
            "reviewer_name": current_user.display_name
        }

    return {}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/export_import.py
git commit -m "feat: add role-scoped serialization for export data"
```

---

## Task 4: Add role-specific export endpoints to backend

**Files:**
- Modify: `backend/app/routers/export_import.py`

- [ ] **Step 1: Add instructor export endpoint**

Add after the existing `/admin/export/{section}` endpoint (after line 1667):

```python
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
    """
    Export instructor-scoped data as Excel or PDF.

    Sections: instructor_courses, instructor_students, instructor_quiz_results, instructor_assignment_results
    Formats: excel, pdf
    """
    valid_sections = ["instructor_courses", "instructor_students", "instructor_quiz_results", "instructor_assignment_results"]
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    if format not in ["excel", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'excel' or 'pdf'"
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
        items = get_role_section_query(db, section, current_user, status, date_from, date_to, search)

        # Build filters dict
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
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters)
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(
                    io.BytesIO(pdf_bytes),
                    media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )
            else:
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(
                    io.BytesIO(excel_bytes),
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

        # Serialize items
        rows = []
        for item in items:
            serialized = serialize_role_item(item, section, db, current_user)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters)
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(
                io.BytesIO(excel_bytes),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
```

- [ ] **Step 2: Add SPOC export endpoint**

```python
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
    """
    Export SPOC-scoped data as Excel or PDF.

    Sections: spoc_students, spoc_internships, spoc_placements
    Formats: excel, pdf
    """
    valid_sections = ["spoc_students", "spoc_internships", "spoc_placements"]
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    if format not in ["excel", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'excel' or 'pdf'"
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
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters)
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(
                    io.BytesIO(pdf_bytes),
                    media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )
            else:
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(
                    io.BytesIO(excel_bytes),
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

        rows = []
        for item in items:
            serialized = serialize_role_item(item, section, db, current_user)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters)
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(
                io.BytesIO(excel_bytes),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
```

- [ ] **Step 3: Add company export endpoint**

```python
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
    """
    Export company-scoped data as Excel or PDF.

    Sections: company_positions, company_interns, company_performance
    Formats: excel, pdf
    """
    valid_sections = ["company_positions", "company_interns", "company_performance"]
    if section not in valid_sections:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}"
        )

    if format not in ["excel", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format. Use 'excel' or 'pdf'"
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
                pdf_bytes = generate_pdf([], columns, f"{section_label} Export", filters)
                filename = f"{section}_export_{timestamp}.pdf"
                return StreamingResponse(
                    io.BytesIO(pdf_bytes),
                    media_type='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )
            else:
                excel_bytes = generate_excel([], columns, f"{section_label} Export", section[:31], filters)
                filename = f"{section}_export_{timestamp}.xlsx"
                return StreamingResponse(
                    io.BytesIO(excel_bytes),
                    media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'}
                )

        rows = []
        for item in items:
            serialized = serialize_role_item(item, section, db, current_user)
            if serialized:
                rows.append(serialized)

        if format == "pdf":
            pdf_bytes = generate_pdf(rows, columns, f"{section_label} Export", filters)
            filename = f"{section}_export_{timestamp}.pdf"
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
        else:
            excel_bytes = generate_excel(rows, columns, f"{section_label} Export", section[:31], filters)
            filename = f"{section}_export_{timestamp}.xlsx"
            return StreamingResponse(
                io.BytesIO(excel_bytes),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/export_import.py
git commit -m "feat: add role-specific export endpoints for instructor, spoc, company"
```

---

## Task 5: Add export count endpoint for role sections

**Files:**
- Modify: `backend/app/routers/export_import.py`

- [ ] **Step 1: Add role-scoped count endpoints**

Add after the `/admin/export/{section}/count` endpoint (after line 2020):

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/export_import.py
git commit -m "feat: add count endpoints for role-based exports"
```

---

## Task 6: Make ExportImportPanel component role-aware

**Files:**
- Modify: `frontend/src/components/admin/ExportImportPanel.tsx`

- [ ] **Step 1: Add role prop and update section definitions**

Update the interface and section labels (around line 41-93):

```typescript
interface ExportImportPanelProps {
  section: ExportSection
  onImportComplete?: () => void
  filters?: Record<string, any>
  role?: 'admin' | 'instructor' | 'spoc' | 'company'  // NEW
}
```

Update the props destructuring (around line 59):

```typescript
export const ExportImportPanel: React.FC<ExportImportPanelProps> = ({
  section,
  onImportComplete,
  filters = {},
  role = 'admin'  // NEW
}) => {
```

Add role-specific section labels after the existing sectionLabel (around line 93):

```typescript
const sectionLabel: Record<ExportSection, string> = {
  // ... existing labels ...
  internships: 'Internships',
  internship_roster: 'Internship Roster',
  // Role-specific sections
  instructor_courses: 'My Courses',
  instructor_students: 'My Students',
  instructor_quiz_results: 'Quiz Results',
  instructor_assignment_results: 'Assignment Results',
  spoc_students: 'College Students',
  spoc_internships: 'College Internships',
  spoc_placements: 'Student Placements',
  company_positions: 'Open Positions',
  company_interns: 'Assigned Interns',
  company_performance: 'Performance Reviews'
}
```

- [ ] **Step 2: Update API endpoint based on role**

Update the `fetchRecordCount` function (around line 102):

```typescript
  const fetchRecordCount = async () => {
    setRecordCount({ count: 0, loading: true })
    try {
      const queryParams = new URLSearchParams({
        ...(dateRangeFilter.from && { date_from: dateRangeFilter.from }),
        ...(dateRangeFilter.to && { date_to: dateRangeFilter.to }),
        ...(statusFilter && { status: statusFilter })
      }).toString()

      const endpoint = role === 'admin' ? '/admin' : `/${role}`
      const response = await api.get(`${endpoint}/export/${section}/count?${queryParams}`)
      setRecordCount({
        count: response.data.count || 0,
        loading: false
      })
    } catch {
      setRecordCount({ count: 0, loading: false })
    }
  }
```

Update the `handleExport` function (around line 142):

```typescript
      const exportFilters = {
        ...filters,
        ...(dateRangeFilter.from && { date_from: dateRangeFilter.from }),
        ...(dateRangeFilter.to && { date_to: dateRangeFilter.to }),
        ...(statusFilter && { status: statusFilter })
      }

      const endpoint = role === 'admin' ? '/admin' : `/${role}`
      const response = await api.get(`${endpoint}/export/${section}?format=${format}&${new URLSearchParams(exportFilters as any).toString()}`, {
        responseType: 'blob'
      })

      const blob = response.data
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/admin/ExportImportPanel.tsx
git commit -m "feat: add role prop to ExportImportPanel component"
```

---

## Task 7: Update TypeScript types for role-specific sections

**Files:**
- Modify: `frontend/src/api/admin.ts`

- [ ] **Step 1: Add role-specific sections to ExportSection type**

Update the ExportSection type (around line 302):

```typescript
export type ExportSection = 'students' | 'instructors' | 'spocs' | 'companies' | 'courses' | 'blogs' | 'certificates' | 'orders' | 'coupons' | 'dashboard' | 'internships' | 'internship_roster'
  // Instructor sections
  | 'instructor_courses' | 'instructor_students' | 'instructor_quiz_results' | 'instructor_assignment_results'
  // SPOC sections
  | 'spoc_students' | 'spoc_internships' | 'spoc_placements'
  // Company sections
  | 'company_positions' | 'company_interns' | 'company_performance'
```

- [ ] **Step 2: Add role-specific export functions**

Add after the existing `downloadTemplate` function (around line 397):

```typescript
// ============================================================================
// Role-based Export/Import
// ============================================================================

export async function exportRoleData({
  role,
  section,
  format,
  filters = {}
}: {
  role: 'instructor' | 'spoc' | 'company'
  section: string
  format: ExportFormat
  filters?: Record<string, any>
}): Promise<Blob> {
  const queryParams = new URLSearchParams({
    format,
    ...Object.entries(filters).reduce((acc, [k, v]) => ({ ...acc, [k]: String(v) }), {})
  }).toString()

  const response = await api.get(`/${role}/export/${section}?${queryParams}`, {
    responseType: 'blob'
  })
  return response.data
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/admin.ts
git commit -m "feat: add role-specific export types and API functions"
```

---

## Task 8: Add ExportImportPanel to Instructor Dashboard

**Files:**
- Modify: `frontend/src/pages/instructor/dashboard.tsx`

- [ ] **Step 1: Add ExportImportPanel to instructor dashboard**

Find the main dashboard content area and add the panel. The exact location depends on the current layout, but add it after the stats cards and before the courses list:

```typescript
import { ExportImportPanel } from '@/components/admin/ExportImportPanel'

// In the component return, add:
<div className="mt-6">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Export Your Data</h2>
  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="instructor_courses" role="instructor" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="instructor_students" role="instructor" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="instructor_quiz_results" role="instructor" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="instructor_assignment_results" role="instructor" />
    </div>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/instructor/dashboard.tsx
git commit -m "feat: add export panels to instructor dashboard"
```

---

## Task 9: Add ExportImportPanel to SPOC Dashboard

**Files:**
- Modify: `frontend/src/pages/spoc/dashboard.tsx`

- [ ] **Step 1: Add ExportImportPanel to SPOC dashboard**

```typescript
import { ExportImportPanel } from '@/components/admin/ExportImportPanel'

// In the component return:
<div className="mt-6">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Export College Data</h2>
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="spoc_students" role="spoc" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="spoc_internships" role="spoc" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="spoc_placements" role="spoc" />
    </div>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/spoc/dashboard.tsx
git commit -m "feat: add export panels to SPOC dashboard"
```

---

## Task 10: Add ExportImportPanel to Company Dashboard

**Files:**
- Modify: `frontend/src/pages/company/dashboard.tsx`

- [ ] **Step 1: Add ExportImportPanel to company dashboard**

```typescript
import { ExportImportPanel } from '@/components/admin/ExportImportPanel'

// In the component return:
<div className="mt-6">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Export Company Data</h2>
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="company_positions" role="company" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="company_interns" role="company" />
    </div>
    <div className="bg-white p-4 rounded-lg border">
      <ExportImportPanel section="company_performance" role="company" />
    </div>
  </div>
</div>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/company/dashboard.tsx
git commit -m "feat: add export panels to company dashboard"
```

---

## Task 11: Fix import for missing models in backend

**Files:**
- Modify: `backend/app/routers/export_import.py`

- [ ] **Step 1: Add missing imports**

Add to the imports section (around line 28):

```python
from app.models.quiz import Quiz, QuizAttempt
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.user import SPOCProfile
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/export_import.py
git commit -m "fix: add missing model imports for role-based export"
```

---

## Task 12: Test the implementation

**Files:**
- No file changes

- [ ] **Step 1: Test instructor export**

```bash
# Login as instructor and test
curl -X GET "http://localhost:8000/api/v1/instructor/export/instructor_courses?format=excel" \
  -H "Authorization: Bearer <INSTRUCTOR_TOKEN>" \
  --output test_instructor_courses.xlsx
```

Expected: Excel file with instructor's courses only.

- [ ] **Step 2: Test SPOC export**

```bash
curl -X GET "http://localhost:8000/api/v1/spoc/export/spoc_students?format=excel" \
  -H "Authorization: Bearer <SPOC_TOKEN>" \
  --output test_spoc_students.xlsx
```

Expected: Excel file with SPOC's college students only.

- [ ] **Step 3: Test company export**

```bash
curl -X GET "http://localhost:8000/api/v1/company/export/company_positions?format=excel" \
  -H "Authorization: Bearer <COMPANY_TOKEN>" \
  --output test_company_positions.xlsx
```

Expected: Excel file with company's positions only.

- [ ] **Step 4: Test unauthorized access**

```bash
# Try accessing instructor endpoint as student
curl -X GET "http://localhost:8000/api/v1/instructor/export/instructor_courses?format=excel" \
  -H "Authorization: Bearer <STUDENT_TOKEN>"
```

Expected: 403 Forbidden error.

- [ ] **Step 5: Verify frontend panels**

1. Start frontend: `cd frontend && npm run dev`
2. Login as instructor - verify Export/Import panels show on dashboard
3. Login as SPOC - verify Export/Import panels show on dashboard
4. Login as company - verify Export/Import panels show on dashboard
5. Click export buttons - verify files download with correct data

- [ ] **Step 6: Test empty data handling**

Export with filters that return no data - verify empty Excel/PDF is generated without errors.

---

## Self-Review Checklist

- [ ] **Spec coverage**: All sections from design spec implemented
  - Instructor: courses, students, quiz_results, assignment_results
  - SPOC: students, internships, placements
  - Company: positions, interns, performance
- [ ] **Placeholder scan**: No "TBD", "TODO", or "implement later" in plan
- [ ] **Type consistency**: Section names match across backend, frontend, and types
- [ ] **Security**: Role check on each endpoint, data filtering via WHERE clauses

---

## Notes

- Import functionality is **not** included in this iteration - exports only. Import can be added later following similar patterns.
- The `SPOCProfile.college_id` relationship is assumed to exist. If the model structure differs, adjust the queries accordingly.
- Company `company_id` on User model is assumed. Verify the actual relationship in your models.
- Attendance/performance data may need additional models depending on your actual schema.
