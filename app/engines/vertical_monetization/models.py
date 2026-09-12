"""VERTICAL-MONETIZATION: two independent, versioned, vertical-scoped
monetization policies + the customer platform-fee charge/snapshot ledger.

Provider-side money movement (UsageCreditLedger, PaymentRecord for credit
top-ups) is NOT reimplemented here -- see migration 178 docstring. These
tables are the single source of truth for WHICH model a vertical uses and
the real customer-fee charge/collection trail.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

PROVIDER_MODELS = {"NONE", "COMPLETION_CREDITS", "PERCENTAGE_COMMISSION",
                   "FIXED_COMPLETION_CHARGE", "SUBSCRIPTION", "LEAD_FEE"}
CUSTOMER_FEE_MODELS = {"NONE", "PERCENTAGE", "FIXED", "PERCENTAGE_WITH_MIN_MAX"}
COLLECTION_STAGES = {"before_booking_confirmation", "after_estimate_approval",
                    "before_work_start", "on_completion"}

#: When the provider is charged. Each value corresponds to a real lifecycle
#: hook that attempts the deduction, so an admin can only choose a moment the
#: runtime actually reaches:
#:
#:   work_started           technician starts the service (start_service)
#:   work_done              technician marks the work finished (mark_work_done)
#:   job_completed          the job is completed and invoiced (complete_job)
#:   consultation_completed as job_completed, for consultation job types
#:
#: The deduction is idempotent per job, so a job passing several of these
#: moments is still charged exactly once -- at the configured one.
PROVIDER_CHARGEABLE_EVENTS = {"work_started", "work_done",
                              "job_completed", "consultation_completed"}
CHARGE_STATUSES = {"PENDING", "NOT_REQUIRED", "PAID", "FAILED", "REFUNDED", "WAIVED"}


class VerticalMonetizationPolicy(ServiceOSBase):
    __tablename__ = "vertical_monetization_policies"
    __table_args__ = (
        Index("ix_vmp_vertical", "vertical_id"),
        Index("ix_vmp_vertical_current", "vertical_id", unique=True,
              postgresql_where="is_current = true"),
        Index("ix_vmp_vertical_version", "vertical_id", "version_number", unique=True),
    )

    vertical_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number:   Mapped[int]       = mapped_column(Integer, nullable=False)
    status:           Mapped[str]       = mapped_column(String(20), default="draft", nullable=False)
    is_current:       Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)

    provider_model:                Mapped[str]            = mapped_column(String(30), default="NONE", nullable=False)
    provider_percentage:           Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    provider_fixed_amount_minor:   Mapped[int | None]     = mapped_column(BigInteger, nullable=True)
    provider_credit_units:         Mapped[int | None]     = mapped_column(Integer, nullable=True)
    provider_subscription_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    provider_chargeable_event:     Mapped[str | None]     = mapped_column(String(40), nullable=True)
    provider_min_charge_minor:     Mapped[int | None]     = mapped_column(BigInteger, nullable=True)
    provider_max_charge_minor:     Mapped[int | None]     = mapped_column(BigInteger, nullable=True)

    # Optional quality adjustment for percentage commission. Values are
    # additive percentage points keyed by the canonical Trust & Quality band
    # (for example base 10% + watchlist 5pp = 15%). Published policies remain
    # immutable; the feature is enabled only by publishing a new version.
    provider_health_adjustment_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_health_adjustments_json: Mapped[dict] = mapped_column(
        JSONB, default=lambda: {
            "platinum": 0, "gold": 0, "silver": 2,
            "watchlist": 5, "at_risk": 8, "blocked": 10,
        }, nullable=False,
    )
    provider_health_score_max_age_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    provider_health_max_effective_percentage: Mapped[Decimal] = mapped_column(
        Numeric(6, 3), default=Decimal("25"), nullable=False,
    )

    # ── SLA breach: what a late job costs, and where the money goes ──────────
    # Every one of these is admin policy rather than a constant, so a penalty
    # can be retuned, reviewed and rolled back exactly like a commission rate.
    # All nullable / defaulted so an existing policy keeps behaving as it does.
    sla_breach_hours:        Mapped[int | None]     = mapped_column(Integer, nullable=True)
    sla_penalty_amount:      Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sla_penalty_to_customer: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    sla_penalty_debt_cap:    Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sla_auto_cancel:         Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    sla_notify_provider:     Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    sla_penalty_type:        Mapped[str]            = mapped_column(String(20), default="fixed", nullable=False)
    sla_penalty_percentage:  Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    sla_penalty_min:         Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sla_penalty_max:         Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sla_breachable_statuses: Mapped[list | None]    = mapped_column(JSONB, nullable=True)
    sla_penalty_max_days:    Mapped[int]            = mapped_column(Integer, default=3, nullable=False)

    # Home Services operational controls. They live on the same versioned,
    # audited policy as SLA enforcement so administrators can change runtime
    # behaviour without a code release. Defaults preserve the launch rules.
    assignment_timeout_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assignment_timeout_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    customer_reschedule_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    arrival_verification_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    arrival_radius_meters: Mapped[int] = mapped_column(Integer, default=250, nullable=False)
    arrival_location_max_age_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    arrival_max_accuracy_meters: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    false_arrival_auto_close: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    false_arrival_penalty_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("150"), nullable=False,
    )
    false_arrival_health_weight: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("3"), nullable=False,
    )

    # ── Health suspension: when a provider is stopped, and what they return at
    health_suspension_threshold: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    health_suspension_days:      Mapped[int | None]     = mapped_column(Integer, nullable=True)
    health_reinstatement_score:  Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    # ── Media retention ──────────────────────────────────────────────────────
    # What the customer sent goes shortly after the job finishes; the
    # provider's before/after evidence is kept until the warranty it defends
    # has expired. NULL means that kind is never purged.
    customer_photo_retention_days:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_proof_retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Credit reminder cadence ──────────────────────────────────────────────
    # Hours between reminders at each level. NULL falls back to the service
    # defaults (24 / 6 / 2), which escalate with severity rather than dripping
    # at a fixed rate a provider would learn to mute.
    credit_reminder_hours_low:     Mapped[int | None] = mapped_column(Integer, nullable=True)
    credit_reminder_hours_blocked: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credit_reminder_hours_arrears: Mapped[int | None] = mapped_column(Integer, nullable=True)

    customer_fee_model:              Mapped[str]            = mapped_column(String(30), default="NONE", nullable=False)
    customer_fee_percentage:         Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    customer_fee_fixed_amount_minor: Mapped[int | None]     = mapped_column(BigInteger, nullable=True)
    customer_fee_min_minor:          Mapped[int | None]     = mapped_column(BigInteger, nullable=True)
    customer_fee_max_minor:          Mapped[int | None]     = mapped_column(BigInteger, nullable=True)
    customer_fee_basis:              Mapped[str]            = mapped_column(String(30), default="service_subtotal", nullable=False)
    collection_stage:                Mapped[str]            = mapped_column(String(40), default="after_estimate_approval", nullable=False)
    customer_fee_refund_policy:      Mapped[str]            = mapped_column(String(30), default="refundable_if_job_not_started", nullable=False)

    currency:            Mapped[str]            = mapped_column(String(3), default="INR", nullable=False)
    effective_from:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    change_summary:      Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "vertical_id": str(self.vertical_id),
            "version_number": self.version_number, "status": self.status, "is_current": self.is_current,
            "provider_model": self.provider_model,
            "provider_percentage": str(self.provider_percentage) if self.provider_percentage is not None else None,
            "provider_fixed_amount_minor": self.provider_fixed_amount_minor,
            "provider_credit_units": self.provider_credit_units,
            "provider_subscription_plan_id": str(self.provider_subscription_plan_id) if self.provider_subscription_plan_id else None,
            "provider_chargeable_event": self.provider_chargeable_event,
            "provider_min_charge_minor": self.provider_min_charge_minor,
            "provider_max_charge_minor": self.provider_max_charge_minor,
            "provider_health_adjustment_enabled": self.provider_health_adjustment_enabled,
            "provider_health_adjustments_json": self.provider_health_adjustments_json,
            "provider_health_score_max_age_days": self.provider_health_score_max_age_days,
            "provider_health_max_effective_percentage": str(self.provider_health_max_effective_percentage),
            "customer_fee_model": self.customer_fee_model,
            "customer_fee_percentage": str(self.customer_fee_percentage) if self.customer_fee_percentage is not None else None,
            "customer_fee_fixed_amount_minor": self.customer_fee_fixed_amount_minor,
            "customer_fee_min_minor": self.customer_fee_min_minor,
            "customer_fee_max_minor": self.customer_fee_max_minor,
            "customer_fee_basis": self.customer_fee_basis,
            "collection_stage": self.collection_stage,
            "sla_breach_hours": self.sla_breach_hours,
            "sla_penalty_amount": float(self.sla_penalty_amount) if self.sla_penalty_amount is not None else None,
            "sla_penalty_to_customer": self.sla_penalty_to_customer,
            "sla_penalty_debt_cap": float(self.sla_penalty_debt_cap) if self.sla_penalty_debt_cap is not None else None,
            "sla_auto_cancel": self.sla_auto_cancel,
            "sla_notify_provider": self.sla_notify_provider,
            "sla_penalty_type": self.sla_penalty_type,
            "sla_penalty_percentage": float(self.sla_penalty_percentage) if self.sla_penalty_percentage is not None else None,
            "sla_penalty_min": float(self.sla_penalty_min) if self.sla_penalty_min is not None else None,
            "sla_penalty_max": float(self.sla_penalty_max) if self.sla_penalty_max is not None else None,
            "sla_breachable_statuses": self.sla_breachable_statuses,
            "sla_penalty_max_days": self.sla_penalty_max_days,
            "assignment_timeout_enabled": self.assignment_timeout_enabled,
            "assignment_timeout_minutes": self.assignment_timeout_minutes,
            "customer_reschedule_limit": self.customer_reschedule_limit,
            "arrival_verification_enabled": self.arrival_verification_enabled,
            "arrival_radius_meters": self.arrival_radius_meters,
            "arrival_location_max_age_seconds": self.arrival_location_max_age_seconds,
            "arrival_max_accuracy_meters": self.arrival_max_accuracy_meters,
            "false_arrival_auto_close": self.false_arrival_auto_close,
            "false_arrival_penalty_amount": float(self.false_arrival_penalty_amount),
            "false_arrival_health_weight": float(self.false_arrival_health_weight),
            "health_suspension_threshold": float(self.health_suspension_threshold) if self.health_suspension_threshold is not None else None,
            "health_suspension_days": self.health_suspension_days,
            "health_reinstatement_score": float(self.health_reinstatement_score) if self.health_reinstatement_score is not None else None,
            "customer_photo_retention_days": self.customer_photo_retention_days,
            "completion_proof_retention_days": self.completion_proof_retention_days,
            "credit_reminder_hours_low": self.credit_reminder_hours_low,
            "credit_reminder_hours_blocked": self.credit_reminder_hours_blocked,
            "credit_reminder_hours_arrears": self.credit_reminder_hours_arrears,
            "customer_fee_refund_policy": self.customer_fee_refund_policy,
            "currency": self.currency,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "change_summary": self.change_summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MonetizationJobTypeRule(ServiceOSBase):
    """Per-Job-Type override of a vertical monetization policy. Exact Job
    Type only (Master Service + Job Type -> Job-Type Blueprint) -- never
    inferred from service count. Child of a specific policy VERSION; a new
    policy version gets its own fresh rule set, never mutates a prior
    version's rows (immutability matches the parent policy)."""
    __tablename__ = "monetization_job_type_rules"
    __table_args__ = (
        UniqueConstraint("policy_id", "job_type_id", name="uq_mjtr_policy_job_type"),
        Index("ix_mjtr_policy", "policy_id"),
    )

    policy_id:                    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_type_id:                  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_charge_enabled:      Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    customer_charge_basis:        Mapped[str]            = mapped_column(String(30), default="booking_price_snapshot", nullable=False)
    provider_charge_enabled:      Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    provider_charge_model:        Mapped[str]            = mapped_column(String(30), default="INHERIT", nullable=False)
    provider_charge_credit_units: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    provider_chargeable_event:    Mapped[str]            = mapped_column(String(40), default="job_completed", nullable=False)
    #: Per-job-type SLA penalty. Disabling it exempts this job type entirely;
    #: an amount overrides whatever the policy would otherwise have charged.
    sla_penalty_enabled:          Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    sla_penalty_amount:           Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status:                       Mapped[str]            = mapped_column(String(20), default="active", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "policy_id": str(self.policy_id), "job_type_id": str(self.job_type_id),
            "customer_charge_enabled": self.customer_charge_enabled, "customer_charge_basis": self.customer_charge_basis,
            "provider_charge_enabled": self.provider_charge_enabled,
            "provider_charge_model": self.provider_charge_model,
            "provider_charge_credit_units": str(self.provider_charge_credit_units) if self.provider_charge_credit_units is not None else None,
            "provider_chargeable_event": self.provider_chargeable_event,
            "sla_penalty_enabled": self.sla_penalty_enabled,
            "sla_penalty_amount": str(self.sla_penalty_amount) if self.sla_penalty_amount is not None else None,
            "status": self.status,
        }


