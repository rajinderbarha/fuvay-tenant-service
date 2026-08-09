"""Weather constants: thresholds, cache policy, and the risk vocabulary.

Every number here is a judgement call, so each one says what it is for. They are
in one module so they can be argued with and tuned without hunting through the
engine.
"""
from __future__ import annotations

# ── Cache ────────────────────────────────────────────────────────────────────
# A slot advisory does not need minute-by-minute data, and a free API tier is a
# real constraint: at 30 minutes, one PIN code costs at most 48 calls a day.
CACHE_TTL_MINUTES = 30

# ── Risk thresholds ──────────────────────────────────────────────────────────
# Rain in mm over the hour of the visit. India's monsoon makes light rain
# unremarkable -- a technician works through it -- so only genuinely disruptive
# rain raises anything.
RAIN_MM_ADVISORY = 7.5      # heavy enough that travel slips
RAIN_MM_SEVERE = 20.0       # IMD "heavy rainfall" territory: safety, not lateness

# Wind in km/h.
WIND_KMH_ADVISORY = 40.0
WIND_KMH_SEVERE = 60.0

# Temperature in Celsius. Rooftop and outdoor-unit work in extreme heat is a
# genuine safety limit, not a comfort preference.
HEAT_C_SEVERE = 43.0
COLD_C_SEVERE = 2.0

# ── Risk levels ──────────────────────────────────────────────────────────────
RISK_NONE = "none"
RISK_ADVISORY = "advisory"   # disruptive: a weather reschedule is defensible
RISK_SEVERE = "severe"       # unsafe: rescheduling is the right call
RISK_LEVELS = (RISK_NONE, RISK_ADVISORY, RISK_SEVERE)

ERR_WEATHER_UNAVAILABLE = "WEATHER_UNAVAILABLE"
