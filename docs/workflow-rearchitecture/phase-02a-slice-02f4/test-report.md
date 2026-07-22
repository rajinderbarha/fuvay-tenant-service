# Test Report — Slice 2F-4

## New tests this slice
`tests/test_phase2f4_tenant_portal_mutation_enforcement.py` — 35 tests
across 8 classes:
1. `TestReadOnlyDeniedAcrossAllGuardedEndpoints` (10) — read-only-scoped
   tenant_owner rejected at all 10 endpoints, even with an explicit
   `permission_overrides` grant.
2. `TestAuthorizedOwnerClearsAuthLayer` (10 + 2 = 12) — authorized
   tenant_owner clears the auth layer for all 10, plus unauthenticated-401
   and super_admin-exemption tests.
3. `TestUnauthorizedRoleRejected` (3) — staff/technician/customer rejected.
4. `TestReadsUnaffected` (1) — the 2 GET endpoints untouched.
5. `TestAlternateAdminRouteUnaffected` (1) — `tenant_engine.admin_router`'s
   parallel super_admin-gated route confirmed unchanged.
6. `TestServiceLayerOwnershipUnchanged` (4) — source-inspection proof that
   tenant/object ownership and role-escalation protection remain intact.
7. `TestLockUnlockRevokeCrashFixed` (2) — the real `AuthService(actor_id=...)`
   crash bug found and fixed.
8. `TestAdminTenantServiceDeactivateStaffSessionRevocation` (2) — the real
   missing-session-revocation bypass found and fixed.

## Combined targeted regression run
```
tests/test_phase2f_mutation_enforcement.py ................. 11 passed
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 88 passed
tests/test_phase2f2_provider_portal_mutation_enforcement.py  53 passed
tests/test_phase2f3a_execution_assignment_overlap.py ....... 7 passed
tests/test_phase2f3b_execution_assignment_mutation_enforcement.py 68 passed
tests/test_phase2f4_tenant_portal_mutation_enforcement.py .. 35 passed (new)
tests/test_phase2d_tenant_access_model.py .................. 18 passed
────────────────────────────────────────────────────────────────
280 passed, 0 failed
```
Plus the wider Slice 2F-family combined run (all prior slices' dedicated
suites + auth/tenant tests): **594 passed, 0 failed** (see below for the
exact command).

## Broader partition (auth, session, staff lifecycle, role editing, cross-tenant IDOR, onboarding)
```
tests/test_final_l5_05m_frontend_permission_guards.py
tests/test_final_l5_05n_role_editor_repair.py
tests/test_module_l5_01_tenant_cross_tenant_idor.py
tests/test_module_l5_01d_canonical_roles.py
tests/test_phase0e_account_security.py
tests/test_module_l5_43_super_admin_staff_deactivate.py
tests/test_p0_provider_onboarding.py
tests/test_phase5_tenant_onboarding_certification.py
────────────────────────────────────────────────────────────────
226 passed, 5 skipped, 0 failed
```
5 pre-existing skips, not investigated (unrelated to this slice).

**Not claimed as full-repository coverage** — 594 + 226 = 820 combined
tests, 0 real failures.

## Live actions this slice
- Ran `inventory_mutation_routes.py --module app.engines.tenant_engine.portal_router`
  before and after the guard swap.
- Ran `--verify-module app.engines.tenant_engine.portal_router`: **exit 0,
  0 unverified out of 10.**
- Confirmed `app.main` imports cleanly after every code change (guard
  swap, `AuthService` constructor fix, `AdminTenantService.deactivate_staff`
  session-revocation fix).
- Grepped `frontend/tenant-portal/lib/api.ts` directly for all 10 path
  fragments and their camelCase equivalents to build the frontend-exposure
  audit, which is what surfaced the `auth.router` alternate-route finding.

## Frontend
No frontend code was changed this slice — read-only for audit purposes.
