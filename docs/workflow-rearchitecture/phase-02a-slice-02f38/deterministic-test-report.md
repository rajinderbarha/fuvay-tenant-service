# Deterministic Test Report

Two independent full runs of `tests/test_phase2f*.py`, same commit
(`12c7545`), no code changes between them: 2445 passed / 0 failed both
times (387.06s, 368.64s). Identical pass and failure counts. No flaky or
order-dependent test observed. This is the third independent confirmation
of this exact figure across three separate worktrees this program has now
produced (2F-37R-A twice, this slice twice).

Full-backend regression determinism (a second full run) was not performed
this slice given the ~10+ minute-per-run cost of the 12,096-test suite —
see `full-backend-regression-report.md` for the single run's result and
this limitation.
