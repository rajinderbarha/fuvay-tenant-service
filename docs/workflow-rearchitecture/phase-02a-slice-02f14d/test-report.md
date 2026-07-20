# Test Report — Slice 2F-14D

## New tests

`tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` — 10 tests, all passing:

- `TestBookingRelationalConsistency` (5) — matching booking/customer/service succeeds,
  customer/booking mismatch rejected, service/booking mismatch rejected, already-converted
  booking rejected, duplicate Job-for-booking rejected.
- `TestParentJobRelationalConsistency` (5) — matching parent/customer succeeds, customer/parent
  mismatch rejected, duplicate repair-from-consultation rejected, differing repair service
  allowed (policy), second non-repair child from the same parent allowed (policy).

All fixtures are deterministic (`MagicMock`/`AsyncMock` job/booking/db objects with explicit
`side_effect` sequencing matching the exact order of DB calls `create_job` now makes) — behavior
is proven by direct service invocation, not source-string assertion.

## Regression

See regression-report.md — 253 passed across direct slice/dependency suites; 1625 passed in the
broad partition sweep; 21 pre-existing live-environment exclusions honestly disclosed and not
counted as passing. One pre-existing test file
(`tests/test_job_type_flows.py`) required a fixture update (one additional mock DB response) to
match the new duplicate-repair check — documented in regression-report.md, not silent.
