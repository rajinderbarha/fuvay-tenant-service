# Deterministic Test Report

Two full independent runs of `tests/test_phase2f*.py`, same environment,
no code changes between them:

| Run | Result |
|---|---|
| 1 | 2445 passed, 0 failed, 0 errors, 29 warnings, 309.42s |
| 2 | 2445 passed, 0 failed, 0 errors, 29 warnings, 307.45s |

Identical pass count and identical failure count (0) across both runs.
No flaky or order-dependent test observed. `tests/test_phase2f37_financial_product_policy_batch.py`
(27/27) and `scripts/workflow_rearchitecture/verify_2f37.py` (21/21,
plus `--selftest` 21/21) were each re-run at least twice with identical
results during the rebaseline pass.
