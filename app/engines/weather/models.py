"""Cached weather readings.

Cached in the database rather than in process memory because several workers serve
the same PIN codes: an in-memory cache would multiply the API calls by the number of
workers, which is exactly what a free tier cannot absorb.

Rows are overwritten per (place, kind, target_hour), so the table stays proportional
to the number of PIN codes served rather than growing with traffic.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

KIND_CURRENT = "current"
KIND_FORECAST = "forecast"


class WeatherReadingCache(ServiceOSBase):
    __tablename__ = "weather_readings"
    __table_args__ = (
        UniqueConstraint("place", "kind", "target_hour", name="uq_weather_place_kind_hour"),
        Index("ix_weather_fetched_at", "fetched_at"),
    )

    # The PIN code (or city) the reading was fetched for, as asked of the provider.
    place: Mapped[str] = mapped_column(String(60), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default=KIND_CURRENT)
    # Null for a current reading; the hour being forecast otherwise. Part of the
    # unique key so forecasts for different hours do not evict each other.
    target_hour: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rain_mm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    wind_kmh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # When WE fetched it, which is what the TTL is measured against -- distinct from
    # `observed_at`, which is when the weather itself was measured.
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
