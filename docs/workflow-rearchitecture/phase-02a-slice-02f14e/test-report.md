# Test Report — Slice 2F-14E

## New tests

`tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py` — 31 tests, all passing:

- `TestBookingStatusEligibility` (13) — every non-`CONFIRMED` Booking status rejected
  (parametrized over all 12 real statuses), `CONFIRMED` accepted.
- `TestParentStatusEligibility` (14) — every non-`QUOTE_APPROVED` CONSULTATION-parent status
  rejected as a repair source (parametrized over 12 real statuses), `QUOTE_APPROVED` accepted,
  non-CONSULTATION parent status correctly NOT gated.
- `TestBookingParentCoexistence` (3) — both fields together rejected, either alone unaffected.
- `TestRouteSecurityRegression` (1) — source-verifies `create_job`'s router guard is unchanged.

All fixtures are deterministic (`MagicMock`/`AsyncMock` booking/job/db objects with explicit
`side_effect` sequencing and `db.add.assert_not_called()` proofs on rejection) — behavior is
proven by direct service invocation, not source-string assertion (only
`TestRouteSecurityRegression` uses source inspection, to confirm the router-level guard wasn't
touched).

## Regression

See regression-report.md — all direct slice/dependency suites passing (138/253 across different
combined runs, 0 failures); 1656 passed in the broad partition sweep; the same pre-existing
live-environment exclusion class honestly disclosed. One pre-existing test file
(`tests/test_phase2f14d_...py`) required fixture updates (documented, not silent) to supply the
new default statuses its mocks now need.
