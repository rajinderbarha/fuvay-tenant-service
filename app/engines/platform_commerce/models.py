"""Platform Commerce Engine — SQLAlchemy Models (12 tables, all append-only ledgers)."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class CreditPackage(ServiceOSBase):
    """Admin-defined credit packages. Soft-delete only — never hard-delete."""
    __tablename__ = "credit_packages"
    __table_args__ = (Index("ix_cpkg_active", "is_active"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    price_inr: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bonus_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_restriction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchase_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantWallet(ServiceOSBase):
    """One row per tenant. Balance enforced >= 0 at DB level."""
    __tablename__ = "tenant_wallets"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_wallet_tenant"),
        CheckConstraint("credit_balance >= 0", name="ck_wallet_non_negative"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    credit_balance: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    lifetime_purchased: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    lifetime_consumed: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    last_transaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sprint 5 additions (nullable for backward compat)
    reserved_balance: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    low_balance_threshold: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def balance(self) -> Decimal:
        return self.credit_balance


class WalletTransaction(ServiceOSBase):
    """APPEND-ONLY ledger. No UPDATE ever. Every credit movement is a row here."""
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        Index("ix_wtxn_tenant_id", "tenant_id"),
        Index("ix_wtxn_reference", "reference_id"),
        Index("ix_wtxn_idem_key", "idempotency_key"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    txn_type: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


# SecurityDeposit / SecurityDepositTransaction were removed in migration 318.
# The per-tenant warranty deposit they modelled no longer exists: dispute
# settlements now draw from tenant_billing.credit_balance alone, and the
# credit floor on the finance policy is what keeps a balance available to
# draw against. See alembic/versions/318_dispute_settlement_credit_only.py.


class CommissionRecord(ServiceOSBase):
    """APPEND-ONLY. One row per job close. Idempotent on job_id."""
    __tablename__ = "commission_records"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_commission_job"),
        Index("ix_crec_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    base_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    health_adjustment: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    effective_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    job_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    wallet_balance_before: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    wallet_balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    health_band_at_time: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    deducted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    # Step 9 — links to the job-level invoice/payment + queryable status
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    calculation_base: Mapped[str] = mapped_column(String(20), default="total_amount", nullable=False)
    # status: pending | deducted | failed | waived | refunded
    status: Mapped[str] = mapped_column(String(20), default="deducted", nullable=False)
    wallet_ledger_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Sprint 5: link to the package purchase that determined commission rate
    package_purchase_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class CustomerHealthScore(ServiceOSBase):
    """Per customer per tenant health score. Same customer = different scores per tenant."""
    __tablename__ = "customer_health_scores"
    __table_args__ = (
        UniqueConstraint("customer_id", "tenant_id", name="uq_chs_customer_tenant"),
        Index("ix_chs_tenant_id", "tenant_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("80.00"), nullable=False)
    band: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    signals: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    can_book: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    advance_required_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    override_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    override_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CustomerCreditBalance(ServiceOSBase):
    """Per customer per tenant credit balance."""
    __tablename__ = "customer_credit_balances"
    __table_args__ = (
        UniqueConstraint("customer_id", "tenant_id", name="uq_ccb_customer_tenant"),
        CheckConstraint("credit_balance >= 0", name="ck_ccb_non_negative"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    credit_balance: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    reserved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    lifetime_purchased: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)
    lifetime_consumed: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0.00"), nullable=False)

    @property
    def available_balance(self) -> Decimal:
        return self.credit_balance - self.reserved_amount


class CustomerTransaction(ServiceOSBase):
    """APPEND-ONLY ledger for customer credit movements."""
    __tablename__ = "customer_transactions"
    __table_args__ = (
        Index("ix_ctxn_customer_tenant", "customer_id", "tenant_id"),
        Index("ix_ctxn_reference", "reference_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    txn_type: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CreditReservation(ServiceOSBase):
    """Booking-time credit lock. Auto-expires via Celery. Never orphaned."""
    __tablename__ = "credit_reservations"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_reservation_booking"),
        Index("ix_creserv_customer_tenant", "customer_id", "tenant_id"),
        Index("ix_creserv_status", "status"),
        Index("ix_creserv_expires_at", "expires_at"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    reserved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_type: Mapped[str | None] = mapped_column(String(30), nullable=True)


class WarrantyClaim(ServiceOSBase):
    """Provider-first warranty claim resolved directly with the customer."""
    __tablename__ = "warranty_claims"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_warranty_job"),
        Index("ix_wc_tenant_id", "tenant_id"),
        Index("ix_wc_status", "status"),
        Index("ix_wc_status_created_at", "status", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False, default="service_quality")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    media_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    amount_requested: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_approved: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="provider_action_required", nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deposit_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    parent_claim_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Finance Hub enterprise upgrade (migration 078)
    assigned_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    documents_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    documents_requested_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    warranty_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warranty_days_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # A warranty claim is now recovered entirely from the provider's credit
    # balance; `security_deposit_deducted` went with the deposit itself in
    # migration 318, and its historical values were folded into this column.
    provider_credit_deducted: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    customer_credit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class TenantBadge(ServiceOSBase):
    """Earned badges shown to customers. Recomputed daily via Celery."""
    __tablename__ = "tenant_badges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "badge_type", name="uq_badge_tenant_type"),
        Index("ix_tbadge_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    badge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    qualification_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
