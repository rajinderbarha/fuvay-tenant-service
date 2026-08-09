"""MODULE-L5-60 — weather: honest absence, risk judgement, and the safety gate.

The single rule this engine is built around: with no weather source, every dependent
feature must degrade to SILENCE, never to a plausible default. A fabricated "clear
skies, 28C" is worse than no weather at all, because the data exists to decide
whether it is safe to send a technician out on a bike.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.weather.constants import (
    ADVISORY_HORIZON_HOURS, RAIN_MM_ADVISORY, RAIN_MM_SEVERE, RISK_ADVISORY,
    RISK_NONE, RISK_SEVERE, WIND_KMH_SEVERE,
)
from app.engines.weather.provider import (
    NullWeatherProvider, WeatherApiProvider, WeatherReading, resolve_weather_provider,
)
from app.engines.weather.scheduling import slot_advisory, weather_reschedule_permitted
from app.engines.weather.service import assess_risk, within_advisory_horizon
from app.engines.weather.slots import slot_start

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _reading(**overrides) -> WeatherReading:
    base = dict(
        observed_at=dt.datetime(2026, 8, 12, 14, tzinfo=dt.timezone.utc),
        temperature_c=29.0, condition="Partly cloudy", rain_mm=0.0, wind_kmh=8.0, is_day=True,
    )
    base.update(overrides)
    return WeatherReading(**base)


# ── Honest absence ───────────────────────────────────────────────────────────

def test_the_default_provider_is_the_null_one():
    # No key configured on this deployment, so nothing must claim to know the
    # weather.
    provider = resolve_weather_provider()
    assert isinstance(provider, NullWeatherProvider)
    assert provider.configured is False


@pytest.mark.asyncio
async def test_the_null_provider_returns_nothing_not_fair_weather():
    """Callers must be able to tell "fine" from "we cannot see", because the second
    is what makes a weather reschedule UNAVAILABLE rather than falsely denied."""
    provider = NullWeatherProvider()
    assert await provider.current(place="140412") is None
    assert await provider.at(place="140412", when=dt.datetime.now(dt.timezone.utc)) is None


def test_an_unknown_reading_is_not_a_quiet_pass():
    verdict = assess_risk(None)
    assert verdict["level"] == RISK_NONE
    # Stated as unknown, and the absent reading travels back, so a caller that must
    # distinguish the two can.
    assert verdict["reason"] == "unknown"
    assert verdict["reading"] is None


# ── Risk judgement ───────────────────────────────────────────────────────────

def test_ordinary_weather_raises_nothing():
    assert assess_risk(_reading())["level"] == RISK_NONE
    # Light monsoon rain is unremarkable in India -- a technician works through it.
    assert assess_risk(_reading(rain_mm=RAIN_MM_ADVISORY - 1))["level"] == RISK_NONE


def test_heavy_rain_is_an_advisory_and_very_heavy_rain_is_severe():
    assert assess_risk(_reading(rain_mm=RAIN_MM_ADVISORY))["level"] == RISK_ADVISORY
    assert assess_risk(_reading(rain_mm=RAIN_MM_SEVERE))["level"] == RISK_SEVERE


def test_dangerous_wind_and_extreme_temperatures_are_severe():
    assert assess_risk(_reading(wind_kmh=WIND_KMH_SEVERE))["level"] == RISK_SEVERE
    assert assess_risk(_reading(temperature_c=44))["level"] == RISK_SEVERE
    assert assess_risk(_reading(temperature_c=1))["level"] == RISK_SEVERE


def test_the_verdict_names_the_dominant_factor():
    assert assess_risk(_reading(rain_mm=RAIN_MM_SEVERE))["reason"] == "heavy_rain"
    assert assess_risk(_reading(temperature_c=45))["reason"] == "extreme_heat"
    assert assess_risk(_reading())["reason"] == "clear"


# ── The advisory horizon ─────────────────────────────────────────────────────

def test_only_slots_close_enough_to_forecast_are_warned_about():
    now = dt.datetime(2026, 8, 12, 9, tzinfo=dt.timezone.utc)
    assert within_advisory_horizon(now + dt.timedelta(hours=3), now) is True
    # A forecast a week out is not worth the anxiety it would cause.
    assert within_advisory_horizon(now + dt.timedelta(hours=ADVISORY_HORIZON_HOURS + 1), now) is False
    # A warning about a visit that already happened is noise.
    assert within_advisory_horizon(now - dt.timedelta(hours=1), now) is False
    assert within_advisory_horizon(None, now) is False


# ── Slot arithmetic ──────────────────────────────────────────────────────────

def test_a_slot_window_is_read_as_local_time():
    """The stored window is wall-clock text with no offset. Reading it as UTC would
    look the forecast up five and a half hours late -- the wrong day, for an evening
    slot."""
    start = slot_start(dt.date(2026, 8, 12), "14:00-15:00")
    assert start == dt.datetime(2026, 8, 12, 14, tzinfo=IST)


def test_an_unreadable_window_yields_nothing_rather_than_a_guessed_hour():
    # A forecast for the wrong hour is worse than none, because it is shown as fact.
    assert slot_start(dt.date(2026, 8, 12), "sometime after lunch") is None
    assert slot_start(None, "14:00-15:00") is None


def test_a_date_with_no_window_uses_a_stated_default():
    assert slot_start(dt.date(2026, 8, 12), None) == dt.datetime(2026, 8, 12, 9, tzinfo=IST)


# ── Customer advisory ────────────────────────────────────────────────────────

def _service(configured: bool, reading: WeatherReading | None):
    service = MagicMock()
    service.configured = configured
    service.at = AsyncMock(return_value=reading)
    return service


@pytest.mark.asyncio
async def test_no_weather_source_means_no_advisory_at_all():
    with patch("app.engines.weather.service.WeatherService", return_value=_service(False, None)):
        result = await slot_advisory(
            AsyncMock(), place="140412",
            slot_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3),
        )
    assert result is None


@pytest.mark.asyncio
async def test_ordinary_weather_produces_no_advisory():
    # Silence, not reassurance: a "conditions look fine" line is a claim, and this
    # feature only speaks when it has something real to warn about.
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, _reading())):
        result = await slot_advisory(
            AsyncMock(), place="140412",
            slot_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3),
        )
    assert result is None


@pytest.mark.asyncio
async def test_heavy_rain_near_a_slot_warns_that_the_visit_may_run_late():
    reading = _reading(rain_mm=RAIN_MM_ADVISORY + 1)
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, reading)):
        result = await slot_advisory(
            AsyncMock(), place="140412",
            slot_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3),
        )
    assert result["level"] == RISK_ADVISORY
    assert result["reason"] == "heavy_rain"
    assert "run late" in result["message"]
    # The reading travels with it so support can see what the customer was told.
    assert result["reading"]["rain_mm"] > RAIN_MM_ADVISORY


@pytest.mark.asyncio
async def test_severe_weather_says_the_provider_may_move_it_for_technician_safety():
    reading = _reading(rain_mm=RAIN_MM_SEVERE + 5)
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, reading)):
        result = await slot_advisory(
            AsyncMock(), place="140412",
            slot_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2),
        )
    assert result["level"] == RISK_SEVERE
    assert "safety" in result["message"]
    # It warns; it does not claim the visit HAS been moved.
    assert "moved" not in result["message"].lower() or "may need to move" in result["message"]


# ── The provider safety gate ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_weather_is_not_an_available_reason_without_a_weather_source():
    """The gate that matters. A reason nobody can check gets used for everything, and
    then the record of why visits move stops meaning anything."""
    with patch("app.engines.weather.service.WeatherService", return_value=_service(False, None)):
        verdict = await weather_reschedule_permitted(
            AsyncMock(), place="140412", slot_at=dt.datetime.now(dt.timezone.utc),
        )
    assert verdict["permitted"] is False
    assert "No weather source" in verdict["detail"]


@pytest.mark.asyncio
async def test_weather_is_not_an_available_reason_without_a_reading_for_that_slot():
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, None)):
        verdict = await weather_reschedule_permitted(
            AsyncMock(), place="140412", slot_at=dt.datetime.now(dt.timezone.utc),
        )
    assert verdict["permitted"] is False
    assert "No weather reading" in verdict["detail"]


@pytest.mark.asyncio
async def test_weather_is_refused_when_the_forecast_is_unremarkable():
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, _reading())):
        verdict = await weather_reschedule_permitted(
            AsyncMock(), place="140412", slot_at=dt.datetime.now(dt.timezone.utc),
        )
    assert verdict["permitted"] is False
    assert verdict["level"] == RISK_NONE


@pytest.mark.asyncio
async def test_weather_is_permitted_on_genuinely_disruptive_conditions():
    reading = _reading(rain_mm=RAIN_MM_SEVERE + 1)
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, reading)):
        verdict = await weather_reschedule_permitted(
            AsyncMock(), place="140412", slot_at=dt.datetime.now(dt.timezone.utc),
        )
    assert verdict["permitted"] is True
    assert verdict["level"] == RISK_SEVERE
    assert verdict["reading"] is not None


@pytest.mark.asyncio
async def test_a_job_with_no_slot_cannot_use_weather_as_a_reason():
    with patch("app.engines.weather.service.WeatherService", return_value=_service(True, _reading())):
        verdict = await weather_reschedule_permitted(AsyncMock(), place="140412", slot_at=None)
    assert verdict["permitted"] is False
    assert "no scheduled slot" in verdict["detail"]


# ── The HTTP provider's failure behaviour ────────────────────────────────────

@pytest.mark.asyncio
async def test_the_http_provider_returns_nothing_on_a_bad_response():
    """A weather lookup must never break a booking screen or a reschedule."""
    provider = WeatherApiProvider("test-key")
    with patch.object(provider, "_get", AsyncMock(return_value=None)):
        assert await provider.current(place="140412") is None
        assert await provider.at(place="140412", when=dt.datetime.now(dt.timezone.utc)) is None


@pytest.mark.asyncio
async def test_the_http_provider_rejects_a_forecast_for_the_wrong_hour():
    """A "forecast" for an hour nowhere near the one asked about is not an answer --
    it is how a missing day silently passes as a match."""
    provider = WeatherApiProvider("test-key")
    target = dt.datetime(2026, 8, 12, 14, tzinfo=dt.timezone.utc)
    far_off = int((target + dt.timedelta(hours=9)).timestamp())
    body = {"forecast": {"forecastday": [{"hour": [
        {"time_epoch": far_off, "temp_c": 30, "condition": {"text": "Sunny"},
         "precip_mm": 0, "wind_kph": 5, "is_day": 1},
    ]}]}}
    with patch.object(provider, "_get", AsyncMock(return_value=body)):
        assert await provider.at(place="140412", when=target) is None


def test_a_reading_reports_its_own_observation_time():
    # A cached reading carries its age rather than pretending to be current.
    reading = _reading()
    assert reading.to_dict()["observed_at"].startswith("2026-08-12T14:00")
