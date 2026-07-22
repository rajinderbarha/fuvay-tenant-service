# Deferred Items — Slice 2F-39C

- **New, precisely characterized deferred item**: 11 residual full-suite
  failures with the live server running (down from 57/111-errors without
  it), at least 2 distinct causes identified but not fixed this slice:
  - `test_module_l5_47_dispatch_notify.py::TestLive::test_dispatch_and_reassign_notify_staff_live`
    — hardcoded wrong DB credentials (`postgres:postgres` instead of the
    real `serviceos:serviceos`). A one-line test fix, plausible for a
    quick future slice.
  - `test_module_l5_45_package_activation_limits.py` and likely others —
    shared-mutable-real-DB-state test-isolation fragility (a "clean
    slate" assumption violated by prior tests' leftover state in the
    same run). Needs proper per-test setup/teardown or transactional
    rollback, a larger test-infrastructure change.
  - `test_final_l5_04c_matching_entitlement.py` and possibly others —
    depend on specific tenant/category entitlement seed rows this local
    database's minimal dataset doesn't include.
- N01 media routes remain deferred to N01's own remediation track,
  unchanged.
- Slice 2F-40: final application-wide authorization recertification —
  not started.
- All items already deferred by prior slices in this arc remain
  deferred, unchanged, except `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED`
  itself, which is now closed (root cause identified and fixed: dev
  server was not running).
- The dev server started for this investigation
  (`G:/serviceos-2f37r-preserve/2f39c-dev-server.log`) was left running
  as a background process — a confirmed prerequisite for any future
  full-suite run needing a clean `TestLive` signal.
