"""
Quiz models - Premium SashaInfinity LMS quiz structure
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.types import Numeric as Decimal
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Quiz(Base):
    """
    Quiz model - Replicated from wp_posts where post_type='tutor_quiz'
    """
    __tablename__ = "quizzes"

    # Core fields (from wp_posts)
    id = Column(Integer, primary_key=True, index=True)
    post_author = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_date = Column(DateTime(timezone=True), server_default=func.now())
    post_content = Column(Text, default="")
    post_title = Column(Text, nullable=False)
    post_excerpt = Column(Text, default="")
    post_status = Column(String(20), default="publish")
    post_name = Column(String(200), index=True, default="")
    post_modified = Column(DateTime(timezone=True), server_default=func.now())
    post_parent = Column(Integer, ForeignKey("courses.id"), nullable=False)
    menu_order = Column(Integer, default=0)
    post_type = Column(String(20), default="tutor_quiz")

    # Quiz settings (from postmeta)
    quiz_time_limit = Column(Integer, default=0)  # in minutes, 0 = no limit
    # R8 assessment integrity: timed window (both optional, UTC)
    quiz_available_from = Column(DateTime(timezone=True), nullable=True)
    quiz_available_until = Column(DateTime(timezone=True), nullable=True)
    quiz_feedback_mode = Column(String(50), default="default")
    quiz_max_questions_for_take = Column(Integer, default=10)
    quiz_max_attempts_allowed = Column(Integer, default=0)  # 0 = unlimited
    quiz_passing_grade = Column(Integer, default=80)  # percentage
    # Scored interactive modules (H5P/Game) attached to this quiz —
    # [{kind: "h5p"|"game", id: int, title: str}]. Their results
    # (h5p_results / game_results) count toward the cumulative grade.
    interactive_modules = Column(JSON, default=list)
    quiz_question_layout_view = Column(String(50), default="single_question")
    quiz_questions_order = Column(String(50), default="rand")

    # Display settings
    quiz_hide_quiz_details = Column(Boolean, default=False)
    quiz_hide_quiz_time_display = Column(Boolean, default=False)
    quiz_auto_start = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz")

    def __repr__(self):
        return f"<Quiz(id={self.id}, title={self.post_title})>"

class QuizQuestion(Base):
    """
    Quiz questions - Replicated from tutor_quiz_questions table
    """
    __tablename__ = "quiz_questions"

    question_id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_title = Column(Text, nullable=False)
    question_description = Column(Text, default="")
    answer_explanation = Column(Text, default="")
    question_type = Column(String(50), nullable=False)  # multiple_choice, true_false, fill_in_blanks, etc.
    question_mark = Column(Decimal(9, 2), default=1.0)
    question_settings = Column(JSON, default={})
    question_order = Column(Integer, default=0)
    # R8: retired items stay in history but never appear in new attempts
    is_retired = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("QuizQuestionAnswer", back_populates="question", cascade="all, delete-orphan")
    attempt_answers = relationship("QuizAttemptAnswer", back_populates="question")

    def __repr__(self):
        return f"<QuizQuestion(id={self.question_id}, type={self.question_type})>"

class QuizQuestionAnswer(Base):
    """
    Quiz question answer options - Replicated from tutor_quiz_question_answers table
    """
    __tablename__ = "quiz_question_answers"

    answer_id = Column(Integer, primary_key=True, index=True)
    belongs_question_id = Column(Integer, ForeignKey("quiz_questions.question_id"), nullable=False)
    belongs_question_type = Column(String(250), default="")
    answer_title = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    image_id = Column(Integer, default=0)
    answer_two_gap_match = Column(Text, default="")
    answer_view_format = Column(String(250), default="")
    answer_settings = Column(JSON, default={})
    answer_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    question = relationship("QuizQuestion", back_populates="answers")

    def __repr__(self):
        return f"<QuizQuestionAnswer(id={self.answer_id}, is_correct={self.is_correct})>"

class QuizAttempt(Base):
    """
    Quiz attempts - Replicated from tutor_quiz_attempts table
    """
    __tablename__ = "quiz_attempts"

    attempt_id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_questions = Column(Integer, default=0)
    total_answered_questions = Column(Integer, default=0)
    total_marks = Column(Decimal(9, 2), default=0)
    earned_marks = Column(Decimal(9, 2), default=0)
    attempt_info = Column(JSON, default={})
    # Valid attempt_status values:
    #   attempt_started  - in progress, answers may still be saved
    #   pending_review   - submitted; contains >=1 manually-graded question
    #                      (essay/open_ended) awaiting instructor grading.
    #                      Auto-scored portion is already computed and
    #                      stored; earned_marks/total_marks reflect ONLY the
    #                      auto-graded questions until finalize recomputes.
    #   attempt_ended    - fully graded/submitted, final score stands.
    attempt_status = Column(String(50), default="attempt_started")
    attempt_ip = Column(String(250), default="")
    attempt_started_at = Column(DateTime(timezone=True), server_default=func.now())
    attempt_ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")
    course = relationship("Course")
    answers = relationship("QuizAttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QuizAttempt(id={self.attempt_id}, user_id={self.user_id}, status={self.attempt_status})>"

class QuizAttemptAnswer(Base):
    """
    Quiz attempt answers - Replicated from tutor_quiz_attempt_answers table
    """
    __tablename__ = "quiz_attempt_answers"

    attempt_answer_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("quiz_questions.question_id"), nullable=False)
    quiz_attempt_id = Column(Integer, ForeignKey("quiz_attempts.attempt_id"), nullable=False)
    given_answer = Column(Text, default="")
    question_mark = Column(Decimal(8, 2), default=0)
    achieved_mark = Column(Decimal(8, 2), default=0)
    minus_mark = Column(Decimal(8, 2), default=0)
    is_correct = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    quiz = relationship("Quiz")
    question = relationship("QuizQuestion", back_populates="attempt_answers")
    attempt = relationship("QuizAttempt", back_populates="answers")

    def __repr__(self):
        return f"<QuizAttemptAnswer(id={self.attempt_answer_id}, is_correct={self.is_correct})>"