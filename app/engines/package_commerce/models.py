"""Sprint 5 / P0 / P1 — Package Commerce Models.

Tables: service_packages, package_features, package_limits,
        tenant_package_purchases, tenant_package_assignments, package_audit_logs.
Extended: tenant_wallets + security_deposits (nullable columns via alter).
"""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class ServicePackage(ServiceOSBase):
    """Admin-defined packages: onboarding, credit_topup, subscription."""
    __tablename__ = "service_packages"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_spkg_slug"),
        CheckConstraint("package_price >= 0", name="ck_spkg_price"),
        CheckConstraint("security_deposit_amount >= 0", name="ck_spkg_deposit"),
        CheckConstraint("included_credit_amount >= 0", name="ck_spkg_credit"),
        Index("ix_spkg_package_type", "package_type"),
        Index("ix_spkg_is_active", "is_active"),
        Index("ix_spkg_display_order", "display_order"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # onboarding | credit_topup | subscription
    package_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # starter | growth | enterprise | custom
    plan_level: Mapped[str | None] = mapped_column(String(30), nullable=True)

    package_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    security_deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    included_credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    storage_quota_gb: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Sprint 070 — signup / public visibility fields
    vertical_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_cycle: Mapped[str | None] = mapped_column(String(30), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False, server_default="INR")
    is_public_signup_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Sprint P0 — extended package definition fields (migration 071)
    short_description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rich_description_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rich_description_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    badge_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cta_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    terms_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_content_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    trial_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bonus_credits: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    lead_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    setup_fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    renewal_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    refund_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PackageFeature(ServiceOSBase):
    """One benefit/feature line displayed on a package card."""
    __tablename__ = "package_features"
    __table_args__ = (
        Index("ix_pkgfeat_package_id",    "package_id"),
        Index("ix_pkgfeat_display_order", "display_order"),
    )

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    feature_label: Mapped[str] = mapped_column(String(200), nullable=False)
    feature_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_highlighted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PackageLimit(ServiceOSBase):
    """One usage-limit line for a package (e.g. Up to 10 staff)."""
    __tablename__ = "package_limits"
    __table_args__ = (
        Index("ix_pkglim_package_id",    "package_id"),
        Index("ix_pkglim_display_order", "display_order"),
    )

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    limit_key: Mapped[str] = mapped_column(String(100), nullable=False)
    limit_label: Mapped[str] = mapped_column(String(200), nullable=False)
    limit_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    limit_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_unlimited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantPackagePurchase(ServiceOSBase):
    """One row per tenant package purchase event."""
    __tablename__ = "tenant_package_purchases"
    __table_args__ = (
        Index("ix_tpp_tenant_id", "tenant_id"),
        Index("ix_tpp_package_id", "package_id"),
        Index("ix_tpp_package_type", "package_type"),
        Index("ix_tpp_payment_status", "payment_status"),
        Index("ix_tpp_purchased_at", "purchased_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    package_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    package_type: Mapped[str] = mapped_column(String(30), nullable=False)
    package_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    security_deposit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    storage_quota_gb: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # pending | paid | failed | cancelled | refunded
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    payment_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantPackageAssignment(ServiceOSBase):
    """
    P1 — Lifecycle record for a tenant's selected/paid/approved package.

    starts_at and expires_at MUST remain NULL until admin approval.
    Credits are added to wallet only on activation (admin approval).
    Security deposit is kept separate — never becomes spendable wallet credit.
    """
    __tablename__ = "tenant_package_assignments"
    __table_args__ = (
        Index("ix_tpa_tenant_id",  "tenant_id"),
        Index("ix_tpa_package_id", "package_id"),
        Index("ix_tpa_status",     "status"),
    )

    tenant_id:   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    package_id:  Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_packages.id", ondelete="SET NULL"), nullable=True
    )
    package_type: Mapped[str]            = mapped_column(String(30), nullable=False)

    # selected | pending_review | pending_payment | paid_pending_approval
    # active | expired | cancelled | refunded | rejected
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="selected")

    # Lifecycle timestamps — starts_at/expires_at NULL until admin approval
    selected_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at:  Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    starts_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Package snapshot at time of selection
    validity_days:              Mapped[int | None]     = mapped_column(Integer,        nullable=True)
    billing_cycle:              Mapped[str | None]     = mapped_column(String(20),     nullable=True)
    price_amount:               Mapped[Decimal]        = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    security_deposit_amount:    Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    included_spendable_credits: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    lead_credits:               Mapped[int | None]     = mapped_column(Integer,        nullable=True)

    # Payment linkage
    payment_reference_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Audit metadata
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PackageAuditLog(ServiceOSBase):
    """Append-only log of all package/wallet/commission admin actions."""
    __tablename__ = "package_audit_logs"
    __table_args__ = (
        Index("ix_pal_tenant_id", "tenant_id"),
        Index("ix_pal_package_id", "package_id"),
        Index("ix_pal_action", "action"),
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    package_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    package_purchase_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
