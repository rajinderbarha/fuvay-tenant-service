"""Field Ops Engine — Models (4 tables). 23-status lifecycle."""
import uuid, secrets
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Job(ServiceOSBase):
    """Core job entity. Status transitions enforced by service layer."""
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_job_tenant_status",  "tenant_id", "status"),
        Index("ix_job_staff",          "assigned_staff_id"),
        Index("ix_job_customer",       "customer_id"),
        Index("ix_job_booking",        "booking_id"),
        Index("ix_job_scheduled_at",   "scheduled_at"),
        Index("ix_job_type",           "job_type"),
        Index("ix_job_city_zip",       "city", "zipcode"),
        Index("ix_job_parent",         "parent_job_id"),
        Index("ix_job_quote",          "quote_id"),
        Index("ix_job_tenant_type_status", "tenant_id", "job_type", "status"),
        Index("ix_job_invoice",        "invoice_id"),
        Index("ix_job_payment",        "payment_id"),
    )

    tenant_id:          Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:         Mapped[str|None]      = mapped_column(String(100), nullable=True)
    customer_id:        Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    assigned_staff_id:  Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    # Serviceability fields (Step 5) — copied from booking at conversion time
    address_id:                    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:                    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    city:                          Mapped[str|None]       = mapped_column(String(100), nullable=True)
    zipcode:                       Mapped[str|None]       = mapped_column(String(20), nullable=True)
    matched_service_area_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    matched_service_area_service_id:Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    coverage_match_level:          Mapped[str|None]       = mapped_column(String(20), nullable=True)
    estimated_price:               Mapped[Decimal|None]   = mapped_column(Numeric(10,2), nullable=True)
    sla_minutes:                   Mapped[int|None]       = mapped_column(Integer, nullable=True)
    source:                        Mapped[str]            = mapped_column(String(30), default="direct", nullable=False)
    service_type_id:    Mapped[str]           = mapped_column(String(100), nullable=False)
    service_category:   Mapped[str]           = mapped_column(String(100), nullable=False)
    job_type:           Mapped[str]           = mapped_column(String(20), default="repair", nullable=False)
    parent_job_id:      Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    findings:            Mapped[str|None]     = mapped_column(Text, nullable=True)
    recommendation:      Mapped[str|None]     = mapped_column(Text, nullable=True)
    checklist:           Mapped[list]         = mapped_column(JSONB, default=list, nullable=False)
    duration_estimate_minutes: Mapped[int|None] = mapped_column(Integer, nullable=True)
    status:             Mapped[str]           = mapped_column(String(40), default="draft", nullable=False)
    job_number:         Mapped[str]           = mapped_column(String(30), nullable=False, unique=True)
    title:              Mapped[str]           = mapped_column(String(255), nullable=False)
    description:        Mapped[str|None]      = mapped_column(Text, nullable=True)
    address:            Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    pincode:            Mapped[str|None]      = mapped_column(String(20), nullable=True)
    latitude:           Mapped[float|None]    = mapped_column(Float, nullable=True)
    longitude:          Mapped[float|None]    = mapped_column(Float, nullable=True)
    scheduled_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at:         Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    quoted_price:       Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    final_price:        Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    # Customer Service Credit propagated from Booking at conversion time (migration 093).
    # payable_amount is the authoritative "collect from customer" figure for staff/tenant/admin.
    credit_applied:     Mapped[Decimal]       = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    payable_amount:     Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    commission_deducted:Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    commission_amount:  Mapped[Decimal|None]  = mapped_column(Numeric(10,4), nullable=True)
    # Step 9 — payment / invoice / commission closure
    invoice_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    commission_id:        Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invoice_generated_at: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    payment_pending_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at:              Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    closure_notes:        Mapped[str|None]       = mapped_column(Text, nullable=True)
    final_payable_amount: Mapped[Decimal|None]   = mapped_column(Numeric(10,2), nullable=True)
    sla_breach:         Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    # Step 6 — assignment + staff lifecycle
    assigned_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by_user_id:Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    accepted_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_rejection_reason: Mapped[str|None]  = mapped_column(String(500), nullable=True)
    en_route_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at:         Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_started_at:    Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_completed_at:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason:Mapped[str|None]      = mapped_column(String(500), nullable=True)
    status_updated_at:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    minutes_in_status:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    sla_breached:       Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    sla_breach_level:   Mapped[str|None]      = mapped_column(String(20), nullable=True)
    current_status_started_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    closing_notes:      Mapped[str|None]      = mapped_column(Text, nullable=True)
    # Step 7 — job-type-specific routing (repair / service / consultation)
    quote_required:     Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    quote_id:           Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    pre_approval_limit: Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    assessment_findings:Mapped[str|None]      = mapped_column(Text, nullable=True)
    recommended_work:   Mapped[str|None]      = mapped_column(Text, nullable=True)
    estimated_parts:    Mapped[list]          = mapped_column(JSONB, default=list, nullable=False)
    assessment_completed_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    quote_sent_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    quote_approved_at:   Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    quote_rejected_at:   Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    quote_rejection_reason: Mapped[str|None]  = mapped_column(Text, nullable=True)
    checklist_required: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    checklist_started_at:   Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    checklist_completed_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_from_consultation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    customer_token:     Mapped[str]           = mapped_column(String(64), nullable=False,
                                                              default=lambda: secrets.token_hex(32))
    customer_rating:    Mapped[float|None]    = mapped_column(Float, nullable=True)
    meta:               Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    tags:               Mapped[list]          = mapped_column(JSONB, default=list, nullable=False)


