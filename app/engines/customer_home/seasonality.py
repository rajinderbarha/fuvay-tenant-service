"""Season-aware ordering for the customer Home screen.

Why this exists: the catalogue's own `display_order` is fixed, so Air
Conditioning led the screen in December and a water heater would have led it in
May. What a household needs is seasonal, and in India strongly so.

Two deliberate limits on what this does:

* It ONLY REORDERS. Nothing is hidden, nothing is added, and no service is
  presented as unavailable out of season -- an AC repair in January is a real
  need for whoever has it, it simply should not be the first thing offered.
* It never invents a service. Ordering can only work on what an admin has
  actually authored: if no water-heater category or problem exists in the
  catalogue, winter has nothing to promote and the order stays the catalogue's
  own.

Season boundaries follow the practical Indian calendar rather than the
astronomical one, and are stated by month so they can be read and argued with:

    Dec-Feb  winter    water heaters/geysers, room heating
    Mar-Jun  summer    air conditioning, coolers, fans, refrigeration
    Jul-Sep  monsoon   leaks and seepage, drainage, damp, pests, electrical safety
    Oct-Nov  festive   deep cleaning, painting, pest control before the festivals

Matching is by KEYWORD against the admin-authored name, which is a heuristic and
is documented as one. It lives in this single module so the vocabulary is
reviewable and tunable in one place, and an unmatched service is treated as
NEUTRAL -- never demoted on a guess.
"""
from __future__ import annotations

import datetime as dt
import re

SEASON_WINTER = "winter"
SEASON_SUMMER = "summer"
SEASON_MONSOON = "monsoon"
SEASON_FESTIVE = "festive"

SEASONS = (SEASON_WINTER, SEASON_SUMMER, SEASON_MONSOON, SEASON_FESTIVE)

# ── Region ───────────────────────────────────────────────────────────────────
# India is not one climate, and the calendar alone gets this badly wrong: January
# in Ludhiana genuinely needs a geyser, January in Chennai does not, and putting
# water heating first for a Chennai customer is the same mistake as leading with
# AC in a Punjab December -- just in the other direction.
REGION_NORTH = "north"      # Punjab, Delhi, UP, Rajasthan, Himachal... real winter
REGION_SOUTH = "south"      # TN, Kerala, Karnataka, coastal AP... barely a winter
REGION_DEFAULT = REGION_NORTH

# Matched against the customer's city/state as stored on their address. States are
# listed because that is what `tenants.state` and address records carry; a few
# major cities are included because a customer's city is often all we have.
_SOUTH_MARKERS = (
    "tamil nadu", "kerala", "karnataka", "andhra", "telangana", "puducherry",
    "goa", "chennai", "bengaluru", "bangalore", "kochi", "cochin", "hyderabad",
    "coimbatore", "madurai", "mysore", "mangalore", "trivandrum",
    "thiruvananthapuram", "vijayawada", "visakhapatnam", "mumbai", "pune",
)


def resolve_region(city: str | None = None, state: str | None = None) -> str:
    """Which climate the customer is in.

    Defaults to NORTH when unknown: the north is where the seasonal swing is
    strongest, so it is the case where getting the order right matters most, and
    an unknown location is more likely to be a northern one on this platform's
    current footprint (Punjab).
    """
    text = " ".join(part for part in (city, state) if part).strip().lower()
    if not text:
        return REGION_DEFAULT
    return REGION_SOUTH if any(marker in text for marker in _SOUTH_MARKERS) else REGION_DEFAULT

# Month (1-12) -> season. Explicit rather than computed from ranges so the
# boundaries are impossible to misread.
_MONTH_SEASON = {
    1: SEASON_WINTER, 2: SEASON_WINTER,
    3: SEASON_SUMMER, 4: SEASON_SUMMER, 5: SEASON_SUMMER, 6: SEASON_SUMMER,
    7: SEASON_MONSOON, 8: SEASON_MONSOON, 9: SEASON_MONSOON,
    10: SEASON_FESTIVE, 11: SEASON_FESTIVE,
    12: SEASON_WINTER,
}

# The south's winter is mild enough that water heating never leads, and its hot
# season runs longer. Only the months that genuinely differ are overridden.
_SOUTH_MONTH_SEASON = {
    **{m: SEASON_SUMMER for m in (1, 2, 3, 4, 5)},   # no heating season worth leading with
    6: SEASON_MONSOON, 7: SEASON_MONSOON, 8: SEASON_MONSOON, 9: SEASON_MONSOON,
    10: SEASON_MONSOON,   # the north-east monsoon is the south's wettest stretch
    11: SEASON_FESTIVE, 12: SEASON_FESTIVE,
}

SEASON_LABELS = {
    SEASON_WINTER: "Winter picks",
    SEASON_SUMMER: "Summer picks",
    SEASON_MONSOON: "Monsoon picks",
    SEASON_FESTIVE: "Festive-season picks",
}

