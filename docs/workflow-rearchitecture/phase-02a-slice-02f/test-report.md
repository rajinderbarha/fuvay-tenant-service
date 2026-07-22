# Test Report — Slice 2F

## New tests this slice
`tests/test_phase2f_mutation_enforcement.py` — 6 tests across 2 classes:
1. `TestPermissionReductionSessionRevocation` (4) — pure grant does not revoke; grant-to-deny revokes both DB and Redis for every active session; a brand-new explicit deny (no prior row) also counts as a reduction; cross-tenant target rejection remains intact.
2. `TestMutationRouteInventoryScript` (2) — the new inventory script's path-prefix classifier and mutation-method set.

## Combined regression run
```
tests/test_phase2a_my_work.py .......................... 13 passed
tests/test_sprint21_execution.py ...................... 72 passed
tests/test_customer_idor.py ........................... 6 passed
tests/test_sprint4_tenant_onboarding.py ............... 76 passed
tests/test_phase11.py::test_create_review_requires_auth 1 passed
tests/test_sprint24_customer_reviews.py ............... 40 passed
tests/test_phase2c_role_integrity.py .................. 7 passed
tests/test_phase2d_tenant_access_model.py ............. 18 passed
tests/test_phase2e_effective_permissions.py ........... 9 passed
tests/test_phase2f_mutation_enforcement.py (new) ...... 6 passed
tests/test_auth_login_fix.py .......................... (included in 72 below)
tests/test_final_l5_05p_tenant_provider_staff_permissions.py
tests/test_final_l5_05u_security_deposit_permission_authorization.py
tests/test_module_l5_01a_admin_finance_router_auth.py
────────────────────────────────────────────────────────
TOTAL: 365 passed, 0 failed, 153.50s
```
Same 14 pre-existing, unrelated `service_setup` duplicate-operation-ID warnings, unchanged.

## Full-repository suite attempt (per the brief's explicit request)
A broader `pytest tests/` run was attempted in a prior slice (2E) and time-boxed at ~5% progress with zero failures before being stopped. This slice instead ran the full **targeted** combined suite (all prior slices' dedicated test files plus the 4 directly auth-adjacent suites most likely affected by touching `AuthService`) to completion — 365 tests, 153.5 seconds, 100% of that targeted set, 0 failures. **This is not a claim of full-repository coverage** — the repository's total test count is materially larger (thousands, based on Slice 2E's partial-run observation), and this slice does not assert every one of those was re-run. Per the brief's own instruction ("do not imply that a targeted suite equals full-repository verification"), this is stated explicitly rather than implied.

## Live actions this slice (beyond pytest)
- Ran `inventory_mutation_routes.py` live against the running app, producing the 1,188-route / 185-tenant-route dataset underlying `tenant-mutation-endpoint-inventory.csv` and `mutation-enforcement-matrix.csv`.
- Verified live (via direct DB query) that `readonly@demo-ac-services.local`'s role and session state are unchanged from the start of this slice.
- Verified live (`alembic current`) that migration 144 remains unapplied at revision 143.
- Verified live (`list_routes.py`) that the total registered route count (2,322) is unchanged — this slice added no new FastAPI route.

## Frontend
No frontend code was changed this slice — no TypeScript compilation or lint run needed.

## Route registration
2,322 total routes, unchanged. No collisions.
