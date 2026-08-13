"""Sprint 19 — Final record SQLAlchemy models (6 tables)."""
from __future__ import annotations
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class ServiceBooking(ServiceOSBase):
    """Final home service booking created from a confirmed draft."""
    __tablename__ = "service_bookings"
    __table_args__ = (
        Index("ix_sb_booking_number", "booking_number", unique=True),
        Index("ix_sb_draft_id",       "draft_id",       unique=True),
        Index("ix_sb_customer_id",    "customer_id"),
        Index("ix_sb_tenant_id",      "tenant_id"),
        Index("ix_sb_status",         "status"),
        Index("ix_sb_customer_created", "customer_id", "created_at"),
        Index("ix_sb_tenant_customer_created", "tenant_id", "customer_id", "created_at"),
    )

    booking_number:        Mapped[str]              = mapped_column(String(30), nullable=False)
    draft_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 (migration 168) -- exact
    # selected Job Type, copied from the booking draft at confirmation and
    # never accepted from the confirmation payload itself. Compatibility
    # field: nullable because one Master Service legitimately has multiple
    # Job Types and legacy/undecided drafts may have none -- callers must
    # treat null as unresolved, never assume a default.
    job_type_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (migration 171) -- the exact
    # catalog link and the exact IMMUTABLE workflow-version row snapshotted
    # from the draft at finalize() time. Copied once, never re-resolved --
    # an admin publishing a new blueprint version must not change this
    # booking's requirements after the fact.
    master_service_job_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_job_workflow_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    selected_problem_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ai_session_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_name:         Mapped[str | None]       = mapped_column(String(200), nullable=True)
    customer_phone:        Mapped[str | None]       = mapped_column(String(30),  nullable=True)
    city:                  Mapped[str | None]       = mapped_column(String(100), nullable=True)
    zipcode:               Mapped[str | None]       = mapped_column(String(20),  nullable=True)
    address_snapshot:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    preferred_date:        Mapped[date | None]      = mapped_column(Date(), nullable=True)
    preferred_time_window: Mapped[str | None]       = mapped_column(String(50), nullable=True)
    price_snapshot:        Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    provider_snapshot:     Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    issue_summary:         Mapped[str | None]       = mapped_column(Text(), nullable=True)
    issue_details:         Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    # migration 222 BOOKING-DETAILS-CONTRACT-FIXES -- found missing during
    # the "make it 100% working" drift audit.
    answer_snapshot:       Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    # ── Urgency ────────────────────────────────────────────────────────────
    # `emergency_surcharge` is FROZEN at confirmation, not a live read of
    # tenant_services.tenant_emergency_surcharge -- a tenant changing their
    # rate later must never alter what an already-confirmed customer owes.
    is_emergency:          Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    emergency_surcharge:   Mapped[Decimal | None]   = mapped_column(Numeric(12, 2), nullable=True)
    status:                Mapped[str]              = mapped_column(String(40), nullable=False, default="pending_assignment")
    assignment_status:     Mapped[str]              = mapped_column(String(30), nullable=False, default="unassigned")
    failure_reason:        Mapped[str | None]       = mapped_column(Text(), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                    str(self.id),
            "booking_number":        self.booking_number,
            "draft_id":              str(self.draft_id),
            "customer_id":           str(self.customer_id) if self.customer_id else None,
            "tenant_id":             str(self.tenant_id)   if self.tenant_id   else None,
            "category_id":           str(self.category_id),
            "offering_id":           str(self.offering_id),
            "job_type_id":           str(self.job_type_id) if self.job_type_id else None,
            "master_service_job_type_id": str(self.master_service_job_type_id) if self.master_service_job_type_id else None,
            "service_job_workflow_id":    str(self.service_job_workflow_id) if self.service_job_workflow_id else None,
            "selected_problem_id":        str(self.selected_problem_id) if self.selected_problem_id else None,
            "ai_session_id":         str(self.ai_session_id) if self.ai_session_id else None,
            "customer_name":         self.customer_name,
            "customer_phone":        self.customer_phone,
            "city":                  self.city,
            "zipcode":               self.zipcode,
            "address_snapshot":      self.address_snapshot,
            "preferred_date":        self.preferred_date.isoformat() if self.preferred_date else None,
            "preferred_time_window": self.preferred_time_window,
            "price_snapshot":        self.price_snapshot,
            "provider_snapshot":     self.provider_snapshot,
            "issue_summary":         self.issue_summary,
            "issue_details":         self.issue_details,
            # Real bug fixed here: this column is what the customer's booking
            # page renders as "what you told us", but it was never included
            # in the payload -- so even once populated it could not reach the
            # client and the section stayed empty.
            "answer_snapshot":       self.answer_snapshot,
            "is_emergency":          bool(self.is_emergency),
            "emergency_surcharge":   str(self.emergency_surcharge) if self.emergency_surcharge is not None else None,
            "status":                self.status,
            "assignment_status":     self.assignment_status,
            "failure_reason":        self.failure_reason,
            "created_at":            self.created_at.isoformat() if self.created_at else None,
            "updated_at":            self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceJob(ServiceOSBase):
    """Field job created alongside a ServiceBooking (one-to-one initially)."""
    __tablename__ = "service_jobs"
    __table_args__ = (
        Index("ix_sj_job_number",  "job_number",  unique=True),
        Index("ix_sj_booking_id",  "booking_id"),
        Index("ix_sj_customer_id", "customer_id"),
        Index("ix_sj_tenant_id",   "tenant_id"),
        Index("ix_sj_staff_status_created", "assigned_staff_id", "status", "created_at"),
        Index("ix_sj_status",      "status"),
        Index("ix_sj_created",     "created_at"),
        Index("ix_sj_tenant_created", "tenant_id", "created_at"),
        Index("ix_sj_customer_status_updated", "customer_id", "status", "updated_at"),
        Index("ix_sj_tenant_customer_status_updated", "tenant_id", "customer_id", "status", "updated_at"),
    )

    job_number:             Mapped[str]              = mapped_column(String(30), nullable=False)
    booking_id:             Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 (migration 168) -- the
    # AUTHORITATIVE Job Type for execution/quote workflow resolution. Copied
    # from ServiceBooking.job_type_id at creation; never mutated afterward
    # (no endpoint accepts a job_type_id on an existing job). Null means
    # unresolved -- the execution guard must fail closed, never guess.
    job_type_id:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (migration 171) -- the exact
    # IMMUTABLE workflow-version row this job's approval requirement resolves
    # against, copied from the booking at creation. The execution resolver
    # reads THIS id directly (never re-derives from offering_id+job_type_id
    # live), so an admin publishing a new blueprint version can never change
    # an in-progress job's requirements.
    master_service_job_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_job_workflow_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    selected_problem_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_staff_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scheduled_date:         Mapped[date | None]      = mapped_column(Date(), nullable=True)
    scheduled_time_window:  Mapped[str | None]       = mapped_column(String(50), nullable=True)
    city:                   Mapped[str | None]       = mapped_column(String(100), nullable=True)
    zipcode:                Mapped[str | None]       = mapped_column(String(20),  nullable=True)
    address_snapshot:       Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    status:                 Mapped[str]              = mapped_column(String(40), nullable=False, default="pending_assignment")
    assignment_status:      Mapped[str]              = mapped_column(String(30), nullable=False, default="unassigned")
    failure_reason:         Mapped[str | None]       = mapped_column(Text(), nullable=True)
    # HS8B — single validated completion action's payload (work summary,
    # collected amount, payment mode, photo ids, technician note). Never
    # mutated by anything except POST .../complete. HS9 reads this to
    # perform usage-credit deduction — this sprint only prepares it.
    completion_data:        Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    # CANCEL-RESCHEDULE-FOUNDATION (migration 224) -- count of customer-
    # initiated reschedules against this job, capped by MAX_RESCHEDULE_COUNT
    # in home_service_assignment.constants. Never decremented.
    reschedule_count:       Mapped[int]              = mapped_column(Integer, nullable=False, default=0)
    # Copied from the booking at creation so the provider's dashboard can sort
    # urgent work first without joining back to the booking on every query.
    is_emergency:           Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            "id":                    str(self.id),
            "job_number":            self.job_number,
            "is_emergency":          bool(self.is_emergency),
            "booking_id":            str(self.booking_id),
            "customer_id":           str(self.customer_id) if self.customer_id else None,
            "tenant_id":             str(self.tenant_id)   if self.tenant_id   else None,
            "category_id":           str(self.category_id),
            "offering_id":           str(self.offering_id),
            "job_type_id":           str(self.job_type_id) if self.job_type_id else None,
            "master_service_job_type_id": str(self.master_service_job_type_id) if self.master_service_job_type_id else None,
            "service_job_workflow_id":    str(self.service_job_workflow_id) if self.service_job_workflow_id else None,
            "selected_problem_id":        str(self.selected_problem_id) if self.selected_problem_id else None,
            "assigned_staff_id":     str(self.assigned_staff_id) if self.assigned_staff_id else None,
            "scheduled_date":        self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time_window": self.scheduled_time_window,
            "city":                  self.city,
            "zipcode":               self.zipcode,
            "address_snapshot":      self.address_snapshot,
            "status":                self.status,
            "assignment_status":     self.assignment_status,
            "failure_reason":        self.failure_reason,
            "completion_data":       self.completion_data,
            "reschedule_count":      self.reschedule_count,
            "created_at":            self.created_at.isoformat() if self.created_at else None,
            "updated_at":            self.updated_at.isoformat() if self.updated_at else None,
        }


