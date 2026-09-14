"""Durable maintenance schedules and append-only execution evidence."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint, Index
from app.core.database import Base


class RuntimeJob(Base):
    __tablename__ = "runtime_jobs"
    name = Column(String(64), primary_key=True)
    status = Column(String(20), nullable=False, default="ready")
    attempts = Column(Integer, nullable=False, default=0)
    next_run_at = Column(DateTime(timezone=True), nullable=False)
    lease_token = Column(String(36), nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    last_finished_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String(120), nullable=True)
    __table_args__ = (
        CheckConstraint("status IN ('ready','running','retry','dead')", name="ck_runtime_job_status"),
        Index("ix_runtime_job_due", "status", "next_run_at"),
    )


class RuntimeRun(Base):
    __tablename__ = "runtime_runs"
    id = Column(String(36), primary_key=True)
    job_name = Column(String(64), ForeignKey("runtime_jobs.name"), nullable=False)
    worker_id = Column(String(80), nullable=False)
    status = Column(String(24), nullable=False)
    attempt = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(120), nullable=True)
    requested_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    __table_args__ = (Index("ix_runtime_runs_job_started", "job_name", "started_at"),
                      Index("ix_runtime_runs_started", "started_at"))
