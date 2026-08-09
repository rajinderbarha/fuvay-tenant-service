"""Weather in scheduling decisions.

`weather_reschedule_permitted` is what the PROVIDER is allowed to do. Rescheduling
for weather exists for technician safety, and it is gated on a REAL reading: with no
weather source, or no reading for that slot, "weather" is not an available reason. The
provider can still reschedule -- they simply have to give the real reason rather than
attributing it to conditions the system cannot see.

This is the ONLY caller of the weather API in the platform, by product decision: it
runs when a provider picks weather as the reason, and nothing a customer opens spends
a lookup. A customer-facing slot advisory lived here once and was removed with the
Home widget for the same reason.

That gate is the whole point. A reschedule reason that cannot be checked is a
reason that gets used for everything, and the record of why visits move stops
meaning anything.
"""
from __future__ import annotations

import datetime as dt

from app.engines.weather.constants import RISK_ADVISORY, RISK_NONE, RISK_SEVERE
from app.engines.weather.service import assess_risk

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
