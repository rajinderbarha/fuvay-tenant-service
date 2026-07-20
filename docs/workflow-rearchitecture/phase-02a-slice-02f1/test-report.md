# Test Report — Slice 2F-1

## New tests this slice
`tests/test_phase2f1_tenant_engine_mutation_enforcement.py` — 40 tests across
4 classes:
1. `TestReadOnlyAccessScopeDeniedAcrossAllGuardedEndpoints` (19) — every one
   of the 19 newly-guarded endpoints rejects a read-only-scoped principal
   (staff role, valid tenant membership, `access_scope=customer_support_limited`,
   **plus an explicit `permission_overrides` grant for every relevant
   `tenant:*` permission**) with 403, proving the access-scope gate rejects
   independently of an affirmative permission grant — the exact "permission
   grant must NOT override read-only access scope" requirement from the
   brief. Never uses the real `readonly@` account.
2. `TestTenantOwnerAndCrossTenantBehavior` (10) — representative sample
   (update_tenant, bulk_enable, set_feature_flag, update_payment_method)
   proving: authorized tenant_owner clears the auth layer; cross-tenant
   tenant_owner is rejected 403 by the pre-existing
   `_assert_own_tenant_or_super_admin` (unmodified this slice); super_admin
   stays exempt from the access-scope check even with a hypothetical
   read-only `access_scope` set; unauthenticated requests get 401.
3. `TestPlatformAdminAndPublicEndpointsUnaffected` (2) — source-inspection
   regression guards proving the 7 `require_super_admin`-gated endpoints and
   the 1 public signup endpoint were NOT touched (still use their original
   dependency, never gained `require_tenant_mutation_permission`).
4. `TestReadPathsUnaffected` (7) — representative GET endpoints (tenant
   detail, engines list, feature-flags list) still work for an authorized
   owner, still enforce tenant isolation on reads, and a read-only-scoped
   user can still read (proving the guard is mutation-only by design, not an
   accidental blanket lockout).
5. `TestDeactivateStaffSessionRevocation` (2) — Workstream 11's fix: Redis
   flag set for every active session on deactivation; no unnecessary Redis
   calls when there are no active sessions.

Plus 2 new regression tests added to the existing
`tests/test_phase2f_mutation_enforcement.py::TestMutationRouteInventoryScript`
covering the extended `guard_status()` classifier and a live re-run proving
`tenant_engine.router` has 0 unverified routes out of 27 (Workstream 12).

Plus 1 updated test in `tests/test_phase2d_tenant_access_model.py`
(`test_coverage_of_require_tenant_mutation_permission_is_still_narrow`):
count bumped from 2 to 3 caller files, with `tenant_engine/router.py` now
asserted present — documented growth, not silent staleness.

## Combined regression run
```
tests/test_phase2a_my_work.py .............................. 13 passed
tests/test_sprint21_execution.py .......................... 72 passed
tests/test_customer_idor.py ............................... 6 passed
tests/test_sprint4_tenant_onboarding.py ................... 76 passed
tests/test_phase11.py::test_create_review_requires_auth ... 1 passed
tests/test_sprint24_customer_reviews.py ................... 40 passed
tests/test_phase2c_role_integrity.py ....................... 7 passed
tests/test_phase2d_tenant_access_model.py ................. 18 passed
tests/test_phase2e_effective_permissions.py ................ 9 passed
tests/test_phase2f_mutation_enforcement.py (updated) ....... 8 passed
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 40 passed (new)
tests/test_auth_login_fix.py
tests/test_final_l5_05p_tenant_provider_staff_permissions.py
tests/test_final_l5_05u_security_deposit_permission_authorization.py
tests/test_module_l5_01a_admin_finance_router_auth.py ...... (72 combined)
tests/test_final_l5_01b_admin_tenant_rbac.py ............... (included)
─────────────────────────────────────────────────────────────────
TOTAL: 382 passed, 0 failed, ~54s
```
Same 14 pre-existing, unrelated `service_setup` duplicate-operation-ID
warnings as every prior slice — unchanged, not fixed, out of scope.

## Live actions this slice (beyond pytest)
- Ran the extended `inventory_mutation_routes.py --verify-module
  app.engines.tenant_engine.router` live against the running app: **exit 0,
  27 total routes, 0 unverified.**
- Ran `inventory_mutation_routes.py --module app.engines.tenant_engine.router`
  (full JSON mode) live: confirmed guard-status breakdown of
  `{PUBLIC_NO_AUTH: 1, PLATFORM_ADMIN_ONLY: 7, TENANT_MUTATION_PERMISSION_SCOPE_AWARE: 19}`,
  exactly matching the classification in `tenant-engine-mutation-inventory.csv`.
- Verified via `app.main` import that the app still boots cleanly after the
  router edit (no circular import, no missing name).

## Full-repository suite
Not attempted this slice (same limitation as Slices 2E/2F) — the 382-test
targeted combined suite is the evidence base, explicitly not claimed as
full-repository coverage.

## Frontend
No frontend code changed this slice.