class CustomerPlatformFeeCharge(ServiceOSBase):
    __tablename__ = "customer_platform_fee_charges"
    __table_args__ = (
        Index("ix_cpfc_booking", "booking_id"),
        Index("ix_cpfc_job", "job_id"),
        Index("ix_cpfc_quote", "quote_id"),
        Index("ix_cpfc_status", "status"),
    )

    idempotency_key:  Mapped[str]            = mapped_column(String(200), nullable=False, unique=True)
    vertical_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    booking_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    quote_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    quote_version:    Mapped[int | None]     = mapped_column(Integer, nullable=True)
    policy_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    policy_version:   Mapped[int | None]     = mapped_column(Integer, nullable=True)
    calculation_basis: Mapped[str]           = mapped_column(String(30), nullable=False)

    service_subtotal_minor:     Mapped[int] = mapped_column(BigInteger, nullable=False)
    chargeable_subtotal_minor:  Mapped[int] = mapped_column(BigInteger, nullable=False)
    fee_amount_minor:           Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_amount_minor:           Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    discount_amount_minor:      Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    credit_amount_minor:        Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_payable_minor:        Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency:                   Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    collection_stage:           Mapped[str] = mapped_column(String(40), nullable=False)
    status:                     Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    payment_id:                 Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    refund_id:                  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    calculation_breakdown:      Mapped[dict] = mapped_column(JSONB, nullable=False)
    correlation_id:             Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_event:               Mapped[str] = mapped_column(String(60), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "idempotency_key": self.idempotency_key,
            "vertical_id": str(self.vertical_id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "booking_id": str(self.booking_id) if self.booking_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "quote_id": str(self.quote_id) if self.quote_id else None,
            "quote_version": self.quote_version,
            "policy_id": str(self.policy_id) if self.policy_id else None,
            "policy_version": self.policy_version,
            "calculation_basis": self.calculation_basis,
            "service_subtotal_minor": self.service_subtotal_minor,
            "chargeable_subtotal_minor": self.chargeable_subtotal_minor,
            "fee_amount_minor": self.fee_amount_minor,
            "tax_amount_minor": self.tax_amount_minor,
            "discount_amount_minor": self.discount_amount_minor,
            "credit_amount_minor": self.credit_amount_minor,
            "total_payable_minor": self.total_payable_minor,
            "currency": self.currency, "collection_stage": self.collection_stage,
            "status": self.status,
            "payment_id": str(self.payment_id) if self.payment_id else None,
            "refund_id": str(self.refund_id) if self.refund_id else None,
            "calculation_breakdown": self.calculation_breakdown,
            "correlation_id": self.correlation_id, "source_event": self.source_event,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
