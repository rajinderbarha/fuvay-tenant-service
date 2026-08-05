"""Phase P — Technician Schedule & Availability: the two genuinely-missing
tables confirmed by audit (no `staff_time_off`/per-staff blocked-time table
existed anywhere in the repo; `availability_resolver.py`'s own docstring
already documents this exact gap and the reason codes it reserves for it).

Both tables are supplementary schedule EXCEPTIONS layered on top of the
existing canonical sources -- `provider_availability_rules` (recurring
weekly working hours) and `service_jobs` (assignments) remain untouched and
authoritative for their own concerns. Neither table is a second job or
availability state machine.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, DateTime, Index, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class StaffBlockedTime(ServiceOSBase):
    """A technician- or tenant-created ad-hoc unavailable interval on a
    specific date, distinct from the recurring weekly pattern. `source`
    distinguishes who created it so the mobile client can render
    tenant/system-created blocks as read-only (spec section 5)."""
    __tablename__ = "staff_blocked_times"
    __table_args__ = (
        Index("ix_sbt_tenant_staff", "tenant_id", "staff_member_id"),
        Index("ix_sbt_date", "block_date"),
    )

    tenant_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    block_date:      Mapped[date]            = mapped_column(Date(), nullable=False)
    start_time:      Mapped[time]            = mapped_column(Time(), nullable=False)
    end_time:        Mapped[time]            = mapped_column(Time(), nullable=False)
    reason:          Mapped[str | None]      = mapped_column(String(200), nullable=True)
    source:          Mapped[str]             = mapped_column(String(20), nullable=False, default="staff")  # staff | tenant | system
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "tenant_id": str(self.tenant_id), "staff_member_id": str(self.staff_member_id),
            "date": self.block_date.isoformat(), "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"), "reason": self.reason, "source": self.source,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StaffTimeOffRequest(ServiceOSBase):
    """Technician-submitted leave request, tenant-approved. Genuinely new
    (confirmed 0% pre-existing) -- `availability_resolver.py` already
    reserves the `ON_TIME_OFF` reason code and `time_off_supported: False`
    capability flag for exactly this table."""
    __tablename__ = "staff_time_off_requests"
    __table_args__ = (
        Index("ix_stor_tenant_staff", "tenant_id", "staff_member_id"),
        Index("ix_stor_status", "status"),
    )

    tenant_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    start_date:      Mapped[date]            = mapped_column(Date(), nullable=False)
    end_date:        Mapped[date]            = mapped_column(Date(), nullable=False)
    is_full_day:     Mapped[bool]            = mapped_column(Boolean, nullable=False, default=True)
    start_time:      Mapped[time | None]     = mapped_column(Time(), nullable=True)
    end_time:        Mapped[time | None]     = mapped_column(Time(), nullable=True)
    reason_category: Mapped[str]             = mapped_column(String(40), nullable=False)
    note:            Mapped[str | None]      = mapped_column(Text(), nullable=True)
    status:          Mapped[str]             = mapped_column(String(20), nullable=False, default="pending")
    requested_by_user_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    decided_by_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decided_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note:   Mapped[str | None]      = mapped_column(Text(), nullable=True)
    cancelled_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "tenant_id": str(self.tenant_id), "staff_member_id": str(self.staff_member_id),
            "start_date": self.start_date.isoformat(), "end_date": self.end_date.isoformat(),
            "is_full_day": self.is_full_day,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "reason_category": self.reason_category, "note": self.note, "status": self.status,
            "requested_by_user_id": str(self.requested_by_user_id),
            "decided_by_user_id": str(self.decided_by_user_id) if self.decided_by_user_id else None,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decision_note": self.decision_note,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
