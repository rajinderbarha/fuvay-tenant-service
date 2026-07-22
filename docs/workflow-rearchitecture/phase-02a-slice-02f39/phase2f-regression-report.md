# Phase-2F Regression Report — Slice 2F-39

Full `tests/test_phase2f*.py` regression, run twice against this slice's
final state:

| Run | Result | Duration |
|---|---|---|
| A | 2473 passed, 0 failed, 0 errors, 32 warnings | 449.50s |
| B | 2473 passed, 0 failed, 0 errors, 32 warnings | 406.37s |

Collection grew from the 2445 baseline to 2473 (+28 — exactly this
slice's new `test_phase2f39_seed_role_guard.py`, which matches the
`test_phase2f*.py` glob). Identical, clean results across both runs.
