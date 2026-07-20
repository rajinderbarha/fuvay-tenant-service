# Regression Report — Slice 2F-15

## Slice-specific executions

- `tests/test_phase2f15_booking_customer_identity_and_confirmation.py` (9 tests, new) — PASS.
- `tests/test_step4_booking.py` (44 tests, unmodified) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` through
  `tests/test_phase2f14g_field_ops_relationship_provenance.py` (165 tests) — PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30 tests, 1 canonical-figure
  assertion updated to 174/221) — PASS.

Combined: **217 passed, 0 failed** (booking + field_ops 2F-14-series suites, excluding the
broader `-k` sweep below).

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request or booking"`:
**1707 passed, 7 skipped, 0 failed.**

## Runtime verification

- `--verify-module app.engines.field_ops.router` — exit 0 (unaffected).
- `--verify-module app.engines.field_ops.staff_router` — exit 0 (unaffected).
- `--verify-module app.engines.booking.router` — exit 1 (6 routes explicitly out-of-scope,
  documented, not a regression — see coverage-verification-report.md).

## No unexpected fixture updates

Only one pre-existing test file required a fixture update this slice: the canonical coverage
figures in `test_phase2f14a_field_ops_alternate_route_and_coverage.py` (expected, since new
booking rows were added to the shared master CSV). `test_step4_booking.py` required zero changes
— all its `create_booking` tests use `actor_role="customer"`, which never reaches this slice's
new validation branches.

## Net result

217 passed across direct slice/dependency suites (0 failures attributable to this slice); 1707
passed in the broad sweep, 0 failed.
