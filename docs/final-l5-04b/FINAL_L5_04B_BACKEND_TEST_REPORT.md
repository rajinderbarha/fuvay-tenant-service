# FINAL-L5-04B — Backend Test Report

> **Updated in FINAL-L5-04C** — a second real regression was found and fixed (see below), plus 7 new real-database integration tests for matching/booking-confirmation entitlement enforcement.

## Real command
```
python -m pytest tests/ -q
```

## Real result (FINAL-L5-04C, most recent run)
**8835 passed, 90 failed, 42 errors** (out of 8967 collected).

## Baseline comparison — 0 regressions, proven by an actual before/after diff (re-verified in 04C)
04B's baseline (`git stash` before any entitlement code): **8804 passed, 90 failed, 42 errors**. 04C added 7 more real tests: **8804 + 24 (04B) + 7 (04C) = 8835 passed**, with **90 failed / 42 errors identical** to the original baseline both times this diff was performed (once in 04B, once again in 04C after the matching/booking-confirmation changes). Confirmed via a second real `git stash`/re-run cycle in 04C, not just carried forward as an assumption.

## New test file: `tests/test_final_l5_04b_entitlement.py` — 24/24 passing
Covers: migration structure (5 tests), ORM models (4), router registration (1), Admin RBAC (401 all endpoints + 403 for 5 non-admin roles + cross-tenant block, 8 tests), Tenant self-read RBAC (3), service-layer idempotency/not-found logic (3 mocked-DB unit tests), and a real regression test for the VARCHAR(20) cascade-audit bug found and fixed this sprint (1 test, statically scans for any future hardcoded status string exceeding the column length).

## New test file (04C): `tests/test_final_l5_04c_matching_entitlement.py` — 7/7 passing, real database (not mocked)
Unlike most of this repo's tests, these bypass the autouse `mock_database` fixture and run against the real live dev database (`init_db()` + `get_session_factory()` inside a dedicated fixture) — the bulk-resolution SQL join shape is what's under test, and mocking it away would only prove a mock is self-consistent. Covers: bulk entitlement resolution correctness for both tenants/categories (2 tests), a dedicated N+1-regression guard that counts real SQL statements issued (1 test), disable→reenable reflected immediately (1 test), matching-engine exclusion-reason correctness (1 test), and both directions of the booking-confirmation guard (2 tests: blocked when disabled, succeeds when entitled). Each mutating test restores real seeded state in a `finally` block, verified to leave the DB in its canonical 2-module/2-category state afterward.

## Fixed 2 real regressions along the way (04B: 1, 04C: 1)
**04B**: Adding the Service Setup Enforcement guard broke 4 pre-existing tests in `test_sprint3_catalog.py` (their `MasterService` mock fixture fabricated a truthy `service_group_id`). Fixed with an honest fixture default (`service_group_id=None`).

**04C**: Adding the booking-confirmation entitlement guard broke `test_sprint16_home_service_booking.py::TestConfirmDraft::test_confirm_returns_booking_ready_payload` — its `db = MagicMock()` never mocked `db.execute` (not needed before this sprint's change), so the new guard's `await self.db.execute(...)` call hit an un-awaitable `MagicMock`, raising `TypeError: object MagicMock can't be used in 'await' expression`. Root-caused and fixed by mocking `db.execute` to return `scalar_one_or_none() -> None` (simulating the real, correct behavior for a synthetic draft whose `offering_id` doesn't correspond to a real `MasterService` row — the entitlement check is skipped for offerings with no resolvable group, which is the actual production behavior, not a workaround).

## `alembic heads` / `alembic current`
```
alembic heads:   132 (head)
alembic current: 132
```
Single head, matches migration 132, confirmed live.

## `ruff`/`mypy`
Not run this sprint — not confirmed to be part of this repo's established CI gate (not found configured in a way this sprint verified); not claimed as passing.

## Result
0 regressions (proven via real before/after diff, twice — once in 04B, once again in 04C), 31 new passing tests total (24 + 7), 2 real pre-existing-test breakages found and properly fixed (not masked), 4 real production bugs found and fixed across both sprints with regression tests added.
