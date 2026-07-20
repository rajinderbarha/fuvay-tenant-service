# Test Report — Slice 2F-3B

## New tests this slice
`tests/test_phase2f3b_execution_assignment_mutation_enforcement.py` — 68
tests across 8 classes:
1. `TestReadOnlyDeniedAcrossAllGuardedEndpoints` (24) — read-only-scoped
   actor rejected at all 24 access-scope-guarded endpoints, even with an
   explicit `permission_overrides` grant.
2. `TestAuthorizedActorClearsAuthLayer` (18 + 2 + 4 + 2 = 26) — authorized
   technician/tenant_owner clears the auth layer for execution (14+4),
   assignment-staff (2), and assignment-provider (4) endpoints, plus
   unauthenticated-401 and super_admin-exemption tests. Distinguishes
   guard-layer denial (`error_code == PERMISSION_DENIED`) from
   ownership-layer denial (`EXECUTION_STAFF_NOT_ASSIGNED`, accepted as
   proof of clearing the guard).
3. `TestUnauthorizedRoleRejected` (3) — customer rejected at execution and
   assignment-staff endpoints; staff rejected at assignment-provider
   endpoints (no delegation proven).
4. `TestPlatformAdminEndpointsUnaffected` (1) — source-inspection proof the
   3 admin endpoints kept their original permission gate.
5. `TestPlatformAdminActionsRetainAccess` (6) — `admin_operations` clears
   auth for all 3 admin endpoints; `tenant_owner` denied for all 3.
6. `TestShadowedRouteDecoratorsRemoved` (4) — functions preserved,
   decorators removed, OpenAPI has one operation per shared path, canonical
   implementation still answers live.
7. `TestPartsRequestBoundaryStillIntact` (2) — no Parts endpoint in
   `home_service_assignment`; install endpoint's guard swap confirmed
   consistent with the rest of the module.
8. `TestTenantDefenseInDepthAdded` (2) — service methods accept optional
   `tenant_id`; router passes it from the principal.

Plus 3 updates to `tests/test_phase2f_mutation_enforcement.py`:
- `test_execution_assignment_overlap_is_fully_resolved` (replaces the
  Slice 2F-3A version, now asserting zero overlaps instead of 2
  adjudicated ones).
- `test_execution_router_has_21_reachable_mutation_routes` (corrects the
  arithmetic: 23 mounted - 2 shadowed = 21, not the "20" miscounted in
  Slice 2F-3A's deferred summary).
- `test_all_three_execution_assignment_modules_have_zero_unverified_routes`
  (combined closure guard for all 27 reachable routes across all 3
  modules).

## Combined targeted regression run
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
tests/test_phase2f_mutation_enforcement.py ................. 11 passed (updated)
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 88 passed
tests/test_phase2f2_provider_portal_mutation_enforcement.py  53 passed
tests/test_phase2f3a_execution_assignment_overlap.py ....... 7 passed
tests/test_phase2f3b_execution_assignment_mutation_enforcement.py 68 passed (new)
tests/test_auth_login_fix.py
tests/test_final_l5_05p_tenant_provider_staff_permissions.py
tests/test_module_l5_01a_admin_finance_router_auth.py
tests/test_final_l5_01b_admin_tenant_rbac.py
────────────────────────────────────────────────────────────────
TOTAL: 532 passed, 0 failed, ~144s
```
Plus `tests/test_final_l5_05u_security_deposit_permission_authorization.py`
run separately: **29 passed, 0 failed** — the concurrency test flagged as
flaky in Slice 2F-3A's report did NOT reoccur this run (reported
separately per the mission's explicit instruction; it is timing-sensitive
and unrelated to this slice's changes either way).

Combined targeted total: **561 passed, 0 failed.**

## Broader partition (execution, assignment, ServiceJob, technician, provider, parts, quotes, auth)
```
tests/test_module_l5_16_quotes.py
tests/test_module_l5_21_quote_notify.py
tests/test_module_l5_36_staff_app_service_jobs.py
tests/test_quote_approval.py
tests/test_sprint20_job_assignment.py
tests/test_sprint22_quote_checklist.py
tests/test_staff_idor.py
tests/test_step6_job_assignment.py
tests/test_step8_quote_checklist.py
────────────────────────────────────────────────────────────────
316 passed, 3 skipped, 0 failed, ~186s
```
3 pre-existing skips, not investigated (unrelated to this slice).

**Not claimed as full-repository coverage** — 877 combined tests (561 + 316)
across the two runs, 0 failures.

## Live actions this slice
- Ran `inventory_mutation_routes.py --module` for all 3 modules before and
  after every guard change to confirm exact counts and guard_status
  transitions.
- Ran `--verify-module` individually for all 3 modules: all exit 0, 0
  unverified.
- Ran `--verify-overlap` across all 3 modules: exit 0, 0 overlaps (down
  from 2 before this slice).
- Confirmed `app.main` imports cleanly after every code change.
- Confirmed OpenAPI schema (`app.openapi()`) has exactly one operation for
  the shared accept/reject paths.

## Frontend
No frontend code was changed this slice.
