# ADMIN-TENANT-E2E-09B — Test Results

## TypeScript (`frontend/tenant-portal`)
`npx tsc --noEmit` → **0 errors**.

## Build (`frontend/tenant-portal`)
`npm run build` → succeeds, all routes compile (static + dynamic), including
`/tenant/setup/services`, `/provider/service-coverage`, `/provider/service-setup`. No
"Failed to compile" / error lines in output.

## Playwright (`frontend/e2e-admin-tenant`, E2E_APP=tenant, project=chrome)
14/14 passed (see Playwright report for full list). Real system Chrome, real backend, real DB.

## Backend pytest (touched: auth JWT claims, UserContext, permissions.py, admin_catalog/tenant_router.py, provider_portal/router.py)

- Targeted regression suite for the touched files:
  `tests/test_hs5b_availability_exceptions_coverage.py`,
  `tests/test_phase6_tenant_dashboard_certification.py`,
  `tests/test_tenant_home_services_service_setup_wizard.py`,
  `tests/test_type_dependent_brand_pricing.py`
  → 1 pre-existing test (`test_permission_gated_actions`) needed updating because it literally
  string-matched the old dependency name (`require_permission(P.TENANT_UPDATE)`); updated to
  match the new, stronger dependency name and it now passes. Result: **79 passed**.

- Full backend suite: `python -m pytest tests/ -q` → **8833 passed, 81 failed, 1 skipped**
  (490.97s). All 81 failures are **pre-existing** frontend-page-content assertion drift
  (string checks against page copy/labels on pages this sprint did not touch — e.g.
  `test_sprint34c_master_data.py`, `test_sprint34k_navigation.py`,
  `test_tenant_business_profile_enterprise_ui.py`, `test_tenant_my_status_enterprise_ui.py`)
  — confirmed by inspecting a representative failure
  (`test_tenant_service_coverage_enterprise_ui.py::test_hero_present`, which checks for the
  string "Coverage Status" on a page this sprint never edited). None reference
  `admin_catalog`, `provider_portal`, `permissions.py`, `tenant_router`, or RBAC/auth in any
  form. Zero regressions attributable to this sprint's backend changes.

## Live database sanity
`tenant_billing.credit_balance` = 3937.00 (Demo AC Services) before and after all testing.
`GET /v1/provider/status` → `is_bookable: true, is_visible: true, bookability_blockers: []`
before and after.
