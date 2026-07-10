"""Sprint 21 — Execution lifecycle SQLAlchemy models (7 tables)."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class ServiceJobExecutionEvent(ServiceOSBase):
    __tablename__ = "service_job_execution_events"
    __table_args__ = (
        Index("ix_sjee_job_id",    "job_id"),
        Index("ix_sjee_tenant_id", "tenant_id"),
        Index("ix_sjee_event_type","event_type"),
    )
    booking_id:      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    event_type:      Mapped[str]              = mapped_column(String(60), nullable=False)
    old_status:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    new_status:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    notes:           Mapped[str | None]       = mapped_column(Text(), nullable=True)
    event_metadata:  Mapped[dict | None]      = mapped_column("metadata", JSONB, nullable=True)
    request_id:      Mapped[str | None]       = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "job_id": str(self.job_id),
            "event_type": self.event_type, "old_status": self.old_status,
            "new_status": self.new_status, "notes": self.notes,
            "actor_role": self.actor_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ServiceJobExecutionNote(ServiceOSBase):
    __tablename__ = "service_job_execution_notes"
    __table_args__ = (
        Index("ix_sjen_job_id",    "job_id"),
        Index("ix_sjen_tenant_id", "tenant_id"),
    )
    booking_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    note_type:           Mapped[str]              = mapped_column(String(40), nullable=False)
    note_text:           Mapped[str]              = mapped_column(Text(), nullable=False)
    is_customer_visible: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "job_id": str(self.job_id),
            "note_type": self.note_type, "note_text": self.note_text,
            "is_customer_visible": self.is_customer_visible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ServiceJobMediaUpload(ServiceOSBase):
    __tablename__ = "service_job_media_uploads"
    __table_args__ = (
        Index("ix_sjmu_job_id",    "job_id"),
        Index("ix_sjmu_tenant_id", "tenant_id"),
    )
    booking_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    media_type:          Mapped[str]              = mapped_column(String(40), nullable=False)
    file_url:            Mapped[str]              = mapped_column(String(1000), nullable=False)
    file_name:           Mapped[str | None]       = mapped_column(String(255), nullable=True)
    mime_type:           Mapped[str | None]       = mapped_column(String(100), nullable=True)
    file_size:           Mapped[int | None]       = mapped_column(Integer, nullable=True)
    caption:             Mapped[str | None]       = mapped_column(Text(), nullable=True)
    is_customer_visible: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "job_id": str(self.job_id),
            "media_type": self.media_type, "file_url": self.file_url,
            "file_name": self.file_name, "caption": self.caption,
            "is_customer_visible": self.is_customer_visible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PartsRequest(ServiceOSBase):
    """HS8B — real parts request record, replacing the note-only
    "needs parts" flag. Technician-created, tenant/business-approved."""
    __tablename__ = "service_job_parts_requests"
    __table_args__ = (
        Index("ix_sjpr_job_id",    "job_id"),
        Index("ix_sjpr_tenant_id", "tenant_id"),
        Index("ix_sjpr_status",    "status"),
    )
    job_id:                      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:                   Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    technician_id:                Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    part_name:                   Mapped[str]              = mapped_column(String(200), nullable=False)
    quantity:                    Mapped[int]              = mapped_column(Integer, nullable=False)
    estimated_cost:               Mapped[float]            = mapped_column(Numeric(12, 2), nullable=False)
    reason:                       Mapped[str]              = mapped_column(Text(), nullable=False)
    photo_ids:                    Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    technician_note:               Mapped[str | None]       = mapped_column(Text(), nullable=True)
    customer_approval_required:   Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    business_approval_required:   Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    status:                       Mapped[str]              = mapped_column(String(30), nullable=False, default="requested")
    approved_by:                   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at:                   Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by:                   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rejected_at:                   Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason:              Mapped[str | None]       = mapped_column(Text(), nullable=True)
    request_id:                    Mapped[str | None]       = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "parts_request_id":           str(self.id),
            "job_id":                     str(self.job_id),
            "tenant_id":                  str(self.tenant_id),
            "technician_id":              str(self.technician_id),
            "part_name":                  self.part_name,
            "quantity":                   self.quantity,
            "estimated_cost":             float(self.estimated_cost),
            "reason":                     self.reason,
            "photo_ids":                  self.photo_ids or [],
            "technician_note":            self.technician_note,
            "customer_approval_required": self.customer_approval_required,
            "business_approval_required": self.business_approval_required,
            "status":                     self.status,
            "approved_by":                str(self.approved_by) if self.approved_by else None,
            "approved_at":                self.approved_at.isoformat() if self.approved_at else None,
            "rejected_by":                str(self.rejected_by) if self.rejected_by else None,
            "rejected_at":                self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason":           self.rejection_reason,
            "created_at":                 self.created_at.isoformat() if self.created_at else None,
            "updated_at":                 self.updated_at.isoformat() if self.updated_at else None,
        }


class CoachingAppointmentExecutionEvent(ServiceOSBase):
    __tablename__ = "coaching_appointment_execution_events"
    __table_args__ = (
        Index("ix_caee_appt_id",   "appointment_id"),
        Index("ix_caee_tenant_id", "tenant_id"),
    )
    appointment_id:  Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    event_type:      Mapped[str]              = mapped_column(String(60), nullable=False)
    old_status:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    new_status:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    notes:           Mapped[str | None]       = mapped_column(Text(), nullable=True)
    event_metadata:  Mapped[dict | None]      = mapped_column("metadata", JSONB, nullable=True)
    request_id:      Mapped[str | None]       = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "appointment_id": str(self.appointment_id),
            "event_type": self.event_type, "old_status": self.old_status,
            "new_status": self.new_status, "notes": self.notes,
            "actor_role": self.actor_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CoachingAppointmentNote(ServiceOSBase):
    __tablename__ = "coaching_appointment_notes"
    __table_args__ = (
        Index("ix_can_appt_id",   "appointment_id"),
        Index("ix_can_tenant_id", "tenant_id"),
    )
    appointment_id:      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    note_type:           Mapped[str]              = mapped_column(String(40), nullable=False)
    note_text:           Mapped[str]              = mapped_column(Text(), nullable=False)
    is_customer_visible: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "appointment_id": str(self.appointment_id),
            "note_type": self.note_type, "note_text": self.note_text,
            "is_customer_visible": self.is_customer_visible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RealEstateLeadExecutionEvent(ServiceOSBase):
    __tablename__ = "real_estate_lead_execution_events"
    __table_args__ = (
        Index("ix_relee_lead_id",   "lead_id"),
        Index("ix_relee_tenant_id", "tenant_id"),
    )
    lead_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_agent_id:Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:       Mapped[str | None]       = mapped_column(String(50), nullable=True)
    event_type:       Mapped[str]              = mapped_column(String(60), nullable=False)
    old_status:       Mapped[str | None]       = mapped_column(String(50), nullable=True)
    new_status:       Mapped[str | None]       = mapped_column(String(50), nullable=True)
    notes:            Mapped[str | None]       = mapped_column(Text(), nullable=True)
    event_metadata:   Mapped[dict | None]      = mapped_column("metadata", JSONB, nullable=True)
    request_id:       Mapped[str | None]       = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "lead_id": str(self.lead_id),
            "event_type": self.event_type, "old_status": self.old_status,
            "new_status": self.new_status, "notes": self.notes,
            "actor_role": self.actor_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RealEstateLeadNote(ServiceOSBase):
    __tablename__ = "real_estate_lead_notes"
    __table_args__ = (
        Index("ix_reln_lead_id",   "lead_id"),
        Index("ix_reln_tenant_id", "tenant_id"),
    )
    lead_id:             Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_agent_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    note_type:           Mapped[str]              = mapped_column(String(40), nullable=False)
    note_text:           Mapped[str]              = mapped_column(Text(), nullable=False)
    is_customer_visible: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "lead_id": str(self.lead_id),
            "note_type": self.note_type, "note_text": self.note_text,
            "is_customer_visible": self.is_customer_visible,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
