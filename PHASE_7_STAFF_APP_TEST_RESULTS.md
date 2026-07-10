# Phase 7 — Test Results

## Backend command

```bash
python -m pytest tests/ -q
```

## Backend result

**8095 passed, 37 failed, 1 skipped.** All 37 failures match the exact
pre-existing, unrelated baseline confirmed in every prior sprint this
session (frontend-assertion tests for unrelated pricing/catalog/nav-config
pages). **0 new failures introduced by Phase 7** — this sprint's backend
changes were: 1 tenant-isolation fix (1-line condition extension), 3
role-filter fixes (identical 1-line pattern), 1 new idempotent-guarded
migration, and 1 data-seeding step via the real API.

## New tests added this sprint

`tests/test_phase7_staff_app_certification.py` — **10/10 passed**, covering:
the tenant-isolation fix in `list_jobs`, the staff-id override, the job-
detail isolation helper, the staff-jobs-router role restriction, the
tenant-staff-list role-filter fix, the `provider_team_members` migration +
model column consistency, the structurally-safe `/v1/auth/me` schema, the
forbidden-label absence, and the absence of job-completion/payment
mutations in the staff job shell.

## Frontend TypeScript result

```bash
npx tsc --noEmit
```

**0 errors** on `frontend/tenant-portal` (no frontend code changed this
sprint — there is no technician-facing frontend to change).

## Frontend build/lint/test result

Not re-run (no frontend files touched). `npm test`: no script exists;
Python static-inspection substitute used as established.

## Result: **PASS — 0 new regressions, all new certification tests green, TypeScript clean.**
