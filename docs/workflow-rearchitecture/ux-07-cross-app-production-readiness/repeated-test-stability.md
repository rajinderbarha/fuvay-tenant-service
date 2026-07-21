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
