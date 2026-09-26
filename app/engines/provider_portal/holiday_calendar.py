"""Provider-facing public holiday calendar.

The calendar is generated locally from the pinned ``python-holidays`` data
set, so opening Coverage & Hours never depends on a third-party API being up.
Provider coverage supplies the Indian state/subdivision; the UI then offers
real holiday names and dates instead of asking an operator to type them.
"""
from __future__ import annotations

from datetime import date

import holidays


_INDIA_STATE_CODES = {
    "andaman and nicobar islands": "AN", "andhra pradesh": "AP",
    "arunachal pradesh": "AR", "assam": "AS", "bihar": "BR",
    "chandigarh": "CH", "chhattisgarh": "CG", "dadra and nagar haveli": "DH",
    "daman and diu": "DD", "delhi": "DL", "goa": "GA", "gujarat": "GJ",
    "haryana": "HR", "himachal pradesh": "HP", "jammu and kashmir": "JK",
    "jharkhand": "JH", "karnataka": "KA", "kerala": "KL", "ladakh": "LA",
    "lakshadweep": "LD", "madhya pradesh": "MP", "maharashtra": "MH",
    "manipur": "MN", "meghalaya": "ML", "mizoram": "MZ", "nagaland": "NL",
    "odisha": "OR", "orissa": "OR", "puducherry": "PY", "pondicherry": "PY",
    "punjab": "PB", "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN",
    "telangana": "TS", "tripura": "TR", "uttar pradesh": "UP",
    "uttarakhand": "UK", "uttaranchal": "UK", "west bengal": "WB",
}


def india_subdivision_code(state: str | None) -> str | None:
    normalized = " ".join(str(state or "").strip().lower().replace("&", "and").split())
    if not normalized:
        return None
    if len(normalized) == 2 and normalized.upper() in holidays.IN.subdivisions:
        return normalized.upper()
    return _INDIA_STATE_CODES.get(normalized)


def build_india_holiday_calendar(
    from_date: date,
    to_date: date,
    *,
    states: list[str] | tuple[str, ...] = (),
) -> dict:
    """Return national + covered-state holidays within an inclusive range."""
    years = list(range(from_date.year, to_date.year + 1))
    national = holidays.country_holidays("IN", years=years)
    subdivisions = sorted({code for state in states if (code := india_subdivision_code(state))})

    combined: dict[date, dict] = {}
    for day, name in national.items():
        if from_date <= day <= to_date:
            combined[day] = {
                "date": day.isoformat(), "name": str(name), "scope": "national",
                "subdivisions": [],
            }

    for subdivision in subdivisions:
        regional = holidays.country_holidays("IN", subdiv=subdivision, years=years)
        for day, name in regional.items():
            if not from_date <= day <= to_date:
                continue
            item = combined.setdefault(day, {
                "date": day.isoformat(), "name": str(name), "scope": "regional",
                "subdivisions": [],
            })
            if day not in national:
                item["scope"] = "regional"
                item["name"] = str(name)
            if subdivision not in item["subdivisions"]:
                item["subdivisions"].append(subdivision)

    return {
        "country": "IN",
        "subdivisions": subdivisions,
        "source": "python-holidays",
        "holidays": [combined[day] for day in sorted(combined)],
    }
