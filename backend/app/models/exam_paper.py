"""Admin-priced, private, single-paper purchases and generation state."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from app.core.database import Base


class ExamPriceSlab(Base):
    __tablename__ = 'exam_price_slabs'
    id = Column(Integer, primary_key=True)
    exam = Column(String(10), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    min_questions = Column(Integer, nullable=False)
    max_questions = Column(Integer, nullable=False)
    price_paise = Column(Integer, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExamPaper(Base):
    __tablename__ = 'exam_papers'
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    slab_id = Column(Integer, ForeignKey('exam_price_slabs.id'), nullable=True)
    exam = Column(String(10), nullable=False)
    title = Column(String(200), nullable=False)
    question_count = Column(Integer, nullable=False)
    input_json = Column(JSON, nullable=False)
    amount_paise = Column(Integer, nullable=False, default=0)
    status = Column(String(24), nullable=False, default='awaiting_payment', index=True)
    gateway_order_id = Column(String(100), unique=True, nullable=True)
    gateway_payment_id = Column(String(100), unique=True, nullable=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    bank_id = Column(Integer, ForeignKey('question_banks.id'), nullable=True)
    questions = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    generation_id = Column(String(36), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
