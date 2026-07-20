# Regression Report — Slice 2F-14F

## Slice-specific executions

- `tests/test_phase2f14f_field_ops_manual_customer_authority.py` (10 tests, new) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` (34) — PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30, unmodified) — PASS.
- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` (21) — PASS.
- `tests/test_phase2f14c_field_ops_notes_media_and_create_job_fk.py` (12) — PASS.
- `tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` (10, `customer_user`
  mock fixtures updated with `is_active=True, deleted_at=None`) — PASS.
- `tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py` (31) — PASS.
- `tests/test_job_type_flows.py` (14, 1 `customer_result` mock fixture updated with
  `is_active=True, deleted_at=None`) — PASS.
- `tests/test_job_type_routing.py`, `tests/test_usage_quota.py` (23, unaffected) — PASS.

Combined: **185 passed, 0 failed** (2F-14-series + job_type/usage_quota suites).

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request or booking"`:
**1681 passed, 7 skipped, 0 failed** this run (a live app server/database happened to be
reachable during this run, unlike prior slices' sweeps which showed ~10-15 pre-existing
live-network-dependent failures from the same test files — none of those files were touched by
this slice, so their pass/fail status is environment-dependent, not attributable to this slice's
changes either way).

## Fixtures updated (regression, not new defects)

- `tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` — 2 `customer_user` mock
  objects updated to explicitly set `is_active=True, deleted_at=None` (previously bare
  `MagicMock(role="customer")`, whose auto-generated `deleted_at` attribute was a truthy Mock
  object, incorrectly tripping this slice's new deleted-customer check).
- `tests/test_job_type_flows.py` — same fix, 1 occurrence.

## Net result

185 passed across direct slice/dependency suites (0 failures attributable to this slice); 1681
passed in the broad sweep with 0 failures this run (environment-dependent live-network tests
happened to succeed).
