"""MODULE-L5-33 — staff-app mobile EarningsScreen called endpoints that don't
exist and modeled a payout ledger the backend never implemented.

Superseded by MODULE-L5-36: the L5-33 fix rewired EarningsScreen to the one
real field_ops endpoint that existed (GET /v1/jobs/staff/{staff_id}/earnings),
but MODULE-L5-36 later confirmed field_ops' `jobs` table has 0 rows
platform-wide -- that "real" endpoint would always report zero for every
job a technician actually does. There is also no job-value/price field
reachable by staff anywhere on the real ServiceJob pipeline (the safe
booking view deliberately excludes pricing from staff visibility). Rewired
again to derive real completed-job counts from the live
/v1/staff/service-jobs list (the same one JobsListScreen uses) and dropped
the fabricated job-value/rating stats rather than show fake zeros.
"""
from __future__ import annotations

from pathlib import Path

API_TS = Path("mobile/staff-app/src/lib/api.ts")
SCREEN_TSX = Path("mobile/staff-app/src/screens/EarningsScreen.tsx")


def test_dead_field_ops_earnings_endpoint_no_longer_called():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/jobs/staff/" not in src
    assert "earningsApi" not in src


def test_app_does_not_present_fabricated_earnings_screen():
    assert not SCREEN_TSX.exists()
