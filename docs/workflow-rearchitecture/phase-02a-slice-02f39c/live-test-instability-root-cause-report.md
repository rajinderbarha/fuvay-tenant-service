# Live-Test Instability Root-Cause Report — Slice 2F-39C

## Mission

Investigate `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED`, the disposition
assigned in Slice 2F-39A4 to 31 failures + 111 errors that appeared in
full-suite runs beyond the known 26-failure baseline, reproduced
byte-for-byte identically in Slice 2F-39A5. The 2F-39A4 review asked for
this to be reproduced under a controlled server-capacity setup rather
than dismissed.

## Root cause #1 (CONFIRMED, FIXED): no live dev server was running

Investigation of the `TestLive`-suffixed test classes
(`test_trust_quality_phase1.py`, `test_p0_provider_enterprise.py`, etc.)
showed they open a real `httpx.AsyncClient`/`asyncpg` connection against
`http://localhost:8000` — a server that pytest itself **never starts**.
It must already be running externally before the suite runs. Checking
port 8000 at the start of this slice's investigation: **nothing was
listening**. No live dev server had been running during either of Slice
2F-39A4's or 2F-39A5's full-suite runs, which is why every
`TestLive`/`test_no_auth_returns_4xx`-style test failed with
`httpcore.ConnectTimeout` — not a capacity/timeout problem under
sustained load, simply a missing precondition.

**Fix applied**: started `python -m uvicorn app.main:app --host 0.0.0.0
--port 8000` as a persistent background process (log:
`G:/serviceos-2f37r-preserve/2f39c-dev-server.log`). Confirmed live via
`curl` (login succeeds, returns a valid JWT) and via re-running
`test_trust_quality_phase1.py` in isolation: **28/28 passed** (previously
all 21 tests in that file errored at fixture setup).

**Full-suite proof**: re-ran the entire backend suite with the server
running: **11 errors → 0 errors** (all 111 setup-time `ConnectTimeout`
errors eliminated). Failures dropped from 57 to 37.

**Disposition retired**: `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED` is
closed. It was not a capacity ceiling or resource-exhaustion issue — it
was the dev server simply not being started before the suite ran.

## Root cause #2 (NEW FINDING, NOT FIXED — out of this slice's scope): residual live-test fragility

With the server running, **11 failures remain beyond the 26-item known
baseline** — all genuine assertion/connection failures now (not
`ConnectTimeout`), meaning the server itself responds correctly but
something else is wrong. Investigated 3 representative cases:

1. **Hardcoded wrong DB credentials.**
   `test_module_l5_47_dispatch_notify.py::TestLive::test_dispatch_and_reassign_notify_staff_live`
   calls `asyncpg.connect("postgresql://postgres:postgres@127.0.0.1:5432/serviceos")`
   — the default Postgres superuser credentials, not this environment's
   actual configured user (`serviceos:serviceos`, confirmed via
   `get_settings().DATABASE_URL`). This is a pre-existing bug in the test
   itself, unrelated to the server-running fix.

2. **Shared-mutable-real-DB-state test-isolation violation.**
   `test_module_l5_45_package_activation_limits.py::test_activation_creates_and_sets_limits_and_commission_live`
   explicitly checks for a "clean slate" (`if had_limits or had_settings:
   pytest.skip(...)`) but fails instead of skipping — meaning a specific
   tenant's `tenant_limits`/`tenant_operational_settings` rows are
   already populated, most likely by another test earlier in the same
   full-suite run mutating shared real database state with no teardown.
   This is a test-ordering/isolation fragility in a suite that uses a
   real, shared, un-reset database rather than per-test transactional
   rollback — a structural issue, not a logic defect in the tested code.

3. **Entitlement-data-dependent tests**
   (`test_final_l5_04c_matching_entitlement.py`) fail with
   `EntitlementNotFoundError: no active entitlement for category` — this
   database's actual seed data doesn't include the specific
   tenant/category entitlement rows these tests assume exist. Consistent
   with this slice's Migration 144 investigation finding (this local dev
   database has a minimal 12-user dataset, not the fuller demo/seed
   dataset some older test suites assume).

**Not investigated further or fixed this slice.** Resolving these would
require either: seeding missing entitlement/tenant data (a database
write this slice's scope does not cover), fixing the hardcoded
credential in `test_module_l5_47_dispatch_notify.py` (a one-line test
fix, plausible for a future slice), and/or adding proper
setup/teardown or per-test isolation to
`test_module_l5_45_package_activation_limits.py` and similar tests
(a larger test-infrastructure change). Recorded as a new, more precisely
characterized deferred item — not conflated with the now-closed
`LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED` disposition.

## Net effect

| Metric | Without server (2F-39A4/A5 baseline) | With server (this slice) |
|---|---|---|
| Passed | 11,969 / 11,976 | 12,108 |
| Failed | 57 | 37 |
| Errors | 111 | **0** |
| Skipped | 33 | 32 |

The dev server log is preserved at
`G:/serviceos-2f37r-preserve/2f39c-dev-server.log` for reference. The
server process was left running (background task) since it is now a
confirmed prerequisite for any future full-suite run to get a clean
signal on `TestLive`-dependent tests.
