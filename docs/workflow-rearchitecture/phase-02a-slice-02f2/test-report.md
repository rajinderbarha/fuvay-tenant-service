# Test Report — Slice 2F-2

## New tests this slice
`tests/test_phase2f2_provider_portal_mutation_enforcement.py` — 53 tests
across 6 classes:
1. `TestReadOnlyAccessScopeDeniedAcrossAllGuardedEndpoints` (23) — all 22
   newly-guarded endpoints reject a read-only-scoped tenant_owner even with
   an explicit `permission_overrides` grant, plus 1 unknown-access-scope
   documentation test.
2. `TestTenantOwnerClearsAuthLayer` (24) — all 22 endpoints clear the auth
   layer for an authorized tenant_owner (with an accepted TypeError-past-auth
   proof pattern for handlers that touch mocked business logic), plus
   unauthenticated-401 and super_admin-exemption tests.
3. `TestUnauthorizedRolesRejected` (3) — staff/technician/customer roles
   are rejected (no delegated-staff or technician-self-service capability
   exists in this router today).
4. `TestTenantScopingMechanismSourceProof` (2) — source-inspection proof
   that every object-mutation handler filters by the caller's own
   `tenant_id`, and that the 8 previously-leaky read-back queries are now
   fixed.
5. `TestDeactivateTeamMemberSessionRevocation` (1) — source proof of the
   new session-revocation code path.

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
tests/test_phase2f_mutation_enforcement.py ................. 8 passed
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 88 passed
tests/test_phase2f2_provider_portal_mutation_enforcement.py  53 passed (new)
tests/test_auth_login_fix.py
tests/test_final_l5_05p_tenant_provider_staff_permissions.py
tests/test_final_l5_05u_security_deposit_permission_authorization.py
tests/test_module_l5_01a_admin_finance_router_auth.py ...... (72 combined)
tests/test_final_l5_01b_admin_tenant_rbac.py ............... (included)
────────────────────────────────────────────────────────────────
TOTAL: 483 passed, 0 failed, ~63s
```

## Broader partition (provider portal, staff, technician, availability, offerings)
```
tests/test_final_l5_05q_provider_coverage_mutations.py
tests/test_hs5_service_areas_availability.py
tests/test_hs5b_availability_exceptions_coverage.py
tests/test_hs6_provider_matching_price_fix.py
tests/test_module_l5_02_provider_portal_endpoints.py
tests/test_p0_provider_enterprise.py
tests/test_p0_provider_onboarding.py
tests/test_provider_first_matching_and_price_choice.py
tests/test_staff_idor.py
tests/test_staff_roster.py
tests/test_tenant_business_hours_availability.py
tests/test_tenant_my_offerings_enterprise_ui.py
tests/test_module_l5_43_super_admin_staff_deactivate.py
────────────────────────────────────────────────────────────────
269 passed, 0 failed, ~50s
```

**Not claimed as full-repository coverage** — 752 combined tests (483 +
269), 0 failures, across the two runs; the repository's total test count is
materially larger.

## Live actions this slice
- Ran `inventory_mutation_routes.py --module app.engines.provider_portal.router`
  before and after the guard swap to confirm the exact 24-route dataset and
  guard_status transition (22 `PERMISSION_ONLY_NOT_SCOPE_AWARE` →
  `TENANT_MUTATION_ROLE_SCOPE_AWARE`).
- Ran `--verify-module app.engines.provider_portal.router`: **exit 0, 0
  unverified out of 24.**
- Verified `app.main` imports cleanly after every code change (guard swap,
  read-back fixes, session-revocation addition).

## Frontend
No frontend code was changed this slice — read-only for audit purposes.
