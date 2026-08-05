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
            "customer_fee_model": self.customer_fee_model,
            "customer_fee_percentage": str(self.customer_fee_percentage) if self.customer_fee_percentage is not None else None,
            "customer_fee_fixed_amount_minor": self.customer_fee_fixed_amount_minor,
            "customer_fee_min_minor": self.customer_fee_min_minor,
            "customer_fee_max_minor": self.customer_fee_max_minor,
            "customer_fee_basis": self.customer_fee_basis,
            "collection_stage": self.collection_stage,
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
    provider_charge_credit_units: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status:                       Mapped[str]            = mapped_column(String(20), default="active", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "policy_id": str(self.policy_id), "job_type_id": str(self.job_type_id),
            "customer_charge_enabled": self.customer_charge_enabled, "customer_charge_basis": self.customer_charge_basis,
            "provider_charge_enabled": self.provider_charge_enabled,
            "provider_charge_credit_units": str(self.provider_charge_credit_units) if self.provider_charge_credit_units is not None else None,
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
