"""Appointment Engine — Models (4 tables). Slot-level scheduling."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Appointment(ServiceOSBase):
    """Specific staff + specific slot booking. Unique constraint prevents double-booking."""
    __tablename__ = "appointments"
    __table_args__ = (
        # DB-level double-booking prevention — same staff + same slot cannot both be active
        UniqueConstraint("staff_id", "scheduled_at", "tenant_id", name="uq_appt_staff_slot"),
        Index("ix_appt_tenant_status",  "tenant_id", "status"),
        Index("ix_appt_staff",          "staff_id"),
        Index("ix_appt_customer",       "customer_id"),
        Index("ix_appt_scheduled",      "scheduled_at"),
    )

    tenant_id:           Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_id:            Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:          Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    service_type_id:     Mapped[str]           = mapped_column(String(100), nullable=False)
    status:              Mapped[str]           = mapped_column(String(20), default="hold", nullable=False)
    appointment_number:  Mapped[str]           = mapped_column(String(30), nullable=False, unique=True)
    scheduled_at:        Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes:    Mapped[int]           = mapped_column(Integer, default=60, nullable=False)
    ends_at:             Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    hold_expires_at:     Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str|None]      = mapped_column(String(500), nullable=True)
    no_show_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_24h_sent:   Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    reminder_2h_sent:    Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    customer_notes:      Mapped[str|None]      = mapped_column(Text, nullable=True)
    meta:                Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)


class AppointmentStatusHistory(ServiceOSBase):
    """APPEND-ONLY appointment lifecycle. Same pattern as BookingStatusHistory."""
    __tablename__ = "appointment_status_history"
    __table_args__ = (Index("ix_ash_appt_id", "appointment_id"),)

    appointment_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status:    Mapped[str|None]       = mapped_column(String(20), nullable=True)
    to_status:      Mapped[str]            = mapped_column(String(20), nullable=False)
    changed_by:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    changed_by_role:Mapped[str|None]       = mapped_column(String(30), nullable=True)
    reason:         Mapped[str|None]       = mapped_column(String(500), nullable=True)


class StaffCalendarBlock(ServiceOSBase):
    """Blocked times per staff — holidays, leave, training. Checked before offering slots."""
    __tablename__ = "staff_calendar_blocks"
    __table_args__ = (
        Index("ix_scb_staff_date", "staff_id", "block_date"),
        Index("ix_scb_tenant",     "tenant_id"),
    )

    staff_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    block_date:   Mapped[str]            = mapped_column(String(10), nullable=False)
    start_time:   Mapped[str]            = mapped_column(String(8), nullable=False)
    end_time:     Mapped[str]            = mapped_column(String(8), nullable=False)
    block_type:   Mapped[str]            = mapped_column(String(30), default="leave", nullable=False)
    reason:       Mapped[str|None]       = mapped_column(String(255), nullable=True)
    is_full_day:  Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_by:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class StaffWorkingHours(ServiceOSBase):
    """Per-staff working hours configuration. Generates available slots."""
    __tablename__ = "staff_working_hours"
    __table_args__ = (
        UniqueConstraint("staff_id", "tenant_id", "day_of_week", name="uq_swh_staff_day"),
        Index("ix_swh_staff", "staff_id"),
    )

    staff_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    day_of_week:    Mapped[int]       = mapped_column(Integer, nullable=False)  # 0=Mon 6=Sun
    start_time:     Mapped[str]       = mapped_column(String(8), nullable=False)  # "09:00"
    end_time:       Mapped[str]       = mapped_column(String(8), nullable=False)  # "18:00"
    slot_duration:  Mapped[int]       = mapped_column(Integer, default=60, nullable=False)
    buffer_minutes: Mapped[int]       = mapped_column(Integer, default=15, nullable=False)
    is_active:      Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
