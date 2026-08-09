"""Weather in scheduling decisions.

Two different jobs, deliberately separated:

* `slot_advisory` is what the CUSTOMER is told about a visit that is close enough to
  forecast. It never moves anything -- it says the visit may run late, or that the
  provider may need to move it, so the customer is not left wondering why a
  technician is not at the door in a storm.

* `weather_reschedule_permitted` is what the PROVIDER is allowed to do. Rescheduling
  for weather exists for technician safety, and it is gated on a REAL reading: with
  no weather source, or no reading for that slot, "weather" is not an available
  reason. The provider can still reschedule -- they simply have to give the real
  reason rather than attributing it to conditions the system cannot see.

That gate is the whole point. A reschedule reason that cannot be checked is a
reason that gets used for everything, and the record of why visits move stops
meaning anything.
"""
from __future__ import annotations

import datetime as dt

from app.engines.weather.constants import (
    RISK_ADVISORY, RISK_NONE, RISK_SEVERE,
)
from app.engines.weather.service import assess_risk, within_advisory_horizon

# Customer-facing copy per reason. Written to be true of what the platform will
# actually do: it warns, it does not promise a reschedule the provider has not
# agreed to.
_ADVISORY_COPY = {
    "heavy_rain": "Heavy rain is forecast around your slot, so your technician may run late.",
    "high_wind": "Strong winds are forecast around your slot, so your technician may run late.",
    "extreme_heat": "Extreme heat is forecast around your slot, so your technician may run late.",
    "extreme_cold": "Very cold weather is forecast around your slot, so your technician may run late.",
}
_SEVERE_COPY = {
    "heavy_rain": "Very heavy rain is forecast around your slot. Your provider may need to move the visit for the technician's safety — we'll let you know.",
    "high_wind": "Dangerous winds are forecast around your slot. Your provider may need to move the visit for the technician's safety — we'll let you know.",
    "extreme_heat": "Extreme heat is forecast around your slot. Outdoor and rooftop work may have to be moved for the technician's safety.",
    "extreme_cold": "Freezing conditions are forecast around your slot. Your provider may need to move the visit for the technician's safety.",
}


async def slot_advisory(
    db, *, place: str | None, slot_at: dt.datetime | None, now: dt.datetime | None = None,
) -> dict | None:
    """What to tell the customer about this slot, or None.

    None in every case where there is nothing honest to say: no weather source, no
    reading, a slot too far out to forecast usefully, a slot already past, or
    perfectly ordinary weather. Silence is the correct output for "we do not know" --
    a "conditions look fine" line backed by no data is the one thing this must not
    produce.
    """
    if not within_advisory_horizon(slot_at, now):
        return None

    from app.engines.weather.service import WeatherService
    service = WeatherService(db)
    if not service.configured:
        return None

    reading = await service.at(place, slot_at)
    verdict = assess_risk(reading)
    level = verdict["level"]
    if level == RISK_NONE:
        return None

    reason = verdict["reason"]
    copy = _SEVERE_COPY if level == RISK_SEVERE else _ADVISORY_COPY
    message = copy.get(reason)
    if not message:
        # A risk level with no wording is not something to improvise about.
        return None

    return {
        "level": level,
        "reason": reason,
        "message": message,
        # The reading travels with the advisory so a support agent can see exactly
        # what the customer was told and why.
        "reading": verdict["reading"],
    }


async def weather_reschedule_permitted(
    db, *, place: str | None, slot_at: dt.datetime | None,
) -> dict:
    """Whether "weather" is an available reschedule reason for this slot.

    Returns {"permitted", "level", "reason", "reading", "detail"}.

    Permitted only on a real reading that genuinely shows disruptive conditions.
    Refused, with a stated detail, when there is no weather source, no reading for
    that hour, or the forecast is unremarkable -- in which case the provider
    reschedules for whatever the real reason is, which keeps the reschedule record
    worth reading.
    """
    from app.engines.weather.service import WeatherService
    service = WeatherService(db)

    if not service.configured:
        return {
            "permitted": False, "level": RISK_NONE, "reason": "unknown", "reading": None,
            "detail": "No weather source is configured, so weather cannot be used as a reason.",
        }
    if slot_at is None:
        return {
            "permitted": False, "level": RISK_NONE, "reason": "unknown", "reading": None,
            "detail": "This job has no scheduled slot to check the weather for.",
        }

    reading = await service.at(place, slot_at)
    if reading is None:
        return {
            "permitted": False, "level": RISK_NONE, "reason": "unknown", "reading": None,
            "detail": "No weather reading is available for that slot.",
        }

    verdict = assess_risk(reading)
    level = verdict["level"]
    permitted = level in (RISK_ADVISORY, RISK_SEVERE)
    return {
        "permitted": permitted,
        "level": level,
        "reason": verdict["reason"],
        "reading": verdict["reading"],
        "detail": (
            "Conditions at the scheduled slot support a weather reschedule."
            if permitted else
            "The forecast for that slot does not show disruptive weather."
        ),
    }
