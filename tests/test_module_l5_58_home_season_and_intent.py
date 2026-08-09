"""MODULE-L5-58 — seasonal ordering and intent grouping for the customer Home.

Both are heuristics over admin-authored names, so what matters is that they only
ever REORDER or GROUP: nothing is hidden, nothing invented, and an unrecognised
service is left alone rather than demoted or mis-grouped on a guess.
"""
from __future__ import annotations

import datetime as dt

from app.engines.customer_home.intent import (
    INTENT_CONSULT, INTENT_REPAIR, classify_intent,
)
from app.engines.customer_home.seasonality import (
    RANK_IN_SEASON, RANK_NEUTRAL, RANK_OUT_OF_SEASON, REGION_NORTH, REGION_SOUTH,
    SEASON_FESTIVE, SEASON_LABELS, SEASON_MONSOON, SEASON_SUMMER, SEASON_WINTER,
    SEASONS, current_season, resolve_region, season_rank, sort_by_season,
)

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _at(month: int, day: int = 15, hour: int = 12) -> dt.datetime:
    return dt.datetime(2026, month, day, hour, tzinfo=IST)


# ── Which season it is ───────────────────────────────────────────────────────

def test_indian_calendar_months_map_to_the_documented_seasons():
    assert current_season(_at(1)) == SEASON_WINTER
    assert current_season(_at(4)) == SEASON_SUMMER
    assert current_season(_at(8)) == SEASON_MONSOON
    assert current_season(_at(11)) == SEASON_FESTIVE
    assert current_season(_at(12)) == SEASON_WINTER


def test_every_month_has_a_season():
    for month in range(1, 13):
        assert current_season(_at(month)) in SEASONS


def test_season_is_read_in_ist_not_the_server_timezone():
    """A UTC server is already the previous day for five and a half hours every
    night, which would flip the season a day early on 1 March and 1 December."""
    # 2026-03-01 02:00 IST is still 2026-02-28 in UTC.
    moment = dt.datetime(2026, 3, 1, 2, 0, tzinfo=IST)
    assert current_season(moment) == SEASON_SUMMER
    assert current_season(moment.astimezone(dt.timezone.utc)) == SEASON_SUMMER


def test_every_season_has_customer_facing_wording():
    for season in SEASONS:
        assert SEASON_LABELS[season]


# ── What each season promotes ────────────────────────────────────────────────

def test_water_heating_leads_in_winter_and_air_conditioning_does_not():
    # The whole point of the feature: December should not open with an AC advert.
    assert season_rank("Geyser Not Heating", SEASON_WINTER) == RANK_IN_SEASON
    assert season_rank("Water Heater Service", SEASON_WINTER) == RANK_IN_SEASON
    assert season_rank("Air Conditioning", SEASON_WINTER) == RANK_OUT_OF_SEASON
    assert season_rank("AC Not Cooling", SEASON_WINTER) == RANK_OUT_OF_SEASON


def test_air_conditioning_leads_in_summer_and_water_heating_does_not():
    assert season_rank("Air Conditioning", SEASON_SUMMER) == RANK_IN_SEASON
    assert season_rank("AC Not Cooling", SEASON_SUMMER) == RANK_IN_SEASON
    assert season_rank("Geyser Repair", SEASON_SUMMER) == RANK_OUT_OF_SEASON


def test_monsoon_leads_with_water_ingress_and_electrical_safety():
    for name in ("Pipe Leakage", "Water Leakage", "Drain Blocked", "Short Circuit",
                 "Pest Infestation", "Water Tank Overflow"):
        assert season_rank(name, SEASON_MONSOON) == RANK_IN_SEASON


def test_festive_season_leads_with_cleaning_and_painting():
    for name in ("Deep Cleaning Needed", "Wall Painting Needed", "Stain Removal"):
        assert season_rank(name, SEASON_FESTIVE) == RANK_IN_SEASON


def test_nothing_is_demoted_without_a_strong_opposite():
    # Monsoon and the festive season demote NOTHING: burying a service for a
    # quarter on a keyword's opinion is worse than a slightly stale order.
    for season in (SEASON_MONSOON, SEASON_FESTIVE):
        assert season_rank("Air Conditioning", season) != RANK_OUT_OF_SEASON
        assert season_rank("Geyser Repair", season) != RANK_OUT_OF_SEASON


def test_unrecognised_wording_is_neutral_never_demoted():
    for name in ("Carpentry", "Sofa Shampoo", "Chimney Service", "", None):
        assert season_rank(name, SEASON_WINTER) == RANK_NEUTRAL


def test_word_boundaries_stop_false_matches():
    # "ac" must not fire inside "back", nor "fan" inside "infant".
    assert season_rank("Back Wall Repair", SEASON_WINTER) == RANK_NEUTRAL
    assert season_rank("Infant Room Setup", SEASON_SUMMER) == RANK_NEUTRAL


# ── The sort itself ──────────────────────────────────────────────────────────

def test_sort_only_reorders_and_keeps_everything():
    items = [{"name": n} for n in ("Air Conditioning", "Plumbing", "Geyser Service")]
    sorted_items = sort_by_season(items, name_key="name", season=SEASON_WINTER)
    assert len(sorted_items) == len(items)
    assert {i["name"] for i in sorted_items} == {i["name"] for i in items}
    assert sorted_items[0]["name"] == "Geyser Service"
    assert sorted_items[-1]["name"] == "Air Conditioning"


