# Phase-2F Regression Report — Slice 2F-37R-A

## Summary

Full `tests/test_phase2f*.py` regression, run twice against the final
committed recovery branch (`security/phase-2f-authorization-recovered`,
commit `d00f723`):

| Run | Result | Duration |
|---|---|---|
| A | 2445 passed, 0 failed, 0 errors, 29 warnings | 484.38s |
| B | 2445 passed, 0 failed, 0 errors, 29 warnings | 399.32s |

Identical collection count (2445) and identical pass/fail counts across
both runs — no flaky or order-dependent test observed.

## Failures found and fixed during this slice (not hidden)

Two intermediate runs, against earlier commits on this same branch, found
real regressions this slice caused and fixed before reaching the clean
result above:

1. **5 failures** (`regression-run1.txt`, against commit `29dd931`):
   4 tests statically inspecting `frontend/tenant-portal/lib/api.ts` for
   absence of certain platform-only-action callers, plus
   `test_migration_144_remains_unapplied`. Root cause: the initial
   exclusion pass deleted 47 paths that existed at the recovery base
   (`4ce23c5`) instead of reverting them to base content, which both
   removed `lib/api.ts` entirely (breaking the 4 caller-inventory tests)
   and broke the Alembic revision chain by deleting `alembic/versions/087_*`
   (which `test_migration_144_remains_unapplied` depends on transitively).
   Fixed in commit `dc7e936` — classified `UNKNOWN_PATH` correction, see
   `unknown-path-resolution.md`.
2. **1 failure** (`regression-run1-corrected.txt`, against commit `dc7e936`):
   `test_migration_144_remains_unapplied` still failed, for an unrelated
   reason: its assertion used "migration 144 appears as untracked in
   `git status --porcelain`" as a proxy for "not applied to a database" —
   a proxy that was only ever true because this program had never been
   committed. Since this slice's entire purpose is to commit a clean
   baseline, the proxy became permanently unsatisfiable. Fixed with an
   explicit `PROTECTED_BY_LATER_SLICE: 2F-37R-A` exemption in commit
   `d00f723` (see `historical-test-integrity-report.md`) that checks the
   real invariant (file exists, no application marker) instead.

Both fixes are narrowly scoped, individually commented, and preserve the
original test's stated intent. Neither is a broad rebaseline.

## What was NOT run

Live HTTP smoke tests were not attempted (no reachable running server in
this environment, unchanged from every prior slice in this program).
