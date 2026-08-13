"""Sprint 16 — Home Service Booking Draft: SQLAlchemy models (2 tables)."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class HomeServiceBookingDraft(ServiceOSBase):
    """
    Pre-booking chatbot draft. Collects required fields via AI chat,
    validates serviceability, estimates price, matches providers, and
    holds a booking-ready payload for Sprint 19 final job creation.

    Backend is source of truth. DeepSeek only collects field values.
    """
    __tablename__ = "home_service_booking_drafts"
    __table_args__ = (
        Index("ix_hsbd_customer_id",       "customer_id"),
        Index("ix_hsbd_ai_session_id",     "ai_session_id"),
        Index("ix_hsbd_status",            "status"),
        Index("ix_hsbd_offering_id",       "offering_id"),
        Index("ix_hsbd_category_offering", "category_id", "offering_id"),
        Index("ix_hsbd_city_zipcode",      "city", "zipcode"),
        Index("ix_hsbd_selected_tenant",   "selected_tenant_id"),
        Index("ix_hsbd_status_created",     "status", "created_at"),
        Index("ix_hsbd_tenant_status_created", "selected_tenant_id", "status", "created_at"),
    )

    # ── Linkage ────────────────────────────────────────────────────────────────
    customer_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    guest_session_id: Mapped[str | None]       = mapped_column(String(100), nullable=True)
    ai_session_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Catalog ────────────────────────────────────────────────────────────────
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 (migration 168) -- the exact Job
    # Type selected for this Master Service (Repair / Installation /
    # Uninstallation / General Service, etc.). Nullable: legacy drafts and
    # any draft where the customer has not yet selected a job type have no
    # value here, and MUST be treated as unresolved (fail-closed) rather than
    # guessed -- one Master Service legitimately has multiple Job Types, each
    # with its own ServiceJobWorkflow (e.g. Repair requires quote approval,
    # Installation does not). Validated against MasterServiceJobType
    # (belongs to offering_id, is_active) in update_draft_fields.
    job_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (migration 171) -- the exact
    # catalog link and the exact (immutable, versioned) workflow row
    # snapshotted at the moment Job Type was resolved. selected_problem_id
    # is the customer's Problem/Intent selection (ServiceIssueMapping) that
    # drove the resolution, when the customer went through the problem-first
    # flow rather than a direct action (Install/Uninstall/General Service).
    master_service_job_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_job_workflow_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    selected_problem_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Provider ───────────────────────────────────────────────────────────────
    selected_tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Status ─────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    # ── Customer identity ──────────────────────────────────────────────────────
    customer_name:  Mapped[str | None] = mapped_column(String(150), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(30),  nullable=True)

    # ── Address ────────────────────────────────────────────────────────────────
    address_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    address_snapshot: Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    city:    Mapped[str | None] = mapped_column(String(100), nullable=True)
    zipcode: Mapped[str | None] = mapped_column(String(20),  nullable=True)

    # ── Issue ──────────────────────────────────────────────────────────────────
    issue_summary: Mapped[str | None]  = mapped_column(Text,  nullable=True)
    issue_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Sprint 34E: structured issue + option IDs
    issue_type_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_option_ids_json: Mapped[list | None]     = mapped_column(JSONB, nullable=True)
    # migration 222 BOOKING-DETAILS-CONTRACT-FIXES -- found missing from
    # this model during the "make it 100% working" drift audit.
    catalog_question_answers: Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    # Migration 220 defines this as a NOT NULL Integer version counter
    # (server_default 1) -- was mis-typed here as a nullable String(30),
    # which made every INSERT send an explicit NULL cast to VARCHAR against
    # an Integer column, failing with DatatypeMismatchError on every single
    # booking-draft creation across every category (not specific to any one
    # service).
    question_flow_version:   Mapped[int]             = mapped_column(Integer, nullable=False, default=1)

    # ── Offering variant ───────────────────────────────────────────────────────
    offering_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Urgency ────────────────────────────────────────────────────────────────
    # Set when the customer picks a slot from the emergency (notice-period
    # waived) list, so the surcharge and the provider's urgent-first sort have
    # a real, persisted fact to work from rather than a transient query param.
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Media ──────────────────────────────────────────────────────────────────
    photo_urls: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    preferred_date:        Mapped[date | None] = mapped_column(Date,        nullable=True)
    preferred_time_window: Mapped[str | None]  = mapped_column(String(50),  nullable=True)

    # ── Serviceability ────────────────────────────────────────────────────────
    serviceability_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # ── Price ─────────────────────────────────────────────────────────────────
    price_status:     Mapped[str | None]  = mapped_column(String(30), nullable=True)
    pricing_rule_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    price_snapshot:   Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Provider matching ─────────────────────────────────────────────────────
    provider_match_status:       Mapped[str | None]  = mapped_column(String(30), nullable=True)
    provider_override_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    provider_options:            Mapped[list | None] = mapped_column(JSONB, nullable=True)
    selected_provider_snapshot:  Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Booking summary ───────────────────────────────────────────────────────
    booking_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Failure ───────────────────────────────────────────────────────────────
    failure_code:    Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text,        nullable=True)

    # ── Expiry ────────────────────────────────────────────────────────────────
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                         str(self.id),
            "customer_id":               str(self.customer_id)     if self.customer_id     else None,
            "guest_session_id":          self.guest_session_id,
            "ai_session_id":             str(self.ai_session_id)   if self.ai_session_id   else None,
            "category_id":               str(self.category_id),
            "offering_id":               str(self.offering_id),
            "job_type_id":               str(self.job_type_id) if self.job_type_id else None,
            "master_service_job_type_id":str(self.master_service_job_type_id) if self.master_service_job_type_id else None,
            "service_job_workflow_id":   str(self.service_job_workflow_id) if self.service_job_workflow_id else None,
            "selected_problem_id":       str(self.selected_problem_id) if self.selected_problem_id else None,
            "selected_tenant_id":        str(self.selected_tenant_id) if self.selected_tenant_id else None,
            "status":                    self.status,
            "customer_name":             self.customer_name,
            "customer_phone":            self.customer_phone,
            "address_id":                str(self.address_id) if self.address_id else None,
            "address_snapshot":          self.address_snapshot,
            "city":                      self.city,
            "zipcode":                   self.zipcode,
            "issue_summary":             self.issue_summary,
            "issue_details":             self.issue_details,
            "offering_type_id":          str(self.offering_type_id) if self.offering_type_id else None,
            "brand_id":                  str(self.brand_id) if self.brand_id else None,
            "is_emergency":              bool(self.is_emergency),
            "photo_urls":                self.photo_urls or [],
            "preferred_date":            self.preferred_date.isoformat() if self.preferred_date else None,
            "preferred_time_window":     self.preferred_time_window,
            "serviceability_status":     self.serviceability_status,
            "price_status":              self.price_status,
            "provider_match_status":     self.provider_match_status,
            "price_snapshot":            self.price_snapshot,
            "provider_options":          self.provider_options or [],
            "selected_provider_snapshot":self.selected_provider_snapshot,
            "booking_summary":           self.booking_summary,
            "failure_code":              self.failure_code,
            "failure_message":           self.failure_message,
            "expires_at":                self.expires_at.isoformat()  if self.expires_at  else None,
            "created_at":                self.created_at.isoformat()  if self.created_at  else None,
            "updated_at":                self.updated_at.isoformat()  if self.updated_at  else None,
        }


class HomeServiceBookingDraftEvent(ServiceOSBase):
    """Immutable event log for every state change on a booking draft."""
    __tablename__ = "home_service_booking_draft_events"
    __table_args__ = (
        Index("ix_hsbde_draft_id",   "draft_id"),
        Index("ix_hsbde_event_type", "event_type"),
        Index("ix_hsbde_created_at", "created_at"),
    )

    draft_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str]       = mapped_column(String(30), nullable=False)   # customer|ai|backend|system
    event_type: Mapped[str]       = mapped_column(String(60), nullable=False)
    old_value:  Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value:  Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    message:    Mapped[str | None]  = mapped_column(Text,  nullable=True)
    request_id: Mapped[str | None]  = mapped_column(String(100), nullable=True)

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