def test_sort_is_stable_so_the_catalogue_still_decides_within_a_tier():
    """Two neutral services keep the admin's own display_order between them."""
    items = [{"name": "Painting"}, {"name": "Carpentry"}, {"name": "Pest Control"}]
    sorted_items = sort_by_season(items, name_key="name", season=SEASON_WINTER)
    assert [i["name"] for i in sorted_items] == ["Painting", "Carpentry", "Pest Control"]


def test_sorting_an_empty_list_is_not_an_error():
    assert sort_by_season([], name_key="name", season=SEASON_SUMMER) == []


# ── Intent grouping ──────────────────────────────────────────────────────────

def test_a_fault_is_a_repair():
    for name in ("AC Not Cooling", "Pipe Leaking", "MCB Trip", "No Power",
                 "Socket Sparking", "Bad Smell", "Not Draining", "Noise Issue"):
        assert classify_intent(name) == INTENT_REPAIR


def test_scoping_and_quoting_work_is_a_consult():
    for name in ("New AC Installation", "Site Visit Request", "Buy Inquiry",
                 "Wall Painting Needed", "Deep Cleaning Needed"):
        assert classify_intent(name) == INTENT_CONSULT


def test_a_fault_wins_when_both_readings_are_possible():
    # "Low Cooling / Gas Refill Needed" ends in "Needed", which the consult list
    # would otherwise claim -- but a gas refill is plainly a fix.
    assert classify_intent("Low Cooling / Gas Refill Needed") == INTENT_REPAIR


def test_unrecognised_wording_falls_back_to_repair_never_to_nothing():
    """Every problem belongs to exactly one intent section.

    `master_issue_types` is a catalogue of FAULTS by its own definition, so a fault
    is the right prior for wording nobody's keywords recognise. Leaving these null
    meant a real, bookable problem appeared in NEITHER section -- worse than being
    one row down in the more likely of the two.
    """
    for name in ("Annual Maintenance", "Chimney", "Cooling Low", "", None):
        assert classify_intent(name) == INTENT_REPAIR


def test_no_problem_is_ever_unclassified():
    for name in ("AC Not Cooling", "New AC Installation", "", None, "??"):
        assert classify_intent(name) in (INTENT_REPAIR, INTENT_CONSULT)


# ── Region ───────────────────────────────────────────────────────────────────

def test_northern_january_is_winter_and_southern_january_is_not():
    """The calendar alone gets one of these wrong every year: January in Ludhiana
    genuinely needs a geyser; January in Chennai does not."""
    north = resolve_region("Ludhiana", "Punjab")
    south = resolve_region("Chennai", "Tamil Nadu")
    assert current_season(_at(1), region=north) == SEASON_WINTER
    assert current_season(_at(1), region=south) != SEASON_WINTER


def test_region_defaults_to_north_when_the_address_says_nothing():
    # The north has the strongest swing, so it is where a wrong order costs most.
    assert resolve_region(None, None) == REGION_NORTH
    assert resolve_region("", "") == REGION_NORTH


def test_region_is_read_from_either_city_or_state():
    assert resolve_region("Kochi", None) == REGION_SOUTH
    assert resolve_region(None, "Kerala") == REGION_SOUTH
    assert resolve_region("Amritsar", "Punjab") == REGION_NORTH


# ── Live weather ─────────────────────────────────────────────────────────────

def test_a_real_cold_snap_beats_the_calendar():
    # An unseasonably cold northern March: what a household needs today is hot
    # water, whatever the month says.
    assert current_season(_at(3), region=REGION_NORTH, temperature_c=12) == SEASON_WINTER


def test_a_real_hot_spell_beats_the_calendar():
    assert current_season(_at(11), region=REGION_NORTH, temperature_c=34) == SEASON_SUMMER


def test_ordinary_temperatures_leave_the_calendar_alone():
    # Only the extremes override, so day-to-day variation does not reshuffle the
    # screen -- and the calendar keeps the things temperature cannot tell you,
    # like the monsoon and the festive season.
    assert current_season(_at(8), region=REGION_NORTH, temperature_c=27) == SEASON_MONSOON
    assert current_season(_at(10), region=REGION_NORTH, temperature_c=25) == SEASON_FESTIVE


def test_no_weather_reading_degrades_to_climatology_rather_than_guessing():
    # No deployment is blocked on a weather integration.
    assert current_season(_at(1), region=REGION_NORTH, temperature_c=None) == SEASON_WINTER


def test_generic_category_names_are_seasonal_too():
    """The service GRID is what a customer looks at first, and its rows are named
    "Plumbing" / "Electrical" -- which match none of the monsoon FAULT words, so
    without category-level wording the seasonal order reached only the problem
    list."""
    assert season_rank("Plumbing", SEASON_MONSOON) == RANK_IN_SEASON
    assert season_rank("Electrical", SEASON_MONSOON) == RANK_IN_SEASON
    assert season_rank("Pest Control", SEASON_MONSOON) == RANK_IN_SEASON
    assert season_rank("Home Cleaning", SEASON_FESTIVE) == RANK_IN_SEASON
    assert season_rank("Painting", SEASON_FESTIVE) == RANK_IN_SEASON
    assert season_rank("Air Conditioning", SEASON_SUMMER) == RANK_IN_SEASON
    # And in monsoon, Air Conditioning is merely neutral -- so it stops leading
    # the grid without being buried.
    assert season_rank("Air Conditioning", SEASON_MONSOON) == RANK_NEUTRAL
