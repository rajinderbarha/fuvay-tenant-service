"""Weather providers.

Same shape as the masked-calling engine, and for the same reason: an integration
nobody has configured yet must degrade to HONEST SILENCE, never to a plausible
default. A fabricated "clear skies, 28°C" is worse than no weather at all -- the
whole point of this data is deciding whether it is safe to send a technician out on
a bike, and a comfortable-looking guess is exactly the wrong answer to that.

`NullWeatherProvider` is the default. It returns nothing, every caller treats that
as "unknown", and the app hides the widget and withholds weather-based rescheduling
rather than inventing either.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger("weather.provider")


@dataclass(frozen=True)
class WeatherReading:
    """One point in time at one place. Every field is what the provider actually
    returned; nothing is derived or filled in."""
    observed_at: dt.datetime
    temperature_c: float
    condition: str
    """Provider wording, shown to nobody -- the app renders our own copy."""
    rain_mm: float
    wind_kmh: float
    is_day: bool

    def to_dict(self) -> dict:
        return {
            "observed_at": self.observed_at.isoformat(),
            "temperature_c": round(self.temperature_c, 1),
            "condition": self.condition,
            "rain_mm": round(self.rain_mm, 1),
            "wind_kmh": round(self.wind_kmh, 1),
            "is_day": self.is_day,
        }


class WeatherProvider(Protocol):
    """A source of weather for a place, now and at a future hour."""

    @property
    def configured(self) -> bool: ...

    async def current(self, *, place: str) -> WeatherReading | None: ...

    async def at(self, *, place: str, when: dt.datetime) -> WeatherReading | None: ...


class NullWeatherProvider:
    """No weather source. Returns nothing, always.

    Deliberately not "sunny and mild": callers must be able to distinguish "the
    weather is fine" from "we do not know", because the second one is what makes a
    weather-based reschedule unavailable rather than falsely denied.
    """

    @property
    def configured(self) -> bool:
        return False

    async def current(self, *, place: str) -> WeatherReading | None:
        return None

    async def at(self, *, place: str, when: dt.datetime) -> WeatherReading | None:
        return None


class WeatherApiProvider:
    """weatherapi.com -- current conditions plus an hourly forecast.

    Chosen over a current-conditions-only API because the scheduling advisory needs
    the forecast FOR THE HOUR OF THE VISIT, not the weather while the customer
    happens to be looking at their phone.

    Every failure -- transport, HTTP status, an unexpected body -- returns None and
    is logged. A weather lookup must never break a booking screen or a reschedule.
    """

    BASE_URL = "https://api.weatherapi.com/v1"
    TIMEOUT_S = 6.0

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def _get(self, path: str, params: dict) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_S) as client:
                response = await client.get(
                    f"{self.BASE_URL}{path}", params={"key": self._api_key, **params},
                )
            if response.status_code != 200:
                logger.warning("weather.http_error", status=response.status_code, path=path)
                return None
            return response.json()
        except Exception as exc:  # noqa: BLE001 -- weather must never break a screen
            logger.warning("weather.request_failed", error=str(exc), path=path)
            return None

    @staticmethod
    def _reading(block: dict, *, observed_at: dt.datetime) -> WeatherReading | None:
        try:
            return WeatherReading(
                observed_at=observed_at,
                temperature_c=float(block["temp_c"]),
                condition=str((block.get("condition") or {}).get("text") or "").strip(),
                # `precip_mm` is the hour's total on a forecast block and the last
                # hour's on a current one -- both are "rain around this time",
                # which is the question being asked.
                rain_mm=float(block.get("precip_mm") or 0.0),
                wind_kmh=float(block.get("wind_kph") or 0.0),
                is_day=bool(block.get("is_day", 1)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("weather.unexpected_body", error=str(exc))
            return None

    async def current(self, *, place: str) -> WeatherReading | None:
        body = await self._get("/current.json", {"q": place, "aqi": "no"})
        if not body:
            return None
        current = body.get("current") or {}
        epoch = current.get("last_updated_epoch")
        observed_at = (
            dt.datetime.fromtimestamp(epoch, dt.timezone.utc) if epoch
            else dt.datetime.now(dt.timezone.utc)
        )
        return self._reading(current, observed_at=observed_at)

    async def at(self, *, place: str, when: dt.datetime) -> WeatherReading | None:
        """The forecast for the HOUR containing `when`.

        Asks for enough days to cover the target and then picks the matching hour,
        rather than trusting the API's day ordering: an off-by-one day here would
        silently advise on the wrong date.
        """
        target = when.astimezone(dt.timezone.utc)
        days = max(1, min(3, (target.date() - dt.datetime.now(dt.timezone.utc).date()).days + 1))
        body = await self._get("/forecast.json", {"q": place, "days": days, "aqi": "no", "alerts": "no"})
        if not body:
            return None
        hours = [
            hour
            for day in ((body.get("forecast") or {}).get("forecastday") or [])
            for hour in (day.get("hour") or [])
        ]
        if not hours:
            return None
        best = min(
            hours,
            key=lambda h: abs(
                dt.datetime.fromtimestamp(h.get("time_epoch", 0), dt.timezone.utc) - target
            ),
        )
        observed_at = dt.datetime.fromtimestamp(best.get("time_epoch", 0), dt.timezone.utc)
        # A "forecast" for an hour that is not near the one asked about is not an
        # answer. Two hours of slack covers provider rounding without letting a
        # missing day pass as a match.
        if abs((observed_at - target).total_seconds()) > 2 * 3600:
            logger.warning("weather.no_hour_for_target", target=target.isoformat())
            return None
        return self._reading(best, observed_at=observed_at)


def resolve_weather_provider() -> WeatherProvider:
    """The configured provider, or the Null one.

    Keyed off a single setting so a deployment turns weather on by adding a key and
    nothing else -- and off by removing it, with every dependent feature degrading
    on its own rather than erroring.
    """
    key = (getattr(get_settings(), "WEATHERAPI_KEY", "") or "").strip()
    return WeatherApiProvider(key) if key else NullWeatherProvider()
