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
    RAIN_MM_ADVISORY, RAIN_MM_SEVERE, RISK_ADVISORY,
    RISK_NONE, RISK_SEVERE, WIND_KMH_SEVERE,
)
from app.engines.weather.provider import (
    NullWeatherProvider, WeatherApiProvider, WeatherReading, resolve_weather_provider,
)
from app.engines.weather.scheduling import weather_reschedule_permitted
from app.engines.weather.service import assess_risk
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

def test_no_key_means_the_null_provider_and_a_key_means_the_real_one():
    """Asserted by CONTROLLING the setting, not by reading whatever this machine
    happens to have: an earlier version passed only because no key was configured,
    and started failing the moment one was -- testing the environment, not the code.
    """
    from app.engines.weather import provider as provider_module

    class _Settings:
        def __init__(self, key):
            self.WEATHERAPI_KEY = key

    with patch.object(provider_module, "get_settings", lambda: _Settings("")):
        empty = resolve_weather_provider()
    assert isinstance(empty, NullWeatherProvider)
    assert empty.configured is False

    with patch.object(provider_module, "get_settings", lambda: _Settings("  a-real-key  ")):
        configured = resolve_weather_provider()
    assert isinstance(configured, WeatherApiProvider)
    assert configured.configured is True


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


# ── The provider safety gate ────────────────────────────────────────

# The gate is the platform's ONLY weather caller: a provider picking weather as the
# reason is the one thing that spends a lookup. The customer-facing slot advisory that
# also lived here was removed along with the Home widget.

def _service(configured: bool, reading: WeatherReading | None):
    service = MagicMock()
    service.configured = configured
    service.at = AsyncMock(return_value=reading)
    return service


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


# ── Two bugs found the moment a real API key was added ───────────────────────

def test_an_indian_pin_code_is_not_treated_as_a_location():
    """Live: `q=140412` answers `1006 No matching location found` -- postcode lookup
    covers US/UK/Canada, not India. A PIN on its own must resolve to nothing rather
    than being sent and silently failing."""
    from app.engines.weather.place import resolve_place
    assert resolve_place(zipcode="140412") is None


def test_a_city_is_always_qualified_with_its_state_and_country():
    """Live, and the more dangerous of the two: `q=Bassi Pathana` returned a valid
    200 for Pathana in Uva, SRI LANKA -- real weather from the wrong country, with
    nothing about the response looking wrong."""
    from app.engines.weather.place import COUNTRY, resolve_place
    place = resolve_place(city="Bassi Pathana", state="Punjab", zipcode="140412")
    assert place == f"Bassi Pathana,Punjab,{COUNTRY}"


def test_coordinates_win_when_the_address_has_them():
    # Exact, and immune to the wrong-country problem entirely.
    from app.engines.weather.place import resolve_place
    assert resolve_place(city="Bassi Pathana", state="Punjab", latitude=30.45, longitude=76.36) == "30.45,76.36"


def test_a_reading_from_another_country_is_discarded():
    provider = WeatherApiProvider("test-key")
    body = {"location": {"country": "Sri Lanka"}, "current": {"temp_c": 27}}
    assert provider._in_expected_country(body, "Bassi Pathana") is False
    assert provider._in_expected_country({"location": {"country": "India"}}, "Ludhiana") is True


@pytest.mark.asyncio
async def test_a_forecast_hour_is_truncated_in_local_time_not_utc():
    """Real bug: India is +05:30, so a local hour boundary lands on :30 in UTC.
    Truncating the UTC timestamp to :00 moved every lookup back half an hour, into
    the PREVIOUS hourly block -- a 10:00 slot consulted the 09:00 forecast. Nothing
    errored; the answer was just quietly for the wrong hour."""
    from app.engines.weather.service import WeatherService

    asked = {}

    class Provider:
        configured = True

        async def current(self, *, place):
            return None

        async def at(self, *, place, when):
            asked["when"] = when
            return _reading()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: None)))
    db.add = MagicMock()
    db.flush = AsyncMock()

    slot = dt.datetime(2026, 8, 11, 10, 0, tzinfo=IST)
    await WeatherService(db, provider=Provider()).at("30.4,76.4", slot)

    # The hour the provider is asked about must still BE 10:00 local, which is
    # 04:30 UTC -- not 04:00, which is 09:30 local and the wrong block.
    assert asked["when"].astimezone(IST).hour == 10
    assert asked["when"].astimezone(dt.timezone.utc).minute == 30


