# Phase-2F Regression Report — Slice 2F-39A

Full `tests/test_phase2f*.py` regression, run twice:

| Run | Result | Duration |
|---|---|---|
| A | 2477 passed, 0 failed, 0 errors, 32 warnings | 420.38s |
| B | 2477 passed, 0 failed, 0 errors, 32 warnings | 348.60s |

Collection grew from the 2473 baseline to 2477 (+4 — exactly this
slice's new `test_phase2f39a_canonical_additions.py`, which matches the
`test_phase2f*.py` glob). Identical, clean results across both runs.
