"""
Instructor Review Model - Private feedback from students to instructors
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class InstructorReview(Base):
    """
    Private reviews/feedback from students to instructors
    Only visible to the instructor and admin
    """
    __tablename__ = "instructor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_title = Column(String(255), default="")
    review_content = Column(Text, nullable=False)

    # Privacy and status
    is_private = Column(Boolean, default=True)  # Always private by default
    is_read = Column(Boolean, default=False)  # Track if instructor has read it
    instructor_response = Column(Text, default="")  # Instructor can respond
    response_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course")
    instructor = relationship("User", foreign_keys=[instructor_id])
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self):
        return f"<InstructorReview(id={self.id}, course_id={self.course_id}, rating={self.rating})>"
