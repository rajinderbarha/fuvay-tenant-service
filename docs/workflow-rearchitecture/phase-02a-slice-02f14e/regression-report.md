# Regression Report — Slice 2F-14E

## Slice-specific executions

- `tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py` (31 tests, new) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` (34) — PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30, unmodified) — PASS.
- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` (21) — PASS.
- `tests/test_phase2f14c_field_ops_notes_media_and_create_job_fk.py` (12) — PASS.
- `tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` (10, `_job`/`_booking`
  fixture helpers updated with `status`/`BS.CONFIRMED` defaults to match this slice's new
  eligibility checks) — PASS.
- `tests/test_job_type_flows.py`, `tests/test_job_type_routing.py`, `tests/test_usage_quota.py`,
  `tests/test_step8_quote_checklist.py`, `tests/test_p0_job_completion_credit_deduction.py` (100,
  unaffected) — PASS.

Combined runs: the full 2F-14-series suite (2F-14/14A/14B/14C/14D/14E) — **138 passed**; the
fuller combined run additionally including job_type/usage_quota/step8/p0 suites — **253 passed**.
All green, 0 failed.

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request or booking"`:
**1656 passed, 6 skipped, 13 failed, 3 errors** (out of collected + deselected others).

## Live-network/live-database exclusions (not counted as passing)

All 13 failures + 3 errors traced to `httpx.ConnectError`, `asyncpg` connection failure, or
`ConnectionRefusedError: [WinError 1225]` — the identical exclusion class documented in every
prior 2F-14 slice's regression report. None touch any file changed this slice.

## Fixture updated (regression, not a new defect)

`tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` — `_job()`/`_booking()`
mock helpers updated to default to `JS.QUOTE_APPROVED`/`BS.CONFIRMED` respectively, matching this
slice's new status-eligibility checks (previously these tests didn't need a status at all since
no status check existed).

## Net result

All direct slice/dependency suites passing (0 failures attributable to this slice); 1656 passed
in the broad sweep; the same class of pre-existing live-environment exclusions honestly disclosed
and not counted as passing.
