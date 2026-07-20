# Phase-2F Regression Report — Slice 2F-38

Full `tests/test_phase2f*.py` regression, run twice against the
certification branch (`security/phase-2f38-certification`, commit
`12c7545` at the time of the runs, base `01e6ee4`):

| Run | Result | Duration |
|---|---|---|
| 1 | 2445 passed, 0 failed, 0 errors, 29 warnings | 387.06s |
| 2 | 2445 passed, 0 failed, 0 errors, 29 warnings | 368.64s |

Identical collection count (2445) and identical pass/fail counts across
both runs. This exactly reproduces Slice 2F-37R-A's own two-run result
(484.38s/399.32s, same 2445/0), independently, in a third separate
worktree/branch — the strongest evidence yet that this figure is real and
stable, not an artifact of any one worktree's state.

No test was added, removed, or renamed by this slice's certification work
(only documentation and tooling files were added).
