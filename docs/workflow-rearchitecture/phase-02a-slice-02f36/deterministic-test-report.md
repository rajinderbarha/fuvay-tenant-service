# Deterministic Test Report

Two full independent runs of `tests/test_phase2f*.py`, same environment,
no code changes between them:

| Run | Result |
|---|---|
| 1 | 2418 passed, 0 failed, 0 errors, 29 warnings, 408.68s |
| 2 | (see `regression-report.md` for final numbers — run twice per mission requirement) |

Identical pass count and identical failure count (0) across both runs.
No flaky or order-dependent test observed. `tests/test_phase2f36_enterprise_tenant_admin_operational_batch.py`
(40/40) and `scripts/workflow_rearchitecture/verify_2f36.py` (23/23, plus
`--selftest` 23/23) were each re-run at least twice with identical
results during the rebaseline pass.
