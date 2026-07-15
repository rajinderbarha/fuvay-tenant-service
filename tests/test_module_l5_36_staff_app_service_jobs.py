"""MODULE-L5-36 — staff-app mobile's entire job surface was pointed at
field_ops, a fully-built but practically dead engine (0 rows platform-wide).

Investigation (following MODULE-L5-35) confirmed: `app/engines/booking/
service.py:convert_to_job` is the ONLY code path anywhere that ever inserts a
field_ops `Job` row, gated behind an explicit tenant_owner action nobody
invokes in production. Every real job is a `ServiceJob` row (table
`service_jobs`), operated on by `home_service_assignment` (assignment phase:
list/detail/accept/reject) and `execution` (post-accept work lifecycle:
on-the-way -> reached-site -> inspection -> service -> complete), both
already live and working at `/v1/staff/service-jobs/*`.

Rewired mobile/staff-app's entire job surface (api.ts's jobsApi, JobsListScreen,
JobDetailScreen, HomeScreen, transitions.ts) to these real endpoints. Verified
live end-to-end: seeded a real service_job + assignment, drove list -> detail
-> accept -> on-the-way -> reached-site -> start-inspection ->
complete-inspection -> start-service -> complete, confirming completion_data
and the usage-credit deduction fire correctly. Also verified reject and the
{success:false, error} wrapper shape home_service_assignment's staff_router
uses for controlled errors (e.g. rejecting an already-rejected job).
"""
from __future__ import annotations

from pathlib import Path

API_TS = Path("mobile/staff-app/src/lib/api.ts")
LIST_SCREEN = Path("mobile/staff-app/src/screens/JobsListScreen.tsx")
DETAIL_SCREEN = Path("mobile/staff-app/src/screens/JobDetailScreen.tsx")
HOME_SCREEN = Path("mobile/staff-app/src/screens/HomeScreen.tsx")
TRANSITIONS = Path("mobile/staff-app/src/lib/transitions.ts")


def _live_lines(text: str) -> str:
    return "\n".join(l for l in text.splitlines()
                      if not l.strip().startswith("//") and not l.strip().startswith("*"))


def test_jobs_api_targets_the_real_service_jobs_endpoints():
    src = API_TS.read_text(encoding="utf-8")
    block = _live_lines(src.split("export const jobsApi")[1].split("\nexport const staffApi")[0])
    assert "/v1/staff/service-jobs" in block
    assert "/v1/jobs/" not in block  # no leftover field_ops path references in jobsApi itself


def test_no_screen_references_fictional_field_ops_fields():
    for path in (LIST_SCREEN, DETAIL_SCREEN, HOME_SCREEN):
        live = [l for l in path.read_text(encoding="utf-8").splitlines()
                if not l.strip().startswith("//") and not l.strip().startswith("*")]
        src = "\n".join(live)
        for fictional in ("service_type", "customer_phone", "customer_address",
                           "job_value", "sla_minutes", "minutes_in_status", "closing_notes"):
            assert fictional not in src, f"{path}: {fictional} does not exist on the real ServiceJob"


def test_transitions_use_the_real_execution_status_set():
    live = _live_lines(TRANSITIONS.read_text(encoding="utf-8"))
    for real_status in ("on_the_way", "reached_site", "inspection_started",
                         "inspection_done", "service_started", "work_done"):
        assert real_status in live
    for dead_status in ("en_route", "arrived", "quality_check", "parts_sourced"):
        assert dead_status not in live


def test_complete_action_requires_work_summary_and_amount():
    src = API_TS.read_text(encoding="utf-8")
    block = src.split("complete: (id:string")[1].split("timeline:")[0]
    assert "work_summary" in block
    assert "collected_amount" in block
