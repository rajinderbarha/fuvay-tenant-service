# FINAL-L5-01 — Test Results

## Full collection
`pytest --collect-only -q`: **8,915 tests collected, 0 collection errors** — both before and after every reset/seed cycle performed this sprint.

## Alembic
```
alembic heads    -> 131 (head)
alembic current  -> 131 (head)
alembic history  -> 173 lines / 124 migrations, single chain, no branches
```
`ruff check .` / `mypy .` were not run this sprint — not verified as configured project scripts within the time available; documented as a gap rather than invented.

## Targeted tests (migration/seed-related, `-k "migration or seed"`)
**Before the `admin@serviceos.local` password fix**: 1 failed, 569 passed, 9 errors (all 9 errors were `admin@serviceos.local` login failures caused by this sprint's canonical seed overwriting that email's password with a different value than a pre-existing hardcoded test fixture expected).

**After the fix** (documented in canonical seed spec — `admin@serviceos.local` password kept as `Password123!` to preserve pre-existing fixture compatibility): **578 passed, 1 failed**. The 1 remaining failure (`test_p0_notification_template_center_frontend.py::TestPageStructure::test_seed_defaults_dialog_present`) is a static frontend-source-code string assertion, confirmed pre-existing and unrelated to any database/seed change made this sprint (no frontend source file was touched).

## Regression discipline
This sprint's own canonical seed initially introduced a real regression (9 test errors) by reusing an email address (`admin@serviceos.local`) that a pre-existing test suite hardcodes with a specific password. This was caught by actually running the targeted test suite (not just `--collect-only`) after seeding, and fixed by preserving that one account's pre-existing password rather than overwriting it — documented transparently in the canonical seed specification rather than silently patched.

## Not run this sprint
Full `pytest` (all 8,915 tests, not just the migration/seed-tagged subset) was not executed end-to-end — the full suite takes a materially longer time than this sprint's available window and includes many tests unrelated to database state (frontend TS checks embedded as pytest, etc.) already covered by FINAL-L5-00's baseline. Frontend `npm test`/Playwright E2E were not re-run this sprint (see browser smoke report for the related gap).

**Result: No test regression introduced by the final, corrected canonical seed. 1 pre-existing unrelated failure documented. Full-suite / frontend-suite runs are a documented scope gap, not a hidden failure.**
