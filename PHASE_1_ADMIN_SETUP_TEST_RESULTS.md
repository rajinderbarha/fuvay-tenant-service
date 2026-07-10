# Phase 1 — Admin Setup Frontend + Backend Certification — Test Results

## Backend test command

```bash
pytest tests/ -q
```

## Backend result

**7968 passed, 37 failed, 1 skipped.** All 37 failures are the same
pre-existing, unrelated baseline confirmed in Phase 0 and the earlier Phase 1
sprint (catalog/pricing-form frontend-assertion tests predating a concurrent
process's nav-config refactor). **0 new failures caused by this sprint's
changes.**

New tests added this sprint: `tests/test_phase1_admin_setup_frontend_backend_certification.py`
— **4/4 passed**, covering the new `login-events` admin endpoint.

## Frontend TypeScript result

```bash
npx tsc --noEmit
```

**0 errors.**

## Frontend lint result

```bash
npx next lint
```

**Broken, pre-existing** (documented in Phase 0) — Next.js 16 removed the
`next lint` subcommand; not caused by this sprint.

## Frontend test result

No JS test runner configured in this repo (same finding as every prior
sprint this session). Python source-inspection tests via `pytest` is the
established convention; frontend module pages were verified via source
inspection in `PHASE_1_ADMIN_SETUP_FRONTEND_REPORT.md`.

## Known pre-existing failures (37, unrelated to Phase 1)

Same list as documented in `PHASE_0_TEST_RESULTS.md` — unchanged.

## New failures caused by this sprint

None.