class JobStatusHistory(ServiceOSBase):
    """APPEND-ONLY. Every status transition recorded. Full job lifecycle always queryable."""
    __tablename__ = "job_status_history"
    __table_args__ = (Index("ix_jsh_job_id", "job_id"),
                      Index("ix_jsh_tenant", "tenant_id"))

    job_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status:    Mapped[str|None]  = mapped_column(String(40), nullable=True)
    to_status:      Mapped[str]       = mapped_column(String(40), nullable=False)
    changed_by:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    changed_by_role:Mapped[str|None]  = mapped_column(String(30), nullable=True)
    reason:         Mapped[str|None]  = mapped_column(String(500), nullable=True)
    lat:            Mapped[float|None]= mapped_column(Float, nullable=True)
    lng:            Mapped[float|None]= mapped_column(Float, nullable=True)
    meta:           Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)


class JobNote(ServiceOSBase):
    """Staff or system notes attached to a job."""
    __tablename__ = "job_notes"
    __table_args__ = (Index("ix_jn_job_id", "job_id"),)

    job_id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    author_id:  Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    author_role:Mapped[str|None]  = mapped_column(String(30), nullable=True)
    note_type:  Mapped[str]       = mapped_column(String(30), default="staff_note", nullable=False)
    content:    Mapped[str]       = mapped_column(Text, nullable=False)
    status_at:  Mapped[str|None]  = mapped_column(String(40), nullable=True)
    is_internal:Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)


class JobMedia(ServiceOSBase):
    """Media attachments per status checkpoint."""
    __tablename__ = "job_media"
    __table_args__ = (Index("ix_jm_job_id", "job_id"),)

    job_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:  Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    media_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    uploaded_by:Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    status_at:  Mapped[str|None]      = mapped_column(String(40), nullable=True)
    media_type: Mapped[str]           = mapped_column(String(30), default="photo", nullable=False)
    caption:    Mapped[str|None]      = mapped_column(String(255), nullable=True)
    storage_key:Mapped[str|None]      = mapped_column(String(500), nullable=True)


