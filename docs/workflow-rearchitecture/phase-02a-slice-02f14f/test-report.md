# Test Report — Slice 2F-14F

## New tests

`tests/test_phase2f14f_field_ops_manual_customer_authority.py` — 10 tests, all passing:

- `TestStandaloneManualCustomerAuthority` (8) — customer with prior tenant Booking succeeds,
  customer with prior tenant Job succeeds, completely unrelated customer rejected, customer known
  only to another tenant rejected with the identical error, wrong-role user rejected before the
  relationship check even runs, deactivated customer rejected, deleted customer rejected, no
  `customer_id` at all does not trigger the relationship check.
- `TestBookingParentModesUnaffectedByRelationshipGuard` (2) — booking-referenced and
  parent-derived creation both proven to NOT issue an extra relationship query (mock `side_effect`
  sequencing would raise `StopAsyncIteration` if an unexpected extra query occurred).

All fixtures are deterministic (`MagicMock`/`AsyncMock` customer/booking/job/db objects with
explicit `side_effect` sequencing and `db.add.assert_not_called()` proofs) — behavior is proven
by direct service invocation, not source-string assertion.

## Regression

See regression-report.md — 185 passed across direct slice/dependency suites; 1681 passed in the
broad partition sweep with 0 failures this run. Two pre-existing test files required fixture
updates (documented, not silent) to explicitly set `is_active=True, deleted_at=None` on their
customer mock objects.