def test_a_reading_reports_its_own_observation_time():
    # A cached reading carries its age rather than pretending to be current.
    reading = _reading()
    assert reading.to_dict()["observed_at"].startswith("2026-08-12T14:00")


# ── The one place a screen triggers a weather lookup ─────────────────────────

class TestEligibilityEndpoint:
    """`GET .../weather-reschedule-eligibility` is the only screen-driven weather
    caller in the platform, and it runs because a provider explicitly picked weather
    as the reason for moving a visit."""

    @staticmethod
    def _request():
        return type("R", (), {"state": type("S", (), {"request_id": "req-1"})()})()

    @staticmethod
    def _job():
        job = MagicMock()
        job.tenant_id = "11111111-1111-1111-1111-111111111111"
        job.scheduled_date = dt.date(2026, 8, 12)
        job.scheduled_time_window = "09:00-10:00"
        job.address_snapshot = {"city": "Ludhiana", "state": "Punjab",
                                "latitude": 30.9, "longitude": 75.85}
        job.city = "Ludhiana"
        job.zipcode = "141002"
        return job

    async def _call(self, **kwargs):
        import uuid as _uuid
        from app.engines.home_service_assignment import provider_router as pr
        from app.exceptions import ServiceOSException

        captured = {}

        async def fake_permitted(db, *, place, slot_at):
            captured["slot_at"] = slot_at
            captured["place"] = place
            return {"permitted": True, "level": RISK_SEVERE, "reason": "heavy_rain",
                    "reading": None, "detail": "ok"}

        svc = MagicMock()
        svc._load_job = AsyncMock(return_value=self._job())
        user = MagicMock()
        user.tenant_id = "11111111-1111-1111-1111-111111111111"

        with patch.object(pr, "HomeServiceJobAssignmentService", return_value=svc), \
             patch("app.engines.weather.scheduling.weather_reschedule_permitted",
                   side_effect=fake_permitted):
            response = await pr.get_weather_reschedule_eligibility(
                job_id=_uuid.uuid4(), r=self._request(), user=user, db=AsyncMock(),
                **kwargs,
            )
        return response, captured

    @pytest.mark.asyncio
    async def test_checks_the_slot_being_moved_TO_when_one_is_given(self):
        # The gate on POST /schedule checks the target slot. If this endpoint answered
        # about the CURRENT slot, a provider would be told "weather reschedule allowed"
        # and then refused on save -- for a slot whose forecast was never examined.
        _, captured = await self._call(
            scheduled_date=dt.date(2026, 8, 14), scheduled_time_window="16:00-17:00",
        )
        assert captured["slot_at"] == dt.datetime(2026, 8, 14, 16, tzinfo=IST)

    @pytest.mark.asyncio
    async def test_falls_back_to_the_jobs_current_slot(self):
        _, captured = await self._call(scheduled_date=None, scheduled_time_window=None)
        assert captured["slot_at"] == dt.datetime(2026, 8, 12, 9, tzinfo=IST)

    @pytest.mark.asyncio
    async def test_asks_about_the_jobs_coordinates_rather_than_its_pin(self):
        # A bare Indian PIN is not resolvable by this provider, and a bare city name
        # once resolved "Bassi Pathana" to Sri Lanka.
        _, captured = await self._call(scheduled_date=None, scheduled_time_window=None)
        assert captured["place"] == "30.9,75.85"

    @pytest.mark.asyncio
    async def test_a_job_from_another_tenant_is_never_checked(self):
        import uuid as _uuid
        from app.engines.home_service_assignment import provider_router as pr
        from app.exceptions import ServiceOSException

        job = self._job()
        job.tenant_id = "22222222-2222-2222-2222-222222222222"
        svc = MagicMock()
        svc._load_job = AsyncMock(return_value=job)
        user = MagicMock()
        user.tenant_id = "11111111-1111-1111-1111-111111111111"

        with patch.object(pr, "HomeServiceJobAssignmentService", return_value=svc), \
             patch("app.engines.weather.scheduling.weather_reschedule_permitted") as permitted:
            with pytest.raises(ServiceOSException) as exc:
                await pr.get_weather_reschedule_eligibility(
                    job_id=_uuid.uuid4(), r=self._request(), user=user, db=AsyncMock(),
                )
        permitted.assert_not_called()
        assert exc.value.error_code == "JOB_ASSIGNMENT_JOB_NOT_FOUND"
