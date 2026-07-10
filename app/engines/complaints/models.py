"""Sprint 25 — Complaints ORM models (migration 043 + 075 settlement engine)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _num(prefix: str) -> str:
    import random, string
    return f"{prefix}-" + "".join(random.choices(string.digits, k=8))


class CustomerComplaint(Base):
    __tablename__ = "customer_complaints"
    __table_args__ = (
        UniqueConstraint("complaint_number", name="uq_cc_number"),
        Index("ix_cc_tenant_id",     "tenant_id"),
        Index("ix_cc_customer_id",   "customer_id"),
        Index("ix_cc_status",        "status"),
        Index("ix_cc_created_at",    "created_at"),
        Index("ix_cc_tenant_status", "tenant_id", "status"),
        Index("ix_cc_tenant_created","tenant_id", "created_at"),
    )

    id                              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_number                = Column(String(40),  nullable=False, default=lambda: _num("CMP"))
    customer_id                     = Column(UUID(as_uuid=True), nullable=False)
    tenant_id                       = Column(UUID(as_uuid=True), nullable=True)
    category_id                     = Column(UUID(as_uuid=True), nullable=False)
    offering_id                     = Column(UUID(as_uuid=True), nullable=True)
    record_type                     = Column(String(40),  nullable=False)
    record_id                       = Column(UUID(as_uuid=True), nullable=False)
    booking_id                      = Column(UUID(as_uuid=True), nullable=True)
    job_id                          = Column(UUID(as_uuid=True), nullable=True)
    invoice_id                      = Column(UUID(as_uuid=True), nullable=True)
    appointment_id                  = Column(UUID(as_uuid=True), nullable=True)
    lead_id                         = Column(UUID(as_uuid=True), nullable=True)
    review_id                       = Column(UUID(as_uuid=True), nullable=True)
    assigned_admin_user_id          = Column(UUID(as_uuid=True), nullable=True)
    complaint_type                  = Column(String(40),  nullable=False)
    requested_resolution            = Column(String(40),  nullable=True)
    priority                        = Column(String(20),  nullable=False, default="normal")
    status                          = Column(String(40),  nullable=False, default="open")
    title                           = Column(String(300), nullable=True)
    description                     = Column(Text,        nullable=False)
    customer_visible_summary        = Column(Text,        nullable=True)
    internal_admin_notes            = Column(Text,        nullable=True)
    provider_response_required      = Column(Boolean,     nullable=False, default=True)
    provider_responded_at           = Column(DateTime(timezone=True), nullable=True)
    customer_accepted_resolution_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at                     = Column(DateTime(timezone=True), nullable=True)
    closed_at                       = Column(DateTime(timezone=True), nullable=True)
    # Migration 075 — SLA + settlement tracking
    severity                        = Column(String(20),  nullable=True, default="medium")
    sla_status                      = Column(String(30),  nullable=True, default="on_time")
    tenant_first_response_due_at    = Column(DateTime(timezone=True), nullable=True)
    ai_escalation_at                = Column(DateTime(timezone=True), nullable=True)
    admin_escalation_at             = Column(DateTime(timezone=True), nullable=True)
    settlement_status               = Column(String(40),  nullable=True)
    ai_session_id                   = Column(UUID(as_uuid=True), nullable=True)
    created_at                      = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at                      = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "complaint_number":     self.complaint_number,
            "customer_id":          str(self.customer_id),
            "tenant_id":            str(self.tenant_id) if self.tenant_id else None,
            "category_id":          str(self.category_id),
            "offering_id":          str(self.offering_id) if self.offering_id else None,
            "record_type":          self.record_type,
            "record_id":            str(self.record_id),
            "booking_id":           str(self.booking_id) if self.booking_id else None,
            "job_id":               str(self.job_id) if self.job_id else None,
            "invoice_id":           str(self.invoice_id) if self.invoice_id else None,
            "appointment_id":       str(self.appointment_id) if self.appointment_id else None,
            "lead_id":              str(self.lead_id) if self.lead_id else None,
            "review_id":            str(self.review_id) if self.review_id else None,
            "assigned_admin_user_id": str(self.assigned_admin_user_id) if self.assigned_admin_user_id else None,
            "complaint_type":       self.complaint_type,
            "requested_resolution": self.requested_resolution,
            "priority":             self.priority,
            "status":               self.status,
            "title":                self.title,
            "description":          self.description,
            "customer_visible_summary": self.customer_visible_summary,
            "internal_admin_notes": self.internal_admin_notes,
            "provider_response_required": self.provider_response_required,
            "provider_responded_at": self.provider_responded_at.isoformat() if self.provider_responded_at else None,
            "customer_accepted_resolution_at": self.customer_accepted_resolution_at.isoformat() if self.customer_accepted_resolution_at else None,
            "resolved_at":          self.resolved_at.isoformat() if self.resolved_at else None,
            "closed_at":            self.closed_at.isoformat() if self.closed_at else None,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
            # SLA + settlement
            "severity":             self.severity,
            "sla_status":           self.sla_status,
            "tenant_first_response_due_at": self.tenant_first_response_due_at.isoformat() if self.tenant_first_response_due_at else None,
            "ai_escalation_at":     self.ai_escalation_at.isoformat() if self.ai_escalation_at else None,
            "admin_escalation_at":  self.admin_escalation_at.isoformat() if self.admin_escalation_at else None,
            "settlement_status":    self.settlement_status,
            "ai_session_id":        str(self.ai_session_id) if self.ai_session_id else None,
        }

    def to_customer_dict(self) -> dict:
        d = self.to_dict()
        d.pop("internal_admin_notes", None)
        return d

    def to_provider_dict(self) -> dict:
        d = self.to_dict()
        d.pop("internal_admin_notes", None)
        return d


class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id   = Column(UUID(as_uuid=True), nullable=False)
    tenant_id      = Column(UUID(as_uuid=True), nullable=True)
    sender_type    = Column(String(20), nullable=False)
    sender_user_id = Column(UUID(as_uuid=True), nullable=True)
    message_text   = Column(Text, nullable=False)
    visibility     = Column(String(30), nullable=False, default="public_to_case")
    created_at     = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at     = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self, viewer: str = "admin") -> dict:
        return {
            "id":             str(self.id),
            "complaint_id":   str(self.complaint_id),
            "tenant_id":      str(self.tenant_id) if self.tenant_id else None,
            "sender_type":    self.sender_type,
            "sender_user_id": str(self.sender_user_id) if self.sender_user_id else None,
            "message_text":   self.message_text,
            "visibility":     self.visibility,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }

    def is_visible_to(self, viewer: str) -> bool:
        if viewer == "admin":
            return True
        if self.visibility == "public_to_case":
            return True
        if self.visibility == "customer_only" and viewer == "customer":
            return True
        if self.visibility == "provider_only" and viewer == "provider":
            return True
        return False


class ComplaintMedia(Base):
    __tablename__ = "complaint_media"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id        = Column(UUID(as_uuid=True), nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    uploaded_by_type    = Column(String(20), nullable=False)
    media_type          = Column(String(20), nullable=False)
    file_url            = Column(String(500), nullable=False)
    file_name           = Column(String(300), nullable=True)
    mime_type           = Column(String(100), nullable=True)
    file_size           = Column(Integer, nullable=True)
    caption             = Column(Text, nullable=True)
    visibility          = Column(String(30), nullable=False, default="public_to_case")
    created_at          = Column(DateTime(timezone=True), nullable=True, default=_now)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "complaint_id":         str(self.complaint_id),
            "uploaded_by_user_id":  str(self.uploaded_by_user_id) if self.uploaded_by_user_id else None,
            "uploaded_by_type":     self.uploaded_by_type,
            "media_type":           self.media_type,
            "file_url":             self.file_url,
            "file_name":            self.file_name,
            "mime_type":            self.mime_type,
            "file_size":            self.file_size,
            "caption":              self.caption,
            "visibility":           self.visibility,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
        }


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id  = Column(UUID(as_uuid=True), nullable=False)
    tenant_id     = Column(UUID(as_uuid=True), nullable=True)
    actor_type    = Column(String(20), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    event_type    = Column(String(60), nullable=False)
    old_status    = Column(String(40), nullable=True)
    new_status    = Column(String(40), nullable=True)
    old_value     = Column(JSONB, nullable=True)
    new_value     = Column(JSONB, nullable=True)
    reason        = Column(Text, nullable=True)
    request_id    = Column(String(100), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=True, default=_now)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "complaint_id":  str(self.complaint_id),
            "tenant_id":     str(self.tenant_id) if self.tenant_id else None,
            "actor_type":    self.actor_type,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "event_type":    self.event_type,
            "old_status":    self.old_status,
            "new_status":    self.new_status,
            "old_value":     self.old_value,
            "new_value":     self.new_value,
            "reason":        self.reason,
            "request_id":    self.request_id,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }


class ComplaintResolution(Base):
    __tablename__ = "complaint_resolutions"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id           = Column(UUID(as_uuid=True), nullable=False)
    tenant_id              = Column(UUID(as_uuid=True), nullable=True)
    resolution_type        = Column(String(40), nullable=False)
    status                 = Column(String(30), nullable=False, default="proposed")
    proposed_by_type       = Column(String(20), nullable=False)
    proposed_by_user_id    = Column(UUID(as_uuid=True), nullable=True)
    description            = Column(Text, nullable=False)
    customer_visible_notes = Column(Text, nullable=True)
    internal_notes         = Column(Text, nullable=True)
    due_date               = Column(Date, nullable=True)
    created_at             = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at             = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                     str(self.id),
            "complaint_id":           str(self.complaint_id),
            "tenant_id":              str(self.tenant_id) if self.tenant_id else None,
            "resolution_type":        self.resolution_type,
            "status":                 self.status,
            "proposed_by_type":       self.proposed_by_type,
            "proposed_by_user_id":    str(self.proposed_by_user_id) if self.proposed_by_user_id else None,
            "description":            self.description,
            "customer_visible_notes": self.customer_visible_notes,
            "due_date":               self.due_date.isoformat() if self.due_date else None,
            "created_at":             self.created_at.isoformat() if self.created_at else None,
            "updated_at":             self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_customer_dict(self) -> dict:
        d = self.to_dict()
        d.pop("internal_notes", None)
        return d


class ServiceReworkRequest(Base):
    __tablename__ = "service_rework_requests"
    __table_args__ = (
        UniqueConstraint("rework_number", name="uq_srr_number"),
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rework_number           = Column(String(40), nullable=False, default=lambda: _num("RWK"))
    complaint_id            = Column(UUID(as_uuid=True), nullable=False)
    booking_id              = Column(UUID(as_uuid=True), nullable=True)
    job_id                  = Column(UUID(as_uuid=True), nullable=True)
    tenant_id               = Column(UUID(as_uuid=True), nullable=False)
    customer_id             = Column(UUID(as_uuid=True), nullable=False)
    original_job_id         = Column(UUID(as_uuid=True), nullable=True)
    assigned_staff_member_id = Column(UUID(as_uuid=True), nullable=True)
    status                  = Column(String(30), nullable=False, default="requested")
    rework_reason           = Column(Text, nullable=False)
    admin_notes             = Column(Text, nullable=True)
    customer_visible_notes  = Column(Text, nullable=True)
    scheduled_date          = Column(Date, nullable=True)
    scheduled_time_window   = Column(String(80), nullable=True)
    completed_at            = Column(DateTime(timezone=True), nullable=True)
    created_at              = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at              = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                       str(self.id),
            "rework_number":            self.rework_number,
            "complaint_id":             str(self.complaint_id),
            "booking_id":               str(self.booking_id) if self.booking_id else None,
            "job_id":                   str(self.job_id) if self.job_id else None,
            "tenant_id":                str(self.tenant_id),
            "customer_id":              str(self.customer_id),
            "original_job_id":          str(self.original_job_id) if self.original_job_id else None,
            "assigned_staff_member_id": str(self.assigned_staff_member_id) if self.assigned_staff_member_id else None,
            "status":                   self.status,
            "rework_reason":            self.rework_reason,
            "customer_visible_notes":   self.customer_visible_notes,
            "scheduled_date":           self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time_window":    self.scheduled_time_window,
            "completed_at":             self.completed_at.isoformat() if self.completed_at else None,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }


class RefundRequest(Base):
    __tablename__ = "refund_requests"
    __table_args__ = (
        UniqueConstraint("refund_number", name="uq_rr_number"),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    refund_number       = Column(String(40), nullable=False, default=lambda: _num("RFD"))
    complaint_id        = Column(UUID(as_uuid=True), nullable=False)
    customer_id         = Column(UUID(as_uuid=True), nullable=False)
    tenant_id           = Column(UUID(as_uuid=True), nullable=True)
    invoice_id          = Column(UUID(as_uuid=True), nullable=True)
    booking_id          = Column(UUID(as_uuid=True), nullable=True)
    job_id              = Column(UUID(as_uuid=True), nullable=True)
    appointment_id      = Column(UUID(as_uuid=True), nullable=True)
    lead_id             = Column(UUID(as_uuid=True), nullable=True)
    status              = Column(String(30), nullable=False, default="requested")
    refund_type         = Column(String(40), nullable=False)
    requested_amount    = Column(Numeric(12,2), nullable=True)
    approved_amount     = Column(Numeric(12,2), nullable=True)
    recorded_amount     = Column(Numeric(12,2), nullable=True)
    currency            = Column(String(10), nullable=False, default="INR")
    refund_method       = Column(String(40), nullable=True)
    reason              = Column(Text, nullable=False)
    rejection_reason    = Column(Text, nullable=True)
    proof_media_url     = Column(String(500), nullable=True)
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    recorded_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    verified_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    approved_at         = Column(DateTime(timezone=True), nullable=True)
    recorded_at         = Column(DateTime(timezone=True), nullable=True)
    verified_at         = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at          = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "refund_number":       self.refund_number,
            "complaint_id":        str(self.complaint_id),
            "customer_id":         str(self.customer_id),
            "tenant_id":           str(self.tenant_id) if self.tenant_id else None,
            "invoice_id":          str(self.invoice_id) if self.invoice_id else None,
            "booking_id":          str(self.booking_id) if self.booking_id else None,
            "job_id":              str(self.job_id) if self.job_id else None,
            "appointment_id":      str(self.appointment_id) if self.appointment_id else None,
            "lead_id":             str(self.lead_id) if self.lead_id else None,
            "status":              self.status,
            "refund_type":         self.refund_type,
            "requested_amount":    str(self.requested_amount) if self.requested_amount else None,
            "approved_amount":     str(self.approved_amount) if self.approved_amount else None,
            "recorded_amount":     str(self.recorded_amount) if self.recorded_amount else None,
            "currency":            self.currency,
            "refund_method":       self.refund_method,
            "reason":              self.reason,
            "rejection_reason":    self.rejection_reason,
            "proof_media_url":     self.proof_media_url,
            "approved_by_user_id": str(self.approved_by_user_id) if self.approved_by_user_id else None,
            "recorded_by_user_id": str(self.recorded_by_user_id) if self.recorded_by_user_id else None,
            "verified_by_user_id": str(self.verified_by_user_id) if self.verified_by_user_id else None,
            "approved_at":         self.approved_at.isoformat() if self.approved_at else None,
            "recorded_at":         self.recorded_at.isoformat() if self.recorded_at else None,
            "verified_at":         self.verified_at.isoformat() if self.verified_at else None,
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_customer_dict(self) -> dict:
        d = self.to_dict()
        d.pop("approved_by_user_id", None)
        d.pop("recorded_by_user_id", None)
        d.pop("verified_by_user_id", None)
        return d


class ComplaintPolicy(Base):
    __tablename__ = "complaint_policies"

    id                           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id                  = Column(UUID(as_uuid=True), nullable=True)
    tenant_id                    = Column(UUID(as_uuid=True), nullable=True)
    policy_key                   = Column(String(80),  nullable=False)
    policy_name                  = Column(String(200), nullable=False)
    allow_customer_complaints    = Column(Boolean, nullable=False, default=True)
    complaint_window_hours       = Column(Integer, nullable=False, default=168)
    allow_duplicate_open_complaints = Column(Boolean, nullable=False, default=False)
    allow_rework                 = Column(Boolean, nullable=False, default=True)
    allow_refund_request         = Column(Boolean, nullable=False, default=True)
    require_admin_review         = Column(Boolean, nullable=False, default=True)
    require_provider_response    = Column(Boolean, nullable=False, default=True)
    default_provider_response_hours = Column(Integer, nullable=False, default=24)
    default_resolution_hours     = Column(Integer, nullable=False, default=72)
    is_active                    = Column(Boolean, nullable=False, default=True)
    created_at                   = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at                   = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                           str(self.id),
            "category_id":                  str(self.category_id) if self.category_id else None,
            "tenant_id":                    str(self.tenant_id) if self.tenant_id else None,
            "policy_key":                   self.policy_key,
            "policy_name":                  self.policy_name,
            "allow_customer_complaints":    self.allow_customer_complaints,
            "complaint_window_hours":       self.complaint_window_hours,
            "allow_duplicate_open_complaints": self.allow_duplicate_open_complaints,
            "allow_rework":                 self.allow_rework,
            "allow_refund_request":         self.allow_refund_request,
            "require_admin_review":         self.require_admin_review,
            "require_provider_response":    self.require_provider_response,
            "default_provider_response_hours": self.default_provider_response_hours,
            "default_resolution_hours":     self.default_resolution_hours,
            "is_active":                    self.is_active,
            "created_at":                   self.created_at.isoformat() if self.created_at else None,
            "updated_at":                   self.updated_at.isoformat() if self.updated_at else None,
        }


# ── Migration 075 — Settlement engine models ──────────────────────────────────

class SettlementProposal(Base):
    __tablename__ = "settlement_proposals"
    __table_args__ = (
        UniqueConstraint("proposal_number", name="uq_sp_number"),
        Index("ix_sp_complaint_id", "complaint_id"),
        Index("ix_sp_status",       "status"),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id        = Column(UUID(as_uuid=True), nullable=False)
    tenant_id           = Column(UUID(as_uuid=True), nullable=True)
    proposal_number     = Column(String(40),  nullable=False, default=lambda: _num("SPR"))
    proposed_by         = Column(String(20),  nullable=False)
    proposed_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    proposal_type       = Column(String(40),  nullable=False)
    proposal_amount     = Column(Numeric(12,2), nullable=True)
    currency            = Column(String(10),  nullable=False, default="INR")
    description         = Column(Text, nullable=False)
    conditions          = Column(Text, nullable=True)
    status              = Column(String(30),  nullable=False, default="proposed")
    customer_response   = Column(String(20),  nullable=True)
    tenant_response     = Column(String(20),  nullable=True)
    customer_responded_at = Column(DateTime(timezone=True), nullable=True)
    tenant_responded_at   = Column(DateTime(timezone=True), nullable=True)
    admin_approved_by   = Column(UUID(as_uuid=True), nullable=True)
    admin_approved_at   = Column(DateTime(timezone=True), nullable=True)
    expires_at          = Column(DateTime(timezone=True), nullable=True)
    ai_generated        = Column(Boolean, nullable=False, default=False)
    ai_confidence_score = Column(Numeric(5,4), nullable=True)
    created_at          = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at          = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "complaint_id":         str(self.complaint_id),
            "tenant_id":            str(self.tenant_id) if self.tenant_id else None,
            "proposal_number":      self.proposal_number,
            "proposed_by":          self.proposed_by,
            "proposed_by_user_id":  str(self.proposed_by_user_id) if self.proposed_by_user_id else None,
            "proposal_type":        self.proposal_type,
            "proposal_amount":      str(self.proposal_amount) if self.proposal_amount else None,
            "currency":             self.currency,
            "description":          self.description,
            "conditions":           self.conditions,
            "status":               self.status,
            "customer_response":    self.customer_response,
            "tenant_response":      self.tenant_response,
            "customer_responded_at":self.customer_responded_at.isoformat() if self.customer_responded_at else None,
            "tenant_responded_at":  self.tenant_responded_at.isoformat() if self.tenant_responded_at else None,
            "admin_approved_by":    str(self.admin_approved_by) if self.admin_approved_by else None,
            "admin_approved_at":    self.admin_approved_at.isoformat() if self.admin_approved_at else None,
            "expires_at":           self.expires_at.isoformat() if self.expires_at else None,
            "ai_generated":         self.ai_generated,
            "ai_confidence_score":  float(self.ai_confidence_score) if self.ai_confidence_score else None,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


class AISettlementSession(Base):
    __tablename__ = "ai_settlement_sessions"
    __table_args__ = (
        Index("ix_ais_complaint_id", "complaint_id"),
        Index("ix_ais_status",       "status"),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id        = Column(UUID(as_uuid=True), nullable=False)
    tenant_id           = Column(UUID(as_uuid=True), nullable=True)
    status              = Column(String(30),  nullable=False, default="started")
    customer_questions  = Column(JSONB, nullable=True)
    customer_answers    = Column(JSONB, nullable=True)
    tenant_questions    = Column(JSONB, nullable=True)
    tenant_answers      = Column(JSONB, nullable=True)
    evidence_summary    = Column(Text, nullable=True)
    ai_recommendation   = Column(Text, nullable=True)
    risk_flags          = Column(JSONB, nullable=True)
    confidence_score    = Column(Numeric(5,4), nullable=True)
    model_used          = Column(String(100), nullable=True)
    prompt_tokens       = Column(Integer, nullable=True)
    completion_tokens   = Column(Integer, nullable=True)
    started_at          = Column(DateTime(timezone=True), nullable=True, default=_now)
    completed_at        = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at          = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "complaint_id":       str(self.complaint_id),
            "tenant_id":          str(self.tenant_id) if self.tenant_id else None,
            "status":             self.status,
            "customer_questions": self.customer_questions,
            "customer_answers":   self.customer_answers,
            "tenant_questions":   self.tenant_questions,
            "tenant_answers":     self.tenant_answers,
            "evidence_summary":   self.evidence_summary,
            "ai_recommendation":  self.ai_recommendation,
            "risk_flags":         self.risk_flags,
            "confidence_score":   float(self.confidence_score) if self.confidence_score else None,
            "model_used":         self.model_used,
            "started_at":         self.started_at.isoformat() if self.started_at else None,
            "completed_at":       self.completed_at.isoformat() if self.completed_at else None,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
            "updated_at":         self.updated_at.isoformat() if self.updated_at else None,
        }
