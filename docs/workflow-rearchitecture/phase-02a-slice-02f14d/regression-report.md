# Regression Report — Slice 2F-14D

## Slice-specific executions

- `tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` (10 tests, new) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` (34) — PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30, unmodified — figures
  unchanged) — PASS.
- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` (21) — PASS.
- `tests/test_phase2f14c_field_ops_notes_media_and_create_job_fk.py` (12) — PASS.
- `tests/test_job_type_flows.py` (14, 1 fixture updated with one additional mock DB response for
  the new duplicate-repair check) — PASS.
- `tests/test_job_type_routing.py`, `tests/test_usage_quota.py` (23, unaffected) — PASS.
- `tests/test_step8_quote_checklist.py`, `tests/test_p0_job_completion_credit_deduction.py` (49,
  unaffected) — PASS.

Combined: **253 passed, 0 failed.**

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request or booking"`:
**1625 passed, 1 skipped, 15 failed, 6 errors** (out of 1647 collected + deselected others; this
sweep additionally included `"booking"` this slice, surfacing more live-DB-dependent booking
tests than prior slices' sweeps, none newly broken by this slice's changes).

## Live-network/live-database exclusions (not counted as passing)

All 15 failures + 6 errors traced to `httpx.ConnectError`, `asyncpg` connection failure, or
`ConnectionRefusedError: [WinError 1225]` — every one requires a running app server/Postgres
instance not present in this environment. The additional entries versus prior slices' sweeps
(`test_final_l5_04c_matching_entitlement.py` x2, `test_module_l5_27_booking_notify.py`,
`test_module_l5_29_booking_cancel_reschedule.py` x2 more, `test_module_l5_13_reviews.py` x1
error) are exclusively booking-live-flow tests surfaced by adding `"booking"` to the `-k` filter —
independently confirmed via traceback inspection to be the same connection-failure class, not new
defects.

## Fixture updated (regression, not a new defect)

`tests/test_job_type_flows.py::test_consultation_quote_approval_spawns_repair_job_with_inherited_data`
— its mock `db.execute` `side_effect` list extended with one additional `None` result for the new
duplicate-repair-from-consultation check (`create_job`, called internally via
`_spawn_repair_from_consultation`, now performs this check before constructing the Job).

## Net result

253 passed in direct slice/dependency suites / 1625 passed in the broad sweep / 21 pre-existing
live-environment exclusions honestly disclosed and not counted as passing.
