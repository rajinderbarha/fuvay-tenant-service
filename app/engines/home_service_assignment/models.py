"""Sprint 20 — Home Service Job Assignment models."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class ServiceJobAssignment(ServiceOSBase):
    """One assignment record per assignment action. Only one is_current=True per job at a time."""
    __tablename__ = "service_job_assignments"
    __table_args__ = (
        Index("ix_sja_job_id",    "job_id"),
        Index("ix_sja_booking_id","booking_id"),
        Index("ix_sja_tenant_id", "tenant_id"),
        Index("ix_sja_staff_id",  "assigned_staff_member_id"),
        Index("ix_sja_status",    "assignment_status"),
        Index("ix_sja_is_current","is_current"),
    )

    job_id:                   Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:               Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:                Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_staff_member_id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_by_user_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assignment_status:        Mapped[str]              = mapped_column(String(30), nullable=False, default="assigned")
    assignment_type:          Mapped[str]              = mapped_column(String(30), nullable=False, default="manual")
    rejection_reason:         Mapped[str | None]       = mapped_column(Text(), nullable=True)
    scheduled_date:           Mapped[date | None]      = mapped_column(Date(), nullable=True)
    scheduled_time_window:    Mapped[str | None]       = mapped_column(String(50), nullable=True)
    notes:                    Mapped[str | None]       = mapped_column(Text(), nullable=True)
    is_current:               Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    accepted_at:              Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at:              Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:             Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                      str(self.id),
            "job_id":                  str(self.job_id),
            "booking_id":              str(self.booking_id),
            "tenant_id":               str(self.tenant_id),
            "assigned_staff_member_id":str(self.assigned_staff_member_id),
            "assigned_by_user_id":     str(self.assigned_by_user_id) if self.assigned_by_user_id else None,
            "assignment_status":       self.assignment_status,
            "assignment_type":         self.assignment_type,
            "rejection_reason":        self.rejection_reason,
            "scheduled_date":          self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time_window":   self.scheduled_time_window,
            "notes":                   self.notes,
            "is_current":              self.is_current,
            "accepted_at":             self.accepted_at.isoformat() if self.accepted_at else None,
            "rejected_at":             self.rejected_at.isoformat() if self.rejected_at else None,
            "cancelled_at":            self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at":              self.created_at.isoformat() if self.created_at else None,
            "updated_at":              self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceJobAssignmentEvent(ServiceOSBase):
    """Append-only timeline of all assignment events for a job."""
    __tablename__ = "service_job_assignment_events"
    __table_args__ = (
        Index("ix_sjae_job_id",    "job_id"),
        Index("ix_sjae_tenant_id", "tenant_id"),
        Index("ix_sjae_event_type","event_type"),
    )

    job_id:        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:     Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:    Mapped[str | None]       = mapped_column(String(50), nullable=True)
    event_type:    Mapped[str]              = mapped_column(String(60), nullable=False)
    old_value:     Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    new_value:     Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    reason:        Mapped[str | None]       = mapped_column(Text(), nullable=True)
    request_id:    Mapped[str | None]       = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "job_id":        str(self.job_id),
            "booking_id":    str(self.booking_id),
            "tenant_id":     str(self.tenant_id),
            "assignment_id": str(self.assignment_id) if self.assignment_id else None,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "actor_role":    self.actor_role,
            "event_type":    self.event_type,
            "old_value":     self.old_value,
            "new_value":     self.new_value,
            "reason":        self.reason,
            "request_id":    self.request_id,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }
