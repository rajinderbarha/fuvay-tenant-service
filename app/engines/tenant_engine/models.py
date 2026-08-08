"""Tenant Engine — SQLAlchemy Models"""
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Tenant(ServiceOSBase):
    __tablename__ = "tenants"
    __table_args__ = (
        Index("ix_tenants_status", "status"),
        Index("ix_tenants_vertical", "vertical"),
        Index("ix_tenants_plan_type", "plan_type"),
        Index("ix_tenants_category_id", "category_id"),
        Index("ix_tenants_verification_status", "verification_status"),
        # Sprint 5 — location + scale indexes
        Index("ix_tenants_state", "state"),
        Index("ix_tenants_district", "district"),
        Index("ix_tenants_city", "city"),
        Index("ix_tenants_city_tier", "city_tier"),
        Index("ix_tenants_created_at", "created_at"),
        Index("ix_tenants_state_district", "state", "district"),
        Index("ix_tenants_state_district_city", "state", "district", "city"),
        Index("ix_tenants_verification_created", "verification_status", "created_at"),
        Index("ix_tenants_status_created", "status", "created_at"),
    )
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subdomain: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    # Sprint 4: slug + tenant_code for canonical identification
    slug: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    tenant_code: Mapped[str | None] = mapped_column(String(30), nullable=True, unique=True)
    # Sprint 4: separate business_name / legal_name
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vertical: Mapped[str] = mapped_column(String(50), nullable=False)
    # Sprint 4: category_id from admin_catalog (nullable for backward-compat)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="onboarding_pending")
    # Sprint 4: verification lifecycle
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_started")
    plan_type: Mapped[str] = mapped_column(String(30), nullable=False, default="starter")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Sprint 4: contact fields
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Sprint 4: address fields
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="India")
    zipcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Sprint 4: media
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Phase 0B: media engine references
    business_logo_media_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    shop_photo_media_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Sprint 5 — location hardening
    city_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)  # small|mid|large|metro
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Scoring + flags
    health_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=100.0)
    health_band: Mapped[str] = mapped_column(String(20), nullable=False, default="gold")
    rating_average: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.0)
    is_discoverable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sprint 4: archived
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantSettings(ServiceOSBase):
    """Per-tenant operational config: timezone, currency, commission rate, notification prefs."""
    __tablename__ = "tenant_operational_settings"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tos_tenant"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(60), nullable=False, default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.10)
    notify_new_booking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_job_completed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_low_credit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    low_credit_threshold: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=500.0)
    auto_accept_bookings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class TenantBusinessProfile(ServiceOSBase):
    __tablename__ = "tenant_business_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tbp_tenant"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gstin_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cin: Mapped[str | None] = mapped_column(String(25), nullable=True)
    cin_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    registered_address: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    year_established: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenantBranding(ServiceOSBase):
    __tablename__ = "tenant_branding"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tb_tenant"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#3D7BFF")
    secondary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#10B981")
    font_preference: Mapped[str] = mapped_column(String(50), nullable=False, default="Inter")
    custom_terms_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TenantFinanceReadiness(ServiceOSBase):
    """Which payment methods a tenant is ready to accept, captured during
    Home Services onboarding.

    Real bug fixed here: the `tenant_finance_readiness` TABLE exists and
    vertical_catalog/tenant_finance_readiness_router.py imports this model,
    but the model was never written -- so that module raised ImportError and
    its whole router could never be mounted. Columns mirror the live table
    exactly (verified against information_schema).
    """
    __tablename__ = "tenant_finance_readiness"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tfr_tenant"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)

    accepts_cash: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepts_upi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepts_card_at_service_location: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepts_bank_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    payment_confirmation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_prefix: Mapped[str | None] = mapped_column(String(50), nullable=True)
    issue_customer_receipt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TenantBilling(ServiceOSBase):
    __tablename__ = "tenant_billing"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tbl_tenant"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    razorpay_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_billing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    credit_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    security_deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    security_deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    vertical_key: Mapped[str | None] = mapped_column(String(50), nullable=True)


class UsageCreditLedger(ServiceOSBase):
    """HS9 — every usage-credit balance change against tenant_billing.
    credit_balance (the pre-existing, real canonical balance field) must
    create one of these rows. Not money — internal platform credits only."""
    __tablename__ = "usage_credit_ledger"
    __table_args__ = (
        Index("ix_ucl_tenant_id", "tenant_id"),
    )
    tenant_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    booking_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type:          Mapped[str]              = mapped_column(String(50), nullable=False)
    credit_delta:        Mapped[float]            = mapped_column(Numeric(12, 2), nullable=False)
    balance_before:      Mapped[float]            = mapped_column(Numeric(12, 2), nullable=False)
    balance_after:       Mapped[float]            = mapped_column(Numeric(12, 2), nullable=False)
    # 100, not 50 (migration 235): the commission path writes a prefixed label
    # such as "category_commission:<uuid>" (56 chars), which truncated and made
    # every percentage-commission job completion fail with a 500.
    deduction_source:    Mapped[str | None]       = mapped_column(String(100), nullable=True)
    service_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_type_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brand_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    zone_id:             Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason:              Mapped[str | None]       = mapped_column(Text(), nullable=True)
    created_by:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_id:          Mapped[str | None]       = mapped_column(String(100), nullable=True)
    idempotency_key:     Mapped[str | None]       = mapped_column(String(200), nullable=True)
    source_type:         Mapped[str | None]       = mapped_column(String(50), nullable=True)
    source_id:           Mapped[str | None]       = mapped_column(String(100), nullable=True)
    reason_code:         Mapped[str | None]       = mapped_column(String(50), nullable=True)
    actor_role:          Mapped[str | None]       = mapped_column(String(30), nullable=True)

    def to_dict(self) -> dict:
        return {
            "ledger_id":          str(self.id),
            "tenant_id":          str(self.tenant_id),
            "job_id":             str(self.job_id) if self.job_id else None,
            "booking_id":         str(self.booking_id) if self.booking_id else None,
            "event_type":         self.event_type,
            "credit_delta":       float(self.credit_delta),
            "balance_before":     float(self.balance_before),
            "balance_after":      float(self.balance_after),
            "deduction_source":   self.deduction_source,
            "service_id":         str(self.service_id) if self.service_id else None,
            "service_type_id":    str(self.service_type_id) if self.service_type_id else None,
            "brand_id":           str(self.brand_id) if self.brand_id else None,
            "reason":             self.reason,
            "reason_code":        self.reason_code,
            "source_type":        self.source_type,
            "source_id":          self.source_id,
            "idempotency_key":    self.idempotency_key,
            "request_id":         self.request_id,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }


class TenantLimits(ServiceOSBase):
    __tablename__ = "tenant_limits"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tlim_tenant"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    max_staff: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_active_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_storage_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_api_calls_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)
    max_engines: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    max_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    max_service_areas: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    current_staff_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_active_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_api_calls_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TenantDocument(ServiceOSBase):
    """Found significantly out of sync with the real, migrated DB schema
    during the Final Phase end-to-end pass -- 14 real columns (staff_member_id,
    status, document_number, version/is_current/superseded_by_id versioning,
    reviewed_by/review_notes, etc.) existed in the DB and were actively used
    by mobile_documents_service.py, but were missing from this model
    entirely, causing every /v1/staff/me/documents call to AttributeError."""
    __tablename__ = "tenant_documents"
    __table_args__ = (
        Index("ix_tenant_docs_tenant_id", "tenant_id"),
        Index("ix_tenant_docs_tenant_doctype", "tenant_id", "doc_type"),
        Index("ix_tenant_docs_current", "tenant_id", "doc_type", "is_current"),
        Index("ix_tenant_docs_staff", "tenant_id", "staff_member_id", "doc_type", "is_current"),
    )
    tenant_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_type:            Mapped[str]              = mapped_column(String(50), nullable=False)
    label:                Mapped[str | None]       = mapped_column(String(200), nullable=True)
    media_asset_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    file_url:            Mapped[str]              = mapped_column(String(500), nullable=False, default="")
    document_number:      Mapped[str | None]       = mapped_column(String(100), nullable=True)
    issue_date:           Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date:          Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    version:              Mapped[int]              = mapped_column(Integer, nullable=False, default=1)
    is_current:           Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    superseded_by_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:               Mapped[str]              = mapped_column(String(30), nullable=False, default="pending_review")
    rejection_reason:      Mapped[str | None]       = mapped_column(Text, nullable=True)
    uploaded_by_user_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff_member_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_by:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    review_notes:         Mapped[str | None]       = mapped_column(Text, nullable=True)


class OnboardingRequest(ServiceOSBase):
    __tablename__ = "onboarding_requests"
    __table_args__ = (Index("ix_onboarding_status", "status"),)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vertical: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted")
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    checklist: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    plan_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    engines_to_enable: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    engine_configs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="self_signup")


class TenantFeatureFlag(ServiceOSBase):
    __tablename__ = "tenant_feature_flags"
    __table_args__ = (UniqueConstraint("tenant_id","flag_key", name="uq_tff_tenant_key"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    flag_key: Mapped[str] = mapped_column(String(100), nullable=False)
    flag_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    set_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)


class TenantAuditLog(ServiceOSBase):
    __tablename__ = "tenant_audit_logs"
    __table_args__ = (Index("ix_tal_tenant_id", "tenant_id"),)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
