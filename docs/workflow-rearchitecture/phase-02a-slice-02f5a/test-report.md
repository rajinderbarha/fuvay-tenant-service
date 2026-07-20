# Test Report — Slice 2F-5A

## New tests this slice
`tests/test_phase2f5a_finance_persona_adjudication.py` — 13 tests across 6
classes:
1. `TestRuntimeRouteInventory` (2) — exact mounted mutation counts (20 for
   `package_commerce.admin_router`, 17 for `finance_hub.admin_router`).
2. `TestSecurityDepositDeprecatedStubsConfirmed` (4) — the 3 deposit stubs
   remain unconditional 410s naming `finance_hub` as canonical.
3. `TestPermissionBundleGaps` (2) — the exact set of permissions confirmed
   granted to no role (6 package + 10 finance) remain ungranted, and the 7
   `admin_finance`-granted permissions remain referenced — a regression
   guard against silent drift in either direction.
4. `TestPackagePurchaseSharedCanonicalService` (1) — both admin and tenant
   purchase paths call the identical service method.
5. `TestWalletDelegatesToCanonicalUsageCreditService` (3) — wallet
   endpoints still delegate to the canonical service and still require a
   reason for adjustments.
6. `TestNoFrontendTenantPortalCaller` (1) — tenant-portal has no caller for
   either module's admin paths.

## Combined targeted regression run (Slice 2F family)
```
tests/test_phase2f_mutation_enforcement.py ................. 11 passed
tests/test_phase2f1_tenant_engine_mutation_enforcement.py .. 88 passed
tests/test_phase2f2_provider_portal_mutation_enforcement.py  53 passed
tests/test_phase2f3a_execution_assignment_overlap.py ....... 7 passed
tests/test_phase2f3b_execution_assignment_mutation_enforcement.py 68 passed
tests/test_phase2f4_tenant_portal_mutation_enforcement.py .. 35 passed
tests/test_phase2f5a_finance_persona_adjudication.py ....... 13 passed (new)
tests/test_phase2d_tenant_access_model.py .................. 18 passed
────────────────────────────────────────────────────────────────
293 passed, 0 failed
```

## Broader finance-related partition
```
tests/test_final_l5_05j_usage_credit_service.py
tests/test_final_l5_05u_security_deposit_permission_authorization.py
tests/test_finance_package_pricing_fix.py
tests/test_hs9b_finance_review_low_credit.py
tests/test_module_l5_01a_admin_finance_router_auth.py
tests/test_module_l5_10_category_commission.py
tests/test_module_l5_10_commission_reversal.py
tests/test_module_l5_10_deposit_refund.py
tests/test_module_l5_10_finance_reporting.py
tests/test_module_l5_10_ledger_amount_guard.py
tests/test_module_l5_10_offline_deposit.py
tests/test_module_l5_17_credits.py
tests/test_module_l5_28_credit_checkout.py
tests/test_module_l5_30_package_purchase.py
tests/test_module_l5_32_package_commission_deadmodel.py
tests/test_module_l5_45_package_activation_limits.py
tests/test_p0_customer_service_credit.py
tests/test_p0_finance_enterprise.py
tests/test_p0_job_completion_credit_deduction.py
tests/test_phase4_finance_certification.py
tests/test_sprint5_packages.py
tests/test_sprint_p0_packages.py
tests/test_sprint_p1_package_approval.py
────────────────────────────────────────────────────────────────
614 passed, 4 skipped, 0 failed
```
4 pre-existing skips, not investigated (unrelated to this slice — no code
was changed this slice, so these were not newly introduced).

**Not claimed as full-repository coverage** — 293 + 614 = 907 combined
tests, 0 real failures.

## Live actions this slice
- Ran `inventory_mutation_routes.py --module` for both modules to build
  the exact 20 + 17 route dataset.
- Grepped `app/core/permissions.py` directly for every `P.PACKAGES_*` and
  `P.FINANCE_PAYOUTS_*`/`P.FINANCE_CLAIMS_*` reference to confirm the
  permission-bundle gap (zero grants beyond the definition line).
- Grepped `frontend/super-admin/lib/api.ts` (53 matches) and
  `frontend/tenant-portal/lib/api.ts` (2 irrelevant matches) for every
  path fragment in both modules.
- Traced `admin_purchase_package`/`tenant_purchase_package` to confirm
  they call the identical `create_package_assignment` service method.

## Frontend / code
No frontend or application code was changed this slice — this was a
read-only adjudication.