class JobQuote(ServiceOSBase):
    """Assessment-driven price quote awaiting customer approve/reject.
    Used by repair jobs (quote if needed) and consultation jobs (quote always).
    Step 7 extends this with the richer line-item fields from the spec while
    keeping the original amount/parts/labour_estimate fields for the legacy
    create_quote/respond_to_quote flow (Phase 7) intact."""
    __tablename__ = "job_quotes"
    __table_args__ = (Index("ix_jq_job_id", "job_id"),
                      Index("ix_jq_tenant", "tenant_id"),
                      Index("ix_jq_customer", "customer_id"),
                      Index("ix_jq_status", "status"),
                      Index("ix_jq_expires_at", "expires_at"))

    job_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    amount:      Mapped[Decimal]        = mapped_column(Numeric(10, 2), nullable=False)
    parts:       Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    labour_estimate: Mapped[Decimal|None] = mapped_column(Numeric(10, 2), nullable=True)
    line_items:  Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    findings_snapshot:       Mapped[str|None] = mapped_column(Text, nullable=True)
    recommendation_snapshot: Mapped[str|None] = mapped_column(Text, nullable=True)
    notes:       Mapped[str|None]       = mapped_column(Text, nullable=True)
    status:      Mapped[str]            = mapped_column(String(20), default="pending", nullable=False)
    created_by:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at:  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at:Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    # Step 7 — richer line-item quote fields
    quote_number:        Mapped[str|None] = mapped_column(String(40), nullable=True, unique=True)
    quote_type:          Mapped[str]      = mapped_column(String(30), default="repair_quote", nullable=False)
    recommended_work:    Mapped[str|None] = mapped_column(Text, nullable=True)
    labour_amount:       Mapped[Decimal]  = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    parts_amount:        Mapped[Decimal]  = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    visit_fee:            Mapped[Decimal] = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    discount_amount:      Mapped[Decimal] = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    tax_amount:           Mapped[Decimal] = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    total_amount:         Mapped[Decimal|None] = mapped_column(Numeric(10,2), nullable=True)
    pre_approval_limit:   Mapped[Decimal|None] = mapped_column(Numeric(10,2), nullable=True)
    requires_customer_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sent_at:              Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason:     Mapped[str|None] = mapped_column(Text, nullable=True)
    created_by_staff_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by_customer_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


# ── Step 8: Service Checklist (templates + per-job execution) ────────────────
class ServiceChecklistTemplate(ServiceOSBase):
    """Tenant-owned checklist template for a given catalog service."""
    __tablename__ = "service_checklist_templates"
    __table_args__ = (Index("ix_sct_tenant_service", "tenant_id", "service_id"),)

    tenant_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    service_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name:        Mapped[str]       = mapped_column(String(255), nullable=False)
    description: Mapped[str|None]  = mapped_column(Text, nullable=True)
    is_active:   Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


class ServiceChecklistItem(ServiceOSBase):
    """A single checklist line item belonging to a template."""
    __tablename__ = "service_checklist_items"
    __table_args__ = (Index("ix_sci_template_id", "template_id"),)

    template_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title:           Mapped[str]      = mapped_column(String(255), nullable=False)
    description:     Mapped[str|None] = mapped_column(Text, nullable=True)
    sort_order:       Mapped[int]     = mapped_column(Integer, default=0, nullable=False)
    is_required:      Mapped[bool]    = mapped_column(Boolean, default=True, nullable=False)
    requires_photo:   Mapped[bool]    = mapped_column(Boolean, default=False, nullable=False)
    requires_note:    Mapped[bool]    = mapped_column(Boolean, default=False, nullable=False)
    is_active:        Mapped[bool]    = mapped_column(Boolean, default=True, nullable=False)
    deleted_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobChecklistItem(ServiceOSBase):
    """A checklist item instance copied onto a specific job at execution time —
    survives template edits/deletes since it's the historical record."""
    __tablename__ = "job_checklist_items"
    __table_args__ = (Index("ix_jci_job_id", "job_id"),
                      Index("ix_jci_tenant_job", "tenant_id", "job_id"))

    job_id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    template_item_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title:              Mapped[str]       = mapped_column(String(255), nullable=False)
    description:        Mapped[str|None]  = mapped_column(Text, nullable=True)
    sort_order:         Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    is_required:        Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    requires_photo:     Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    requires_note:      Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    is_completed:       Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    completed_by_staff_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_at:       Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes:              Mapped[str|None]  = mapped_column(Text, nullable=True)
    photo_urls:         Mapped[list]      = mapped_column(JSONB, default=list, nullable=False)
