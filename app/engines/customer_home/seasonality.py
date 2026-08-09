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

# Month (1-12) -> season. Explicit rather than computed from ranges so the
# boundaries are impossible to misread.
_MONTH_SEASON = {
    1: SEASON_WINTER, 2: SEASON_WINTER,
    3: SEASON_SUMMER, 4: SEASON_SUMMER, 5: SEASON_SUMMER, 6: SEASON_SUMMER,
    7: SEASON_MONSOON, 8: SEASON_MONSOON, 9: SEASON_MONSOON,
    10: SEASON_FESTIVE, 11: SEASON_FESTIVE,
    12: SEASON_WINTER,
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

# India-wide. The platform is single-country today; when that changes this becomes
# a per-tenant timezone read rather than a constant.
_IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def current_season(now: dt.datetime | None = None) -> str:
    """The season in India right now.

    Evaluated in IST rather than the server's timezone: a server in UTC is
    already the previous day for five and a half hours every night, which would
    flip the season a day early on 1 March and 1 December.
    """
    moment = (now or dt.datetime.now(dt.timezone.utc)).astimezone(_IST)
    return _MONTH_SEASON[moment.month]


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
