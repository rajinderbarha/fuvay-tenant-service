# Test Report — Slice 2F-15

## New tests

`tests/test_phase2f15_booking_customer_identity_and_confirmation.py` — 9 tests, all passing:

- `TestAssistedBookingCustomerValidation` (5) — foreign/wrong-role/disabled/deleted customer
  rejected; customer self-booking proven to skip the validation branch entirely (via an
  `AssertionError`-raising `db.execute` mock that would fail the test if the check were
  mistakenly triggered).
- `TestAssistedBookingRelationshipRequirement` (2) — the exact Slice 2F-14G bootstrap attack
  rejected; an assisted booking WITH an existing relationship succeeds (full pipeline exercised
  via patched `ServiceabilityService`/`_run_legacy_preflight`, matching the established
  `test_step4_booking.py` mocking pattern).
- `TestBookingRouterGuardSources` (2) — source-verifies the router dependency upgrades.

All behavioral tests are deterministic (`MagicMock`/`AsyncMock` with explicit `side_effect`
sequencing and `db.add.assert_not_called()` proofs) — behavior is proven by direct service
invocation, not source-string assertion (only `TestBookingRouterGuardSources` uses source
inspection, to confirm wiring).

## Regression

See regression-report.md — 217 passed across direct slice/dependency suites (0 failures
attributable to this slice); 1707 passed in the broad partition sweep, 0 failed. One test file
(`test_phase2f14a_field_ops_alternate_route_and_coverage.py`) required an expected
canonical-figure update (174/221); `test_step4_booking.py` required zero changes.

## Lint/type checking

Not run this slice — not verified (reported honestly per the mission's instruction, rather than
claimed as passing).
