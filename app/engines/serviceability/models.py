"""Serviceability Engine — Models (4 tables)."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, text
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
    """Defines a geographic area a tenant covers for services."""
    __tablename__ = "tenant_service_areas"
    __table_args__ = (
        Index("ix_tsa_tenant_city",    "tenant_id", "city", "is_active"),
        Index("ix_tsa_tenant_zip",     "tenant_id", "zipcode", "is_active"),
        Index("ix_tsa_city_zip",       "city", "zipcode"),
        Index("ix_tsa_tenant_coverage_city_zip",
              "tenant_id", "coverage_type", "city", "zipcode"),
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


class TenantServiceAreaService(ServiceOSBase):
    """Maps a specific service (+ job_type) to a tenant service area."""
    __tablename__ = "tenant_service_area_services"
    __table_args__ = (
        Index("ix_tsas_area_available", "tenant_service_area_id", "is_available"),
        Index("ix_tsas_service_type",   "service_id", "job_type", "is_available"),
        Index("ix_tsas_tenant",         "tenant_id", "is_available"),
        Index("ix_tsas_tenant_service_job", "tenant_id", "service_id", "job_type"),
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