# What each season genuinely brings forward. Word-boundary matched, so "fan" does
# not fire on "infant" and "ac" does not fire on "back".
_IN_SEASON = {
    SEASON_WINTER: (
        r"geyser", r"water\s*heater", r"\bheater\b", r"heating", r"immersion\s*rod",
        r"\bboiler\b", r"room\s*heater", r"blanket",
    ),
    SEASON_SUMMER: (
        r"\bac\b", r"air\s*condition", r"cooling", r"\bcooler\b", r"\bfan\b",
        r"refrigerat", r"\bfridge\b", r"gas\s*refill",
    ),
    SEASON_MONSOON: (
        r"leak", r"seepage", r"damp", r"waterproof", r"drain", r"blockage", r"blocked",
        r"overflow", r"pest", r"termite", r"mosquito", r"short\s*circuit", r"sparking",
        r"\bmcb\b", r"wiring", r"water\s*tank",
        # CATEGORY names are generic ("Plumbing", "Electrical") and match none of
        # the fault words above, so without these the monsoon ordering only
        # reached the problem list and left the SERVICE GRID untouched -- which is
        # where a customer looks first.
        r"plumb", r"electric",
    ),
    SEASON_FESTIVE: (
        r"deep\s*clean", r"cleaning", r"paint", r"stain", r"sofa", r"move\s*in",
        r"move\s*out", r"pest",
    ),
}

# What each season pushes DOWN. Only the strong, unambiguous opposites: a water
# heater in June and an air conditioner in January. Everything else stays neutral,
# because guessing wrong here removes a service from view for a whole season.
_OUT_OF_SEASON = {
    SEASON_WINTER: (r"\bac\b", r"air\s*condition", r"\bcooler\b"),
    SEASON_SUMMER: (r"geyser", r"water\s*heater", r"room\s*heater", r"\bboiler\b"),
    SEASON_MONSOON: (),
    SEASON_FESTIVE: (),
}

# Rank values. Sorted ascending, so lower shows first.
RANK_IN_SEASON = 0
RANK_NEUTRAL = 1
RANK_OUT_OF_SEASON = 2

# Live-weather thresholds, in Celsius. Deliberately far apart: only a genuinely
# cold or genuinely hot day overrides the calendar, so ordinary variation does not
# reshuffle the screen day to day.
COLD_THRESHOLD_C = 18.0
HOT_THRESHOLD_C = 32.0

# India-wide. The platform is single-country today; when that changes this becomes
# a per-tenant timezone read rather than a constant.
_IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def current_season(
    now: dt.datetime | None = None,
    *,
    region: str = REGION_DEFAULT,
    temperature_c: float | None = None,
) -> str:
    """The season for this customer, by region and -- when known -- real weather.

    Evaluated in IST rather than the server's timezone: a server in UTC is already
    the previous day for five and a half hours every night, which would flip the
    season a day early on 1 March and 1 December.

    `temperature_c` is a live reading if the deployment has a weather source
    configured. It OVERRIDES the calendar at the two extremes only, because those
    are the cases where the calendar is most obviously wrong to a customer: an
    unseasonal cold snap in a northern March, or a hot spell in a mild November.
    The middle of the range is left to the calendar, which knows about monsoon and
    the festive season -- things temperature cannot tell you.

    With no reading it degrades to climatology, which is a real answer rather than
    a guess: no deployment is ever blocked on a weather integration.
    """
    moment = (now or dt.datetime.now(dt.timezone.utc)).astimezone(_IST)
    calendar = (
        _SOUTH_MONTH_SEASON[moment.month] if region == REGION_SOUTH
        else _MONTH_SEASON[moment.month]
    )

    if temperature_c is None:
        return calendar
    if temperature_c <= COLD_THRESHOLD_C:
        # Cold enough that water heating is what a household actually needs today,
        # whatever the month says.
        return SEASON_WINTER
    if temperature_c >= HOT_THRESHOLD_C:
        return SEASON_SUMMER
    return calendar


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def season_rank(name: str | None, season: str) -> int:
    """Where a service or problem belongs this season: 0 first, 1 neutral, 2 last.

    Unrecognised wording is NEUTRAL, never demoted -- the keyword list cannot
    possibly cover every service an admin will author, and a wrong demotion buries
    a real service for months.
    """
    text = (name or "").strip().lower()
    if not text:
        return RANK_NEUTRAL
    if _matches(_IN_SEASON.get(season, ()), text):
        return RANK_IN_SEASON
    if _matches(_OUT_OF_SEASON.get(season, ()), text):
        return RANK_OUT_OF_SEASON
    return RANK_NEUTRAL


def sort_by_season(items: list[dict], *, name_key: str, season: str) -> list[dict]:
    """Reorders in place-safe fashion, keeping the catalogue's order within a rank.

    A STABLE sort, deliberately: inside one rank the admin's own `display_order`
    still decides, so this adds a seasonal tier on top of the catalogue rather
    than replacing its ordering with a keyword's opinion.
    """
    return sorted(items, key=lambda item: season_rank(item.get(name_key), season))
