"""MODULE-L5-33 — staff-app mobile EarningsScreen called endpoints that don't
exist and modeled a payout ledger the backend never implemented.

Investigation (part of the MODULE-L5-00-004 gap-register item, "staff_app_mobile
least-certified surface") found mobile/staff-app/src/lib/api.ts's earningsApi
called /v1/staff/{id}/earnings/summary and /v1/staff/{id}/earnings -- neither
exists; every call 404'd. The screen also modeled "total earned / pending
payout / commission deductions" -- a gig-worker payout ledger concept that
has no backend counterpart: ServiceOS charges the TENANT commission per job,
not the technician (FieldOpsService.get_staff_earnings documents itself as
"not a payout ledger; a tenant runs its own payroll, this just shows job
value handled").

Fix: rewired to the one real endpoint (GET /v1/jobs/staff/{staff_id}/earnings,
requires tenant_id query param) and rewrote EarningsScreen to show only the
real fields the backend actually returns.
"""
from __future__ import annotations

from pathlib import Path

API_TS = Path("mobile/staff-app/src/lib/api.ts")
SCREEN_TSX = Path("mobile/staff-app/src/screens/EarningsScreen.tsx")


def test_earnings_api_targets_the_real_endpoint():
    src = API_TS.read_text(encoding="utf-8")
    assert "/v1/jobs/staff/" in src
    assert "/staff/${id}/earnings/summary" not in src
    # the paginated commission-list endpoint never existed; must not be called
    assert "commissions:" not in src.split("export const earningsApi")[1].split("};")[0]


def test_earnings_summary_passes_tenant_id():
    src = API_TS.read_text(encoding="utf-8")
    block = src.split("export const earningsApi")[1]
    assert "tenant_id=" in block
    assert "getTenantId" in block


def test_earnings_screen_no_longer_renders_fictional_payout_fields():
    src = SCREEN_TSX.read_text(encoding="utf-8")
    for fictional_field in ("total_earned", "pending_payout", "commissions.data"):
        assert fictional_field not in src, f"{fictional_field} is not a real backend field"
    for real_field in ("job_value_total", "jobs_completed_total", "job_value_this_month"):
        assert real_field in src
