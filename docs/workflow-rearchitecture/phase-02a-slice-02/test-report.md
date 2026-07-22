# Test Report

## Backend tests run

| Suite | Result |
|---|---|
| `tests/test_phase2a_my_work.py` (Slice 1, unchanged) | 13 passed |
| `tests/test_sprint21_execution.py` (Slice 1 regression) | 72 passed |
| `tests/test_customer_idor.py` (1 test replaced this slice) | 6 passed |
| `tests/test_sprint4_tenant_onboarding.py` (1 test fixed + 4 new this slice) | 76 passed |
| `tests/test_phase11.py::test_create_review_requires_auth` (unchanged, still passes against new 410 handler since auth check runs first) | 1 passed |
| `tests/test_sprint24_customer_reviews.py` (regression check — canonical review engine untouched) | 40 passed |
| **Combined** | **253 passed, 0 failed** |

Command: `PYTHONPATH=. python -m pytest tests/test_phase2a_my_work.py tests/test_sprint21_execution.py tests/test_customer_idor.py tests/test_sprint4_tenant_onboarding.py tests/test_phase11.py tests/test_sprint24_customer_reviews.py -q`

### New tests added this slice
1. `test_customer_idor.py::test_legacy_review_create_endpoint_is_blocked` — confirms `POST /v1/reviews` now raises `HTTPException(410)`.
2. `test_sprint4_tenant_onboarding.py::test_create_user_rejects_former_placeholder_roles` (parametrized ×4) — confirms `tenant_manager`, `tenant_staff_admin`, `tenant_finance`, `tenant_support` are all rejected by `create_user`.

### Existing tests fixed (behavior changed under them, not broken by accident)
- `test_customer_idor.py::test_create_review_router_ignores_spoofed_customer_id` → replaced (its premise, that the endpoint creates something, no longer holds).
- `test_sprint4_tenant_onboarding.py::test_create_user_duplicate_email` → changed its test-data role from `"tenant_manager"` (now invalid) to `"staff"` (real).

### Pre-existing, unrelated warnings observed (not introduced by this slice)
Same 14 `Duplicate Operation ID` warnings from `app/engines/service_setup/templates_router.py` noted in Slice 1's regression report — still present, still unrelated, not fixed.

## Runtime route-registration verification
Ran `scripts/workflow_rearchitecture/list_routes.py` (Phase 1A tool, reused) before and after all backend changes:
- Total route count: 2,322 (unchanged from Slice 1) — confirms the `POST /v1/reviews` change altered behavior, not route registration/count.
- Targeted check of `/v1/reviews` prefix confirmed the `POST` route is still registered (returns 410 at runtime, not removed from the route table).

## Frontend
- TypeScript compilation (`npx tsc --noEmit`) run on `frontend/super-admin` and `frontend/tenant-portal` after every meaningful change (4 separate runs across this slice) — **0 errors, exit code 0 each time**.
- No `next lint` or `next build` run this slice (same scope decision as Slice 1).
- No frontend unit/component test runner was exercised (none is configured with authenticated-session fixtures in this repo for either app) — verified via TypeScript compilation only, consistent with Slice 1's approach.

## What was NOT tested this slice
- Live HTTP integration tests (real server + real DB) for the 6 new nav-reachable pages, the 410 review endpoint, or the tenant-user-creation fix — all covered by unit/mocked-DB tests instead (matching this repo's existing test conventions, e.g. `test_sprint4_tenant_onboarding.py`'s `_make_db()` mock pattern).
- The 5 other files identified with placeholder-role-shaped arrays (`notifications/templates`, `checklists`, `compliance`, `intelligence`, `workflow-templates`) — not fixed, therefore no tests were needed/added for them; see `known-limitations.md`.
- Admin sub-role (admin_operations/finance/security/readonly) end-to-end navigation tests against a live server — the existing frontend permission-gating logic was read and verified by inspection, not exercised via an automated frontend test (no test harness exists for it in this repo).
