# Deterministic Test Report

Two full independent runs of `tests/test_phase2f*.py`, same environment,
no code changes between them:

| Run | Result |
|---|---|
| 1 | 2378 passed, 0 failed, 0 errors, 29 warnings, 365.24s |
| 2 | 2378 passed, 0 failed, 0 errors, 29 warnings, 376.82s |

Identical pass count, identical failure count (0), identical warning
count across both runs. No flaky or order-dependent test observed in this
slice's targeted suite or the historical regression suite it touched.
`tests/test_phase2f35_critical_authorization_batch.py` (34/34) and
`scripts/workflow_rearchitecture/verify_2f35.py` (22/22, plus
`--selftest` 22/22) were also each re-run at least twice with identical
results during the rebaseline pass.
