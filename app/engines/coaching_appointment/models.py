"""Sprint 17 — Coaching Appointment Draft: SQLAlchemy models (3 tables)."""
from __future__ import annotations
import uuid
from datetime import datetime, date, time
from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class CoachingAppointmentDraft(ServiceOSBase):
    """Pre-appointment chatbot draft for Coaching / IELTS flow."""
    __tablename__ = "coaching_appointment_drafts"

    customer_id:                Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    guest_session_id:           Mapped[str | None]       = mapped_column(String(200), nullable=True)
    ai_session_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:                Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:                Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    selected_tenant_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    selected_staff_member_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:                     Mapped[str]              = mapped_column(String(40), nullable=False, default="draft")
    # Student details
    student_name:               Mapped[str | None]       = mapped_column(String(200), nullable=True)
    student_phone:              Mapped[str | None]       = mapped_column(String(30), nullable=True)
    student_email:              Mapped[str | None]       = mapped_column(String(255), nullable=True)
    student_age:                Mapped[int | None]       = mapped_column(Integer(), nullable=True)
    current_education:          Mapped[str | None]       = mapped_column(String(200), nullable=True)
    target_exam:                Mapped[str | None]       = mapped_column(String(100), nullable=True)
    target_band:                Mapped[str | None]       = mapped_column(String(20), nullable=True)
    # Appointment preferences
    preferred_mode:             Mapped[str | None]       = mapped_column(String(20), nullable=True)
    city:                       Mapped[str | None]       = mapped_column(String(100), nullable=True)
    zipcode:                    Mapped[str | None]       = mapped_column(String(20), nullable=True)
    selected_date:              Mapped[date | None]      = mapped_column(Date(), nullable=True)
    selected_time_start:        Mapped[time | None]      = mapped_column(Time(), nullable=True)
    selected_time_end:          Mapped[time | None]      = mapped_column(Time(), nullable=True)
    # Snapshots
    slot_snapshot:              Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    center_location_snapshot:   Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    appointment_fee_snapshot:   Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    provider_options:           Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    next_available_slots:       Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    recommended_slot_snapshot:  Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    selected_provider_snapshot: Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    fallback_inquiry_payload:   Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    appointment_summary:        Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    # Sub-statuses
    location_status:            Mapped[str | None]       = mapped_column(String(30), nullable=True, default="pending")
    slot_status:                Mapped[str | None]       = mapped_column(String(30), nullable=True, default="pending")
    fee_status:                 Mapped[str | None]       = mapped_column(String(30), nullable=True, default="pending")
    # Failure
    failure_code:               Mapped[str | None]       = mapped_column(String(100), nullable=True)
    failure_message:            Mapped[str | None]       = mapped_column(Text(), nullable=True)
    notes:                      Mapped[str | None]       = mapped_column(Text(), nullable=True)
    expires_at:                 Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                        str(self.id),
            "customer_id":               str(self.customer_id) if self.customer_id else None,
            "ai_session_id":             str(self.ai_session_id) if self.ai_session_id else None,
            "category_id":               str(self.category_id),
            "offering_id":               str(self.offering_id),
            "selected_tenant_id":        str(self.selected_tenant_id) if self.selected_tenant_id else None,
            "selected_staff_member_id":  str(self.selected_staff_member_id) if self.selected_staff_member_id else None,
            "status":                    self.status,
            "student_name":              self.student_name,
            "student_phone":             self.student_phone,
            "student_email":             self.student_email,
            "student_age":               self.student_age,
            "current_education":         self.current_education,
            "target_exam":               self.target_exam,
            "target_band":               self.target_band,
            "preferred_mode":            self.preferred_mode,
            "city":                      self.city,
            "zipcode":                   self.zipcode,
            "selected_date":             self.selected_date.isoformat() if self.selected_date else None,
            "selected_time_start":       self.selected_time_start.isoformat() if self.selected_time_start else None,
            "selected_time_end":         self.selected_time_end.isoformat() if self.selected_time_end else None,
            "slot_snapshot":             self.slot_snapshot,
            "center_location_snapshot":  self.center_location_snapshot,
            "appointment_fee_snapshot":  self.appointment_fee_snapshot,
            "provider_options":          self.provider_options,
            "next_available_slots":      self.next_available_slots,
            "recommended_slot_snapshot": self.recommended_slot_snapshot,
            "selected_provider_snapshot":self.selected_provider_snapshot,
            "fallback_inquiry_payload":  self.fallback_inquiry_payload,
            "appointment_summary":       self.appointment_summary,
            "location_status":           self.location_status,
            "slot_status":               self.slot_status,
            "fee_status":                self.fee_status,
            "failure_code":              self.failure_code,
            "failure_message":           self.failure_message,
            "notes":                     self.notes,
            "expires_at":                self.expires_at.isoformat() if self.expires_at else None,
            "created_at":                self.created_at.isoformat() if self.created_at else None,
            "updated_at":                self.updated_at.isoformat() if self.updated_at else None,
        }


class CoachingAppointmentDraftEvent(ServiceOSBase):
    """Immutable event log for coaching appointment drafts."""
    __tablename__ = "coaching_appointment_draft_events"

    draft_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str]            = mapped_column(String(30), nullable=False)
    event_type: Mapped[str]            = mapped_column(String(60), nullable=False)
    old_value:  Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    new_value:  Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    message:    Mapped[str | None]     = mapped_column(Text(), nullable=True)
    request_id: Mapped[str | None]     = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":         str(self.id),
            "draft_id":   str(self.draft_id),
            "actor_type": self.actor_type,
            "event_type": self.event_type,
            "old_value":  self.old_value,
            "new_value":  self.new_value,
            "message":    self.message,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CoachingAppointmentSlotHold(ServiceOSBase):
    """Short-lived slot hold during appointment confirmation window (15 min TTL)."""
    __tablename__ = "coaching_appointment_slot_holds"

    draft_id:        Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    offering_id:     Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    slot_date:       Mapped[date]             = mapped_column(Date(), nullable=False)
    start_time:      Mapped[time]             = mapped_column(Time(), nullable=False)
    end_time:        Mapped[time]             = mapped_column(Time(), nullable=False)
    hold_status:     Mapped[str]              = mapped_column(String(20), nullable=False, default="held")
    expires_at:      Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id":              str(self.id),
            "draft_id":        str(self.draft_id),
            "tenant_id":       str(self.tenant_id),
            "staff_member_id": str(self.staff_member_id) if self.staff_member_id else None,
            "offering_id":     str(self.offering_id),
            "slot_date":       self.slot_date.isoformat(),
            "start_time":      self.start_time.isoformat(),
            "end_time":        self.end_time.isoformat(),
            "hold_status":     self.hold_status,
            "expires_at":      self.expires_at.isoformat(),
            "created_at":      self.created_at.isoformat() if self.created_at else None,
        }
