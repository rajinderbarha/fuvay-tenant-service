"""Location Engine — India Location Hierarchy Master Data.

Tables: location_states, location_districts, location_cities, location_zones.
Admin-managed. Used by tenant/provider profile, address validation, and cascade filters.
"""
from __future__ import annotations
import uuid
from sqlalchemy import Boolean, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class LocationState(ServiceOSBase):
    """Master list of states. India-first."""
    __tablename__ = "location_states"
    __table_args__ = (
        UniqueConstraint("country_code", "state_code", name="uq_ls_country_state"),
        Index("ix_ls_country_code", "country_code"),
        Index("ix_ls_is_active", "is_active"),
    )

    country_code: Mapped[str] = mapped_column(String(5), nullable=False, default="IN")
    state_name: Mapped[str] = mapped_column(String(100), nullable=False)
    state_code: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LocationDistrict(ServiceOSBase):
    """Districts within a state."""
    __tablename__ = "location_districts"
    __table_args__ = (
        Index("ix_ld_state_id", "state_id"),
        Index("ix_ld_is_active", "is_active"),
    )

    state_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    district_name: Mapped[str] = mapped_column(String(100), nullable=False)
    district_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LocationCity(ServiceOSBase):
    """Cities within a district."""
    __tablename__ = "location_cities"
    __table_args__ = (
        Index("ix_lc_state_id", "state_id"),
        Index("ix_lc_district_id", "district_id"),
        Index("ix_lc_city_tier", "city_tier"),
        Index("ix_lc_is_active", "is_active"),
    )

    state_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    city_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # small | mid | large | metro
    city_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LocationZone(ServiceOSBase):
    """Zones/pincodes within a city."""
    __tablename__ = "location_zones"
    __table_args__ = (
        Index("ix_lz_state_id", "state_id"),
        Index("ix_lz_district_id", "district_id"),
        Index("ix_lz_city_id", "city_id"),
        Index("ix_lz_pincode", "pincode"),
        Index("ix_lz_is_active", "is_active"),
    )

    state_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    district_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    city_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
