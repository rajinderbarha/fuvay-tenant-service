"""Geo Engine — Models (3 tables)."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class ServiceZone(ServiceOSBase):
    """Versioned service zone per tenant. valid_until=None = currently active."""
    __tablename__ = "service_zones"
    __table_args__ = (Index("ix_sz_tenant_active", "tenant_id", "is_active"),)

    tenant_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_name:    Mapped[str]       = mapped_column(String(100), nullable=False)
    zone_type:    Mapped[str]       = mapped_column(String(20), nullable=False)
    identifiers:  Mapped[list]      = mapped_column(JSONB, default=list, nullable=False)
    center_lat:   Mapped[float|None]= mapped_column(Float, nullable=True)
    center_lng:   Mapped[float|None]= mapped_column(Float, nullable=True)
    radius_km:    Mapped[float|None]= mapped_column(Float, nullable=True)
    surcharge_pct:Mapped[float]     = mapped_column(Float, default=0.0, nullable=False)
    is_active:    Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    valid_from:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    valid_until:  Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    set_by:       Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)


class StaffLocation(ServiceOSBase):
    """Current staff coordinates. Updated every 5 min from mobile app."""
    __tablename__ = "staff_locations"
    __table_args__ = (UniqueConstraint("staff_id","tenant_id", name="uq_sl_staff_tenant"),
                      Index("ix_sl_tenant", "tenant_id"))

    staff_id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    latitude:     Mapped[float]     = mapped_column(Float, nullable=False)
    longitude:    Mapped[float]     = mapped_column(Float, nullable=False)
    accuracy_m:   Mapped[float|None]= mapped_column(Float, nullable=True)
    status:       Mapped[str]       = mapped_column(String(20), default="available", nullable=False)
    last_ping_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    active_job_count: Mapped[int]   = mapped_column(Integer, default=0, nullable=False)
    meta:         Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)


class ZoneAnalyticSnapshot(ServiceOSBase):
    """Daily zone usage metrics for heat maps and coverage analysis."""
    __tablename__ = "zone_analytic_snapshots"
    __table_args__ = (Index("ix_zan_zone_date", "zone_id", "snapshot_date"),)

    zone_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:     Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_date: Mapped[str]       = mapped_column(String(10), nullable=False)
    job_count:     Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    avg_response_min: Mapped[float]  = mapped_column(Float, default=0.0, nullable=False)
    completion_rate:  Mapped[float]  = mapped_column(Float, default=100.0, nullable=False)
