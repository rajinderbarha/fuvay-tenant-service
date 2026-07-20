# Documentation Corrections - Slice 2F-30

## 1. Slice 2F-29 final test count (explicitly requested)

Corrected from **2170** to **2213 passed, 0 failed, 0 errors** in:
`approval-gate.md`, `deterministic-test-report.md`,
`environment-test-evidence.md`, `implementation-summary.md`,
`regression-report.md`, `test-report.md`, `regression-comparison.csv`.

The one remaining `2170` is in `regression-report.md` under a heading now
labelled *"Before (pre-slice baseline, excludes this slice's new M01 test
file)"* - that figure is accurate as the pre-slice baseline; 2213 is the final
total and already includes the 43 new M01 tests.

## 2. Slice 2F-28 risk scores superseded

2F-28's scores for media and security-deposit assumed missing object ownership.
Reading the services this slice disproved that (`MediaAccessService`,
`_assert_owns_tenant_deposit`). 2F-28's artifacts are left as the historical
record; this slice's `updated-module-risk-scoring.csv` supersedes them and
carries an `ownership_verified_in_service` column so the basis is auditable.

## 3. 2F-28 queue artifact is point-in-time

Its 45 routes were correct when written. This slice rebuilt the queue from the
live inventory (33) rather than editing 2F-28. `45 - 12 (M01) = 33`.
