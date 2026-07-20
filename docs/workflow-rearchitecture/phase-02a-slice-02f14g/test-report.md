# Test Report — Slice 2F-14G

## New tests

`tests/test_phase2f14g_field_ops_relationship_provenance.py` — 17 tests, all passing:

- `TestBookingBootstrapRejected` (13, parametrized) — 7 non-qualifying Booking statuses rejected,
  6 qualifying statuses accepted.
- `TestLegacyJobRowTrust` (2) — generic standalone Job rejected as evidence, booking-derived Job
  accepted.
- `TestRelationshipQuerySourceVerification` (2) — source-verifies the SQL-level status/lineage
  filters are actually present in the query construction.

All behavioral tests are deterministic (`MagicMock`/`AsyncMock` booking/job/db objects with
explicit `side_effect` sequencing and `db.add.assert_not_called()` proofs) — behavior is proven
by direct service invocation, not source-string assertion (only
`TestRelationshipQuerySourceVerification` uses source inspection, to confirm the filter
construction, not behavior).

## Regression

See regression-report.md — 202 passed across direct slice/dependency suites (0 failures
attributable to this slice); 1698 passed in the broad partition sweep, 0 failed. No pre-existing
test file required a fixture update this slice.
