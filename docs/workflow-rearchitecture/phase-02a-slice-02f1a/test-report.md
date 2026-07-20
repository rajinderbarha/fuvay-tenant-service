# Test Report — Slice 2F-1A

## New tests this slice
`tests/test_phase2f1_tenant_engine_mutation_enforcement.py` gained 48 tests
(40 → 88 total in the file), across 2 new classes:

1. `TestFullNineteenEndpointAuthorizationMatrix` (46 tests) — Workstream 6:
   - `test_owner_accessible_endpoint_clears_auth_layer_for_owner` × 11 —
     each of the 11 `TENANT_OWNER_SELF_SERVICE` endpoints clears the auth
     layer for an authorized tenant_owner.
   - `test_owner_accessible_endpoint_rejects_cross_tenant` × 11 — each
     rejects a cross-tenant tenant_owner with 403.
   - `test_platform_only_endpoint_denies_owner_same_tenant` × 8 — each of
     the 8 `PLATFORM_ADMIN_ONLY` endpoints correctly denies a same-tenant
     tenant_owner (expected outcome, not a regression).
   - `test_platform_only_endpoint_denies_owner_cross_tenant` × 8 — same, for
     cross-tenant.
   - `test_platform_only_endpoint_super_admin_retains_access` × 8 — proves
     the classification correction did not lock out the actual, legitimate
     caller persona.
2. `TestNoTenantPortalExposureForPlatformOnlyActions` (2 tests) —
   Workstream 5: `frontend/tenant-portal/lib/api.ts` has zero references to
   any of the 8 platform-only path fragments; `frontend/super-admin/lib/api.ts`
   still has all 8 (regression guard against silently losing legitimate
   access).

Combined with Slice 2F-1's existing 40 tests, the file now has **88 tests**,
all passing.

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
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 88 passed (was 40)
tests/test_auth_login_fix.py
tests/test_final_l5_05p_tenant_provider_staff_permissions.py
tests/test_final_l5_05u_security_deposit_permission_authorization.py
tests/test_module_l5_01a_admin_finance_router_auth.py ...... (72 combined)
tests/test_final_l5_01b_admin_tenant_rbac.py ............... (included)
─────────────────────────────────────────────────────────────────
TOTAL: 430 passed, 0 failed, ~70s
```

## Broader partition (tenant lifecycle, onboarding, authentication, permission behavior)
Attempted per Workstream 8's instruction. Ran 14 additional test files
covering tenant management/governance, cross-tenant IDOR, canonical roles,
admin RBAC, role editors, in-page permissions, frontend permission guards,
tenant activation provisioning, enterprise-tenant flows, and onboarding
certification:
```
tests/test_admin_a3_tenant_management_provider_360.py
tests/test_admin_tenant_stabilization.py
tests/test_final_l5_05l_admin_roles.py
tests/test_final_l5_05m_frontend_permission_guards.py
tests/test_final_l5_05n_role_editor_repair.py
tests/test_final_l5_05o_inpage_permissions.py
tests/test_module_l5_01_tenant_cross_tenant_idor.py
tests/test_module_l5_01d_canonical_roles.py
tests/test_module_l5_02_tenant_detail_endpoints.py
tests/test_module_l5_02_tenant_governance.py
tests/test_module_l5_46_tenant_activation_provisioning.py
tests/test_p0_enterprise_tenants.py
tests/test_p0_provider_onboarding.py
tests/test_phase5_tenant_onboarding_certification.py
─────────────────────────────────────────────────────────────────
364 passed, 5 skipped, 0 failed, 206.33s
```
The 5 skips are pre-existing (not introduced this slice — not investigated
further, out of scope for a policy-closure slice with no code changes).

**Not claimed as full-repository coverage** — this is the same honest
disclosure pattern as every prior slice. The repository's total test count
is materially larger than the ~800 tests these two runs cover combined.

## Live actions this slice (beyond pytest)
- Re-ran `inventory_mutation_routes.py --module app.engines.tenant_engine.router`
  live against the running app to re-confirm the 27-endpoint dataset
  underlying the corrected classification (guard_status unchanged from
  Slice 2F-1, confirming no code drifted).
- Grepped `frontend/super-admin/lib/api.ts` and
  `frontend/tenant-portal/lib/api.ts` directly (not from memory) for all 8
  platform-only path fragments to build the frontend-exposure audit.
- Read `app/engines/tenant_engine/service.py` directly for all 8 disputed
  methods' actual implementation (not inferred from names) to build the
  sensitive-capability policy.

## Frontend
No frontend code was changed this slice — only read for audit purposes.
