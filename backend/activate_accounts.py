#!/usr/bin/env python3
"""Activate instructor and student accounts"""
from app.core.database import SessionLocal
from app.models.user import User, InstructorProfile

db = SessionLocal()

# Fix instructor
instructor = db.query(User).filter(User.user_email == "instructor@sashainfinity.com").first()
instructor.user_status = 1
instructor.is_active = True
instructor.is_verified = True

ip = db.query(InstructorProfile).filter(InstructorProfile.user_id == instructor.id).first()
if ip:
    ip.is_approved = True
    ip.is_blocked = False
    print(f"Updated InstructorProfile: is_approved=True")
else:
    ip = InstructorProfile(
        user_id=instructor.id,
        instructor_bio="Course Instructor at SashaInfinity",
        instructor_designation="Instructor",
        is_approved=True,
        is_blocked=False,
        profile_completion=100
    )
    db.add(ip)
    print(f"Created InstructorProfile: is_approved=True")

# Fix student
student = db.query(User).filter(User.user_email == "student@sashainfinity.com").first()
student.user_status = 1
student.is_active = True
student.is_verified = True

db.commit()

# Verify
for email in ["instructor@sashainfinity.com", "student@sashainfinity.com"]:
    u = db.query(User).filter(User.user_email == email).first()
    status = "active" if u.user_status == 1 else "inactive"
    print(f"{u.user_email}: role={u.role}, status={status}, verified={u.is_verified}")
    if u.role == "instructor":
        ip2 = db.query(InstructorProfile).filter(InstructorProfile.user_id == u.id).first()
        approved = ip2.is_approved if ip2 else "MISSING"
        print(f"  InstructorProfile approved: {approved}")

db.close()
print("All accounts activated!")
