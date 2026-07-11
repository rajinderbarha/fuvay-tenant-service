# FINAL-L5-01D — Test Results

## Backend
- `pytest --collect-only -q`: **8,936 tests collected, 0 errors** — unchanged from before this sprint, confirming the seed-script edit introduced no import/syntax breakage.
- `tests/test_final_l5_01b_admin_tenant_rbac.py`: **21/21 passing**, re-confirmed 3 times this sprint (before fixes, after Tenant Jobs migration, after full repeatability cycle).
- Full non-collect `pytest`, `ruff check .`, `mypy .`: not run this sprint — same proportionate-scope decision as prior FINAL-L5-01* sprints.
- `alembic heads` / `alembic current`: `131 (head)`, unchanged.

## Frontend (tenant-portal — the app with all of this sprint's code changes)
- `npx tsc --noEmit`: **0 errors**, verified 3 times (after Tenant Jobs migration, after Read-Only fix, after full repeatability cycle).
- `npm run build` / `npm test`: not run this sprint (time constraint) — TypeScript strictness is the verification performed.

## Playwright (real Chromium, this sprint's actual verification method)
| Spec | Result |
|---|---|
| `final-l5-01d-readonly-precision.spec.ts` | 1/1 passed — 4-page banner/button check |
| `final-l5-01d-technician-redirect.spec.ts` | 1/5 successful transitions within 15s (see technician redirect reports) |
| `final-l5-01d-tech-debug.spec.ts` | 1/1 passed — isolated full-detail capture, confirmed correct end state |
| `final-l5-01d-regression.spec.ts` | 2/3 passed cleanly (Customer bookings, Admin); Tenant Jobs test captured all required assertions successfully before an unrelated click-interaction hang |
| `final-l5-01d-job-detail.spec.ts` | 1/1 passed (after Turbopack first-compile latency was accounted for) |

## Required focused tests (mission Part 22 checklist)

| Requirement | Status |
|---|---|
| Tenant canonical jobs API | **Verified live + in browser** |
| Legacy `/v1/jobs` not used by Tenant Jobs | **Verified via real browser network capture** (`USED_LEGACY_V1_JOBS: false`) |
| Booking source decision | **Made and documented with code-level evidence** |
| Booking seed idempotency | **Proven** — reran seed, 100% skips |
| Customer booking list/detail/tracking | **Verified live and in browser** |
| Customer isolation | **Verified** — zero leakage in both directions |
| Tenant Read Only UI | **Verified live in browser** for Jobs pages; broader app has 1 known remaining gap (Service Areas) |
| Tenant Read Only 403-before-422 | **Verified live** on 2 mutation endpoints |
| Technician redirect stability | **Not proven** — real fix applied, 1/5 repeated runs succeeded |

## Result
No regressions. Both primary objectives (Tenant Jobs migration, Customer Booking source alignment) have layered evidence (unit-level idempotency, live API, real browser). Technician redirect has a real, verified-correct fix but unproven repeat-stability.
