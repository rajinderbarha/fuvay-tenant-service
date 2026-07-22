# Phase-2F Regression Report — Slice 2F-39B

Full `tests/test_phase2f*.py` regression, run twice (this slice touched
only `tests/test_phase2c_role_integrity.py`, no application code, no
migrations):

| Run | Result | Duration |
|---|---|---|
| A | 2526 passed, 0 failed, 0 errors, 38 warnings | 561.72s (0:09:21) |
| B | 2526 passed, 0 failed, 0 errors, 38 warnings | 376.62s (0:06:16) |

Collection unchanged from the 2526 baseline (Slice 2F-39A5) — this
slice's test file edit renamed/rewrote 1 existing test in place, adding
no new test. Identical, clean results across both runs.
