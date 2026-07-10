"""Dispatch Engine — Models (2 tables)."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class DispatchRecord(ServiceOSBase):
    """Immutable record of every dispatch decision with full scoring breakdown."""
    __tablename__ = "dispatch_records"
    __table_args__ = (UniqueConstraint("job_id", name="uq_dr_job"),
                      Index("ix_dr_tenant", "tenant_id"),
                      Index("ix_dr_staff", "assigned_staff_id"))

    job_id:             Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    tenant_id:          Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    dispatch_mode:      Mapped[str]           = mapped_column(String(20), nullable=False)
    status:             Mapped[str]           = mapped_column(String(20), default="pending", nullable=False)
    assigned_staff_id:  Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    candidates_scored:  Mapped[list]          = mapped_column(JSONB, default=list, nullable=False)
    score_weights:      Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    rejection_count:    Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    escalation_count:   Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    accepted_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:         Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_by:      Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)


class DispatchEscalationLog(ServiceOSBase):
    """Log of each escalation attempt — who was tried, why rejected."""
    __tablename__ = "dispatch_escalation_logs"
    __table_args__ = (Index("ix_del_job_id", "job_id"),)

    job_id:       Mapped[str]           = mapped_column(String(100), nullable=False)
    tenant_id:    Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_no:   Mapped[int]           = mapped_column(Integer, nullable=False)
    outcome:      Mapped[str]           = mapped_column(String(20), nullable=False)
    reason:       Mapped[str|None]      = mapped_column(String(255), nullable=True)
    score:        Mapped[float|None]    = mapped_column(Float, nullable=True)
