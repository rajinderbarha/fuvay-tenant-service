from datetime import date
from pathlib import Path

from app.engines.provider_portal.holiday_calendar import (
    build_india_holiday_calendar,
    india_subdivision_code,
)


def test_punjab_state_name_resolves_to_iso_subdivision():
    assert india_subdivision_code("Punjab") == "PB"
    assert india_subdivision_code("PB") == "PB"


def test_punjab_calendar_includes_national_and_regional_holidays():
    calendar = build_india_holiday_calendar(
        date(2026, 10, 1), date(2026, 12, 31), states=["Punjab"],
    )
    by_date = {item["date"]: item for item in calendar["holidays"]}

    assert calendar["subdivisions"] == ["PB"]
    assert by_date["2026-10-02"]["name"] == "Mahatma Gandhi's Jayanti"
    assert by_date["2026-11-10"]["name"] == "Vishwakarma Day"
    assert by_date["2026-11-10"]["scope"] == "regional"


def test_holiday_calendar_respects_requested_range():
    calendar = build_india_holiday_calendar(
        date(2026, 10, 2), date(2026, 10, 2), states=["Punjab"],
    )
    assert [item["date"] for item in calendar["holidays"]] == ["2026-10-02"]


def test_calendar_route_precedes_dynamic_availability_route():
    source = (Path(__file__).parents[1] / "app/engines/provider_portal/router.py").read_text(encoding="utf-8")
    assert source.index('@router.get("/availability/holiday-calendar")') < source.index(
        '@router.get("/availability/{rule_id}")'
    )
