"""Weather lookups, cached, plus the risk judgement that scheduling depends on."""
from __future__ import annotations

import datetime as dt

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.weather.constants import (
    ADVISORY_HORIZON_HOURS, CACHE_TTL_MINUTES, COLD_C_SEVERE, HEAT_C_SEVERE,
    RAIN_MM_ADVISORY, RAIN_MM_SEVERE, RISK_ADVISORY, RISK_NONE, RISK_SEVERE,
    WIND_KMH_ADVISORY, WIND_KMH_SEVERE,
)
from app.engines.weather.models import KIND_CURRENT, KIND_FORECAST, WeatherReadingCache
from app.engines.weather.provider import (
    WeatherProvider, WeatherReading, resolve_weather_provider,
)

logger = structlog.get_logger("weather.service")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class WeatherService:
    def __init__(self, db: AsyncSession, provider: WeatherProvider | None = None):
        self.db = db
        self.provider = provider or resolve_weather_provider()

    @property
    def configured(self) -> bool:
        """Whether a real source exists. Callers use this to decide between "the
        weather is fine" and "we do not know" -- two different answers."""
        return self.provider.configured

    # ── Reads ────────────────────────────────────────────────────────────────

    async def current(self, place: str | None) -> WeatherReading | None:
        if not place or not self.configured:
            return None
        return await self._cached(place=place, kind=KIND_CURRENT, target_hour=None)

    async def at(self, place: str | None, when: dt.datetime | None) -> WeatherReading | None:
        if not place or not when or not self.configured:
            return None
        hour = when.astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
        return await self._cached(place=place, kind=KIND_FORECAST, target_hour=hour)

    async def _cached(
        self, *, place: str, kind: str, target_hour: dt.datetime | None,
    ) -> WeatherReading | None:
        """Cache-then-provider, and on a provider failure the STALE row is returned
        rather than nothing.

        That trade is deliberate: an hour-old temperature is a far better answer than
        a blank widget, and for a slot advisory it is better than silently dropping a
        warning because one HTTP call timed out. The row's own `observed_at` travels
        with it, so nothing pretends the reading is newer than it is.
        """
        row = (await self.db.execute(
            select(WeatherReadingCache).where(
                WeatherReadingCache.place == place,
                WeatherReadingCache.kind == kind,
                WeatherReadingCache.target_hour == target_hour,
            )
        )).scalars().first()

        fresh_until = _now() - dt.timedelta(minutes=CACHE_TTL_MINUTES)
        if row and row.fetched_at and row.fetched_at > fresh_until:
            return self._from_row(row)

        reading = (
            await self.provider.current(place=place) if kind == KIND_CURRENT
            else await self.provider.at(place=place, when=target_hour)
        )
        if reading is None:
            return self._from_row(row) if row else None

        if row is None:
            row = WeatherReadingCache(place=place, kind=kind, target_hour=target_hour)
            self.db.add(row)
        row.observed_at = reading.observed_at
        row.temperature_c = reading.temperature_c
        row.condition = reading.condition or None
        row.rain_mm = reading.rain_mm
        row.wind_kmh = reading.wind_kmh
        row.fetched_at = _now()
        await self.db.flush()
        return reading

    @staticmethod
    def _from_row(row: WeatherReadingCache) -> WeatherReading:
        return WeatherReading(
            observed_at=row.observed_at,
            temperature_c=row.temperature_c,
            condition=row.condition or "",
            rain_mm=row.rain_mm or 0.0,
            wind_kmh=row.wind_kmh or 0.0,
            is_day=True,
        )


def assess_risk(reading: WeatherReading | None) -> dict:
    """What this weather means for a visit.

    Returns {"level", "reason", "reading"}. `level` is:

      none      nothing worth saying
      advisory  the visit may run late -- tell the customer, do not move anything
      severe    unsafe to send someone -- rescheduling is the right call

    A NULL reading is `none` with a stated reason of "unknown", NOT a quiet pass:
    callers that must distinguish "fine" from "we cannot see" read `reading is None`,
    which is why the reading travels back with the verdict.
    """
    if reading is None:
        return {"level": RISK_NONE, "reason": "unknown", "reading": None}

    if (
        reading.rain_mm >= RAIN_MM_SEVERE
        or reading.wind_kmh >= WIND_KMH_SEVERE
        or reading.temperature_c >= HEAT_C_SEVERE
        or reading.temperature_c <= COLD_C_SEVERE
    ):
        return {"level": RISK_SEVERE, "reason": _reason(reading), "reading": reading.to_dict()}

    if reading.rain_mm >= RAIN_MM_ADVISORY or reading.wind_kmh >= WIND_KMH_ADVISORY:
        return {"level": RISK_ADVISORY, "reason": _reason(reading), "reading": reading.to_dict()}

    return {"level": RISK_NONE, "reason": "clear", "reading": reading.to_dict()}


def _reason(reading: WeatherReading) -> str:
    """The single dominant factor, so the customer-facing line can name it. Ordered
    by how much each actually disrupts a visit in Indian conditions."""
    if reading.rain_mm >= RAIN_MM_ADVISORY:
        return "heavy_rain"
    if reading.wind_kmh >= WIND_KMH_ADVISORY:
        return "high_wind"
    if reading.temperature_c >= HEAT_C_SEVERE:
        return "extreme_heat"
    if reading.temperature_c <= COLD_C_SEVERE:
        return "extreme_cold"
    return "clear"


def within_advisory_horizon(slot_at: dt.datetime | None, now: dt.datetime | None = None) -> bool:
    """Whether a slot is close enough to warn about.

    Past slots are excluded as well as distant ones: a warning about a visit that
    has already happened is noise, and a forecast a week out is not worth the
    anxiety it would cause.
    """
    if slot_at is None:
        return False
    moment = now or _now()
    delta = slot_at.astimezone(dt.timezone.utc) - moment
    return dt.timedelta(0) <= delta <= dt.timedelta(hours=ADVISORY_HORIZON_HOURS)