class CoachingAppointment(ServiceOSBase):
    """Final coaching appointment created from a confirmed draft."""
    __tablename__ = "coaching_appointments"
    __table_args__ = (
        Index("ix_ca_appointment_number", "appointment_number", unique=True),
        Index("ix_ca_draft_id",           "draft_id",           unique=True),
        Index("ix_ca_customer_id",        "customer_id"),
        Index("ix_ca_tenant_id",          "tenant_id"),
        Index("ix_ca_status",             "status"),
    )

    appointment_number:       Mapped[str]              = mapped_column(String(30), nullable=False)
    draft_id:                 Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:                Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    ai_session_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    staff_member_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    student_name:             Mapped[str | None]       = mapped_column(String(200), nullable=True)
    student_phone:            Mapped[str | None]       = mapped_column(String(30),  nullable=True)
    student_email:            Mapped[str | None]       = mapped_column(String(255), nullable=True)
    target_exam:              Mapped[str | None]       = mapped_column(String(100), nullable=True)
    target_band:              Mapped[str | None]       = mapped_column(String(20),  nullable=True)
    preferred_mode:           Mapped[str | None]       = mapped_column(String(20),  nullable=True)
    selected_date:            Mapped[date | None]      = mapped_column(Date(), nullable=True)
    selected_time_start:      Mapped[time | None]      = mapped_column(Time(), nullable=True)
    selected_time_end:        Mapped[time | None]      = mapped_column(Time(), nullable=True)
    city:                     Mapped[str | None]       = mapped_column(String(100), nullable=True)
    appointment_fee_snapshot: Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    provider_snapshot:        Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    status:                   Mapped[str]              = mapped_column(String(40), nullable=False, default="confirmed")
    failure_reason:           Mapped[str | None]       = mapped_column(Text(), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                       str(self.id),
            "appointment_number":       self.appointment_number,
            "draft_id":                 str(self.draft_id),
            "customer_id":              str(self.customer_id) if self.customer_id else None,
            "tenant_id":                str(self.tenant_id)   if self.tenant_id   else None,
            "category_id":              str(self.category_id),
            "offering_id":              str(self.offering_id),
            "ai_session_id":            str(self.ai_session_id) if self.ai_session_id else None,
            "staff_member_id":          str(self.staff_member_id) if self.staff_member_id else None,
            "student_name":             self.student_name,
            "student_phone":            self.student_phone,
            "student_email":            self.student_email,
            "target_exam":              self.target_exam,
            "target_band":              self.target_band,
            "preferred_mode":           self.preferred_mode,
            "selected_date":            self.selected_date.isoformat() if self.selected_date else None,
            "selected_time_start":      self.selected_time_start.isoformat() if self.selected_time_start else None,
            "selected_time_end":        self.selected_time_end.isoformat() if self.selected_time_end else None,
            "city":                     self.city,
            "appointment_fee_snapshot": self.appointment_fee_snapshot,
            "provider_snapshot":        self.provider_snapshot,
            "status":                   self.status,
            "failure_reason":           self.failure_reason,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }


class RealEstateLead(ServiceOSBase):
    """Final real estate lead created from a confirmed draft."""
    __tablename__ = "real_estate_leads"
    __table_args__ = (
        Index("ix_rel_lead_number", "lead_number",  unique=True),
        Index("ix_rel_draft_id",    "draft_id",     unique=True),
        Index("ix_rel_customer_id", "customer_id"),
        Index("ix_rel_tenant_id",   "tenant_id"),
        Index("ix_rel_status",      "status"),
        Index("ix_rel_city_intent", "city", "lead_intent"),
    )

    lead_number:            Mapped[str]              = mapped_column(String(30), nullable=False)
    draft_id:               Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    agent_id:               Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    ai_session_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lead_intent:            Mapped[str | None]       = mapped_column(String(40),  nullable=True)
    property_type:          Mapped[str | None]       = mapped_column(String(40),  nullable=True)
    city:                   Mapped[str | None]       = mapped_column(String(100), nullable=True)
    locality:               Mapped[str | None]       = mapped_column(String(150), nullable=True)
    zipcode:                Mapped[str | None]       = mapped_column(String(20),  nullable=True)
    budget_min:             Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    budget_max:             Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    rent_min:               Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    rent_max:               Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    customer_snapshot:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    requirement_snapshot:   Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    lead_score_snapshot:    Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    provider_snapshot:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    fallback_payload:       Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    status:                 Mapped[str]              = mapped_column(String(40), nullable=False, default="new")
    failure_reason:         Mapped[str | None]       = mapped_column(Text(), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "lead_number":          self.lead_number,
            "draft_id":             str(self.draft_id),
            "customer_id":          str(self.customer_id) if self.customer_id else None,
            "tenant_id":            str(self.tenant_id)   if self.tenant_id   else None,
            "agent_id":             str(self.agent_id)    if self.agent_id    else None,
            "category_id":          str(self.category_id),
            "offering_id":          str(self.offering_id),
            "ai_session_id":        str(self.ai_session_id) if self.ai_session_id else None,
            "lead_intent":          self.lead_intent,
            "property_type":        self.property_type,
            "city":                 self.city,
            "locality":             self.locality,
            "zipcode":              self.zipcode,
            "budget_min":           float(self.budget_min) if self.budget_min is not None else None,
            "budget_max":           float(self.budget_max) if self.budget_max is not None else None,
            "rent_min":             float(self.rent_min)   if self.rent_min   is not None else None,
            "rent_max":             float(self.rent_max)   if self.rent_max   is not None else None,
            "customer_snapshot":    self.customer_snapshot,
            "requirement_snapshot": self.requirement_snapshot,
            "lead_score_snapshot":  self.lead_score_snapshot,
            "provider_snapshot":    self.provider_snapshot,
            "fallback_payload":     self.fallback_payload,
            "status":               self.status,
            "failure_reason":       self.failure_reason,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


class CustomerBookingConfirmation(ServiceOSBase):
    """Idempotency record: one row per confirmed draft, prevents double creation."""
    __tablename__ = "customer_booking_confirmations"
    __table_args__ = (
        UniqueConstraint("draft_type", "draft_id", name="uq_cbc_draft_type_draft_id"),
        Index("ix_cbc_customer_id",     "customer_id"),
        Index("ix_cbc_idempotency_key", "idempotency_key"),
        Index("ix_cbc_draft_id",        "draft_id"),
    )

    customer_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    draft_type:       Mapped[str]              = mapped_column(String(30), nullable=False)
    draft_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_key:  Mapped[str | None]       = mapped_column(String(200), nullable=True)
    result_type:      Mapped[str | None]       = mapped_column(String(40), nullable=True)
    result_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result_number:    Mapped[str | None]       = mapped_column(String(30), nullable=True)
    status:           Mapped[str]              = mapped_column(String(20), nullable=False, default="created")
    failure_reason:   Mapped[str | None]       = mapped_column(Text(), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":               str(self.id),
            "customer_id":      str(self.customer_id) if self.customer_id else None,
            "draft_type":       self.draft_type,
            "draft_id":         str(self.draft_id),
            "idempotency_key":  self.idempotency_key,
            "result_type":      self.result_type,
            "result_id":        str(self.result_id) if self.result_id else None,
            "result_number":    self.result_number,
            "status":           self.status,
            "failure_reason":   self.failure_reason,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }


class FinalCreationAuditLog(ServiceOSBase):
    """Immutable audit log for every final record creation attempt."""
    __tablename__ = "final_creation_audit_logs"
    __table_args__ = (
        Index("ix_fcal_draft_id",    "draft_id"),
        Index("ix_fcal_customer_id", "customer_id"),
        Index("ix_fcal_action",      "action"),
        Index("ix_fcal_created_at",  "created_at"),
    )

    action:        Mapped[str]              = mapped_column(String(60), nullable=False)
    draft_type:    Mapped[str | None]       = mapped_column(String(30), nullable=True)
    draft_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result_type:   Mapped[str | None]       = mapped_column(String(40), nullable=True)
    result_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result_number: Mapped[str | None]       = mapped_column(String(30), nullable=True)
    customer_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_id:    Mapped[str | None]       = mapped_column(String(100), nullable=True)
    details:       Mapped[dict | None]      = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "action":        self.action,
            "draft_type":    self.draft_type,
            "draft_id":      str(self.draft_id) if self.draft_id else None,
            "result_type":   self.result_type,
            "result_id":     str(self.result_id) if self.result_id else None,
            "result_number": self.result_number,
            "customer_id":   str(self.customer_id) if self.customer_id else None,
            "tenant_id":     str(self.tenant_id)   if self.tenant_id   else None,
            "request_id":    self.request_id,
            "details":       self.details,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }
