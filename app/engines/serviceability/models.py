"""Serviceability Engine — Models (4 tables)."""
from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class CustomerAddress(ServiceOSBase):
    """A customer's saved delivery/service address."""
    __tablename__ = "customer_addresses"
    __table_args__ = (
        Index("ix_ca_customer_active",  "customer_id", "is_active"),
        Index("ix_ca_customer_default", "customer_id", "is_default"),
        Index("ix_ca_city_zip",         "city", "zipcode"),
        Index("uq_ca_one_default_active", "customer_id", unique=True,
              postgresql_where=text("is_default = true AND is_active = true")),
    )

    customer_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name:          Mapped[str|None]       = mapped_column(String(100), nullable=True)
    phone:         Mapped[str|None]       = mapped_column(String(30), nullable=True)
    address_line_1:Mapped[str]            = mapped_column(String(300), nullable=False)
    address_line_2:Mapped[str|None]       = mapped_column(String(300), nullable=True)
    landmark:      Mapped[str|None]       = mapped_column(String(200), nullable=True)
    city:          Mapped[str]            = mapped_column(String(100), nullable=False)
    district:      Mapped[str|None]       = mapped_column(String(100), nullable=True)
    state:         Mapped[str]            = mapped_column(String(100), nullable=False)
    country:       Mapped[str]            = mapped_column(String(50), default="India", nullable=False)
    zipcode:       Mapped[str]            = mapped_column(String(20), nullable=False)
    latitude:      Mapped[Decimal|None]   = mapped_column(Numeric(10, 7), nullable=True)
    longitude:     Mapped[Decimal|None]   = mapped_column(Numeric(10, 7), nullable=True)
    is_default:    Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    is_active:     Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)


class TenantServiceArea(ServiceOSBase):
    """Defines a geographic area a tenant covers for services.

    Coverage-approval workflow (migration 162): rows created before this
    slice have no request behind them (self-service, instant-activate era);
    their `status` was backfilled from the pre-existing `is_active` flag.
    Rows created going forward are expected to trace back to an approved
    TenantServiceAreaRequestItem via `approved_request_item_id`, enforced at
    the service layer (super_admin retains a documented, audited manual
    path for support cases — not a silent bypass)."""
    __tablename__ = "tenant_service_areas"
    __table_args__ = (
        Index("ix_tsa_tenant_city",    "tenant_id", "city", "is_active"),
        Index("ix_tsa_tenant_zip",     "tenant_id", "zipcode", "is_active"),
        Index("ix_tsa_city_zip",       "city", "zipcode"),
        Index("ix_tsa_tenant_coverage_city_zip",
              "tenant_id", "coverage_type", "city", "zipcode"),
        Index("ix_tsa_category",       "category_id"),
        Index("ix_tsa_status",         "status"),
        Index("ix_tsa_tenant_category_status", "tenant_id", "category_id", "status"),
        UniqueConstraint("tenant_id", "coverage_type", "city", "zipcode",
                         name="uq_tsa_tenant_coverage"),
    )

    tenant_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    coverage_type: Mapped[str]            = mapped_column(String(20), nullable=False)  # city|zipcode|zone|radius
    country:       Mapped[str]            = mapped_column(String(50), default="India", nullable=False)
    state:         Mapped[str]            = mapped_column(String(100), nullable=False)
    district:      Mapped[str|None]       = mapped_column(String(100), nullable=True)
    city:          Mapped[str]            = mapped_column(String(100), nullable=False)
    zipcode:       Mapped[str|None]       = mapped_column(String(20), nullable=True)
    zone_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    zone_name:     Mapped[str|None]       = mapped_column(String(100), nullable=True)
    latitude:      Mapped[Decimal|None]   = mapped_column(Numeric(10, 7), nullable=True)
    longitude:     Mapped[Decimal|None]   = mapped_column(Numeric(10, 7), nullable=True)
    radius_km:     Mapped[Decimal|None]   = mapped_column(Numeric(8, 2), nullable=True)
    priority:      Mapped[int]            = mapped_column(Integer, default=100, nullable=False)
    is_active:     Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    is_primary:    Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    # ── Coverage-approval workflow additions (migration 162) ──────────────
    category_id:              Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:                   Mapped[str]            = mapped_column(String(30), default="ACTIVE", nullable=False)  # ACTIVE|SUSPENDED|EXPIRED|REVOKED
    approved_request_item_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by:              Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at:              Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at:             Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_by:             Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    suspension_reason:        Mapped[str|None]       = mapped_column(Text, nullable=True)
    effective_from:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    effective_until:          Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)


class TenantServiceAreaService(ServiceOSBase):
    """Maps a specific service (+ job_type) to a tenant service area.

    min_price/max_price/base_price predate the coverage-approval slice — a
    pre-existing coupling between coverage and price on this table, left
    as-is (not deepened; the request/approval flow never writes these)."""
    __tablename__ = "tenant_service_area_services"
    __table_args__ = (
        Index("ix_tsas_area_available", "tenant_service_area_id", "is_available"),
        Index("ix_tsas_service_type",   "service_id", "job_type", "is_available"),
        Index("ix_tsas_tenant",         "tenant_id", "is_available"),
        Index("ix_tsas_tenant_service_job", "tenant_id", "service_id", "job_type"),
        Index("ix_tsas_status",         "status"),
        Index("uq_tsas_active_mapping", "tenant_service_area_id", "service_id", "job_type",
              unique=True, postgresql_where=text("is_available = true")),
    )

    tenant_service_area_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    service_id:             Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_type:               Mapped[str]            = mapped_column(String(30), nullable=False)
    is_available:           Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    sla_minutes:            Mapped[int|None]       = mapped_column(Integer, nullable=True)
    min_price:              Mapped[Decimal|None]   = mapped_column(Numeric(10, 2), nullable=True)
    max_price:              Mapped[Decimal|None]   = mapped_column(Numeric(10, 2), nullable=True)
    base_price:             Mapped[Decimal|None]   = mapped_column(Numeric(10, 2), nullable=True)
    status:                 Mapped[str]            = mapped_column(String(30), default="ACTIVE", nullable=False)  # ACTIVE|SUSPENDED|EXPIRED|REVOKED


class TenantServiceAreaRequest(ServiceOSBase):
    """A tenant's request to serve one or more city/zipcode areas for one or
    more of its services, subject to admin review. Reviewed at the
    request-item level (TenantServiceAreaRequestItem); this row's `status`
    is the aggregate of its items' decisions."""
    __tablename__ = "tenant_service_area_requests"
    __table_args__ = (
        Index("ix_tsar_tenant",          "tenant_id"),
        Index("ix_tsar_tenant_category", "tenant_id", "category_id"),
        Index("ix_tsar_status",          "status"),
        Index("ix_tsar_submitted_at",    "submitted_at"),
    )

    STATUSES = ("DRAFT", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUESTED",
                "PARTIALLY_APPROVED", "APPROVED", "REJECTED", "WITHDRAWN")
    TENANT_EDITABLE_STATUSES = ("DRAFT", "CHANGES_REQUESTED")

    tenant_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:       Mapped[str]            = mapped_column(String(30), default="DRAFT", nullable=False)
    version:      Mapped[int]            = mapped_column(Integer, default=1, nullable=False)
    submitted_at: Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at:  Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_notes: Mapped[str|None]       = mapped_column(Text, nullable=True)
    admin_notes:  Mapped[str|None]       = mapped_column(Text, nullable=True)
    superseded_by_request_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class TenantServiceAreaRequestItem(ServiceOSBase):
    """One requested city/zipcode x tenant_service within a request.
    `applies_to_all_job_types` is explicit and validated — a NULL
    `job_type_id` alone never implicitly means 'all job types'."""
    __tablename__ = "tenant_service_area_request_items"
    __table_args__ = (
        Index("ix_tsari_request",         "request_id"),
        Index("ix_tsari_tenant_service",  "tenant_service_id"),
        Index("ix_tsari_decision_status", "decision_status"),
        Index("ix_tsari_city_zip",        "city", "zipcode"),
    )

    DECISION_STATUSES = ("PENDING", "APPROVED", "REJECTED", "CHANGES_REQUESTED")

    request_id:                Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_service_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    master_service_id:         Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_type_id:               Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    applies_to_all_job_types:  Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    country:                   Mapped[str]            = mapped_column(String(50), default="India", nullable=False)
    state:                     Mapped[str]            = mapped_column(String(100), nullable=False)
    district:                  Mapped[str|None]       = mapped_column(String(100), nullable=True)
    city:                      Mapped[str]            = mapped_column(String(100), nullable=False)
    zipcode:                   Mapped[str|None]       = mapped_column(String(20), nullable=True)
    requested_effective_date:  Mapped[date|None]      = mapped_column(Date, nullable=True)
    decision_status:           Mapped[str]            = mapped_column(String(30), default="PENDING", nullable=False)
    decision_reason:           Mapped[str|None]       = mapped_column(Text, nullable=True)
    reviewed_at:               Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by:               Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class ServiceabilityAuditLog(ServiceOSBase):
    """Immutable log of every serviceability check — used for debugging and analytics."""
    __tablename__ = "serviceability_audit_logs"
    __table_args__ = (
        Index("ix_sal_customer",    "customer_id"),
        Index("ix_sal_city_zip",    "city", "zipcode"),
        Index("ix_sal_created_at",  "created_at"),
    )

    customer_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    address_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_type:             Mapped[str|None]        = mapped_column(String(30), nullable=True)
    city:                 Mapped[str|None]        = mapped_column(String(100), nullable=True)
    zipcode:              Mapped[str|None]        = mapped_column(String(20), nullable=True)
    result:               Mapped[str]             = mapped_column(String(20), nullable=False)  # available|unavailable
    matched_tenants_count:Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    best_match_level:     Mapped[str|None]        = mapped_column(String(20), nullable=True)
    request_payload:      Mapped[dict]            = mapped_column(JSONB, default=dict, nullable=False)
    response_payload:     Mapped[dict]            = mapped_column(JSONB, default=dict, nullable=False)
