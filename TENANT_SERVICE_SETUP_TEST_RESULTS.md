# Tenant Service Setup — Test Results

## TypeScript
`npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors, exit code 0**
(both before and after the Home-Services vertical-guard addition).

## Build
`npm run build`: Service Setup page compiles successfully. One pre-existing,
unrelated failure on `/service-jobs` (`EnterpriseDataGrid.tsx` Suspense
boundary issue, documented in prior sprints, confirmed untouched here).

## New certification tests
`pytest tests/test_tenant_service_setup_enterprise_wizard.py`: **23/23 passed.**
Covers: route wired into nav, breadcrumb, header actions, readiness hero
fields, catalog cards, enabled-services table columns, readiness issues
panel, all 10 wizard steps present, service step is read-only with no
free-text input, type/brand steps use real coverage APIs, issues step uses
the real (now-fixed) customer diagnostics API, options step uses the real
(now-fixed) provider service-option API, service-area step filters to active
areas only with an Add CTA, technician step filters to active staff with an
Add CTA, pricing step uses the backend resolver with no client-side price
math and correct payment-mode copy, availability step shows the missing
state with a CTA, review step has the full checklist plus ready/draft
messaging, Enable is disabled until ready with Save Draft available, no bare
"Unexpected error.", section errors show request_id, Home-Services vertical
guard present, 0 forbidden labels, both response_model bug fixes verified via
static inspection of the actual router source.

## Live evidence-based smoke test

Authenticated as `provider@serviceos.in` (tenant_owner, Demo AC Services):

```
GET /v1/provider/setup/services/{AC Repair id}/available-options → 200 (was 500, fixed)
GET /v1/provider/setup/services/{AC Repair id}/supported-options → 200 (was 500, fixed)
GET /v1/customer/catalog/issue-types?service_id={AC Repair id}   → 200 (was 500, fixed)
GET /v1/customer/catalog/service-options?service_id={AC Repair id} → 200 (was 500, fixed)
```

All 4 calls now return real, correctly-shaped data.

## Regression check

`pytest tests/test_tenant_service_setup_enterprise_wizard.py tests/test_home_services_only_bargain_scope.py tests/test_provider_first_matching_and_price_choice.py tests/test_bargain_customer_range_platform_fee.py tests/test_tenant_my_offerings_enterprise_ui.py tests/test_tenant_my_status_enterprise_ui.py`:
**126/126 passed** — 0 regressions across the full recent-sprint history.

## Forbidden label scan
0 matches in the Service Setup page — verified via test and manual grep.
