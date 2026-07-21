# Repeated Test Stability

## Round 1

Not run this round — no test suite was executed at all this session (see
`unit-component-test-report.md`). Deferred to a later round.

## Round 2

- **mobile/customer-app**: full suite run 3 times total this round (once
  default-parallel, twice more investigating the 1 failure) — parallel run
  is flaky (47-48/48 depending on worker contention), serial (`--runInBand`)
  run is 100% stable at 48/48 across 2 consecutive runs. See
  `typecheck-build-test-baseline.md` for the full analysis.
- **mobile/staff-app**: run once this round (`--runInBand`), 56/56 passed,
  no flakiness observed within this single run.
- **frontend/tenant-portal**: run twice after the `@testing-library/dom`
  fix (`dependency-install-report.md`) — IDENTICAL result both times:
  13/16 suites passed (42 tests), 3/16 suites failed (11 tests). This
  confirms (a) the fix is genuinely stable, not accidentally
  order-dependent, and (b) the remaining 3-suite failure is a consistent,
  reproducible real defect (duplicate React instance from a version-pin
  mismatch — see `typecheck-build-test-baseline.md`), not a flake requiring
  a retry.
- **frontend/super-admin**: run once (`npx vitest run`, no `test` script
  exists) — not re-run a second time this round (time budget); the failure
  mode (`document is not defined`, missing jsdom environment config) is
  clearly an environment-configuration gap, not the kind of timing-
  sensitive issue that benefits from a repeat run.

## Round 4, Pass 1

- **frontend/super-admin**: reproduced the Round 2/3-confirmed baseline
  from a genuinely clean WSL install (`rm`-fresh directory, fresh
  `npm install --workspaces --include-workspace-root --legacy-peer-deps`):
  10/13 passing, 3 failing — identical to the prior rounds' reported
  numbers, confirming no drift.
- After applying the two test-infrastructure fixes documented in
  `super-admin-test-failure-analysis.md` (ResizeObserver mock in
  `test-setup.ts`; scoped `getByRole` query in `patterns.test.tsx`), ran
  `npx vitest run` **3 consecutive times** with no code changes between
  runs:
  - Run 1: 13/13 passed, 3.95s
  - Run 2: 13/13 passed, 3.64s
  - Run 3: 13/13 passed, 3.67s
  All three runs show identical pass/fail composition (Test Files: 4
  passed; Tests: 13 passed) with only a benign recharts console warning
  ("width(0) and height(0) of chart") that does not fail any assertion —
  this is jsdom giving the container zero layout dimensions, not a defect.
  No flakiness observed.
