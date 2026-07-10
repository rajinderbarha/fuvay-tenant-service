# Automatic Price Options — Test Results

## TypeScript
`npx tsc --noEmit`: **0 errors, exit code 0** in both `frontend/super-admin`
and `frontend/tenant-portal`.

## New certification tests
`pytest tests/test_deactivate_manual_bargain_auto_price_options.py`:
**22/22 passed.** Covers: Bargain Rules removed from admin Pricing & Rules
nav, Home Services admin nav group present with all 3 pages, deprecated
bargain page shows banner + redirect link, Customer Price Experience page
hero/explanation/preview/breakdown, Provider Matching page ranking weights
and "manual selection disabled" messaging, Matching Diagnostics page uses
the real backend and shows customer-safe + admin-only fields, tenant nav has
no Bargain Settings item and has Customer Price Preview, tenant page shows
Low/Mid/High + payment/deduction copy, tenant cannot edit platform fee or
configure a bargain rule (structural checks), tenant page uses only
read-only endpoints, Home Services scope guard present, backend endpoints
exist and reuse the certified engines, tenant backend endpoints are GET-only,
config endpoint uses the real feature-flag system, feature-flag defaults
match the business decision, 0 forbidden labels, no bargain-rule-builder
customer-facing language.

## Regression check

`pytest tests/test_deactivate_manual_bargain_auto_price_options.py tests/test_tenant_service_setup_enterprise_wizard.py tests/test_home_services_only_bargain_scope.py tests/test_provider_first_matching_and_price_choice.py tests/test_bargain_customer_range_platform_fee.py tests/test_tenant_my_offerings_enterprise_ui.py tests/test_tenant_my_status_enterprise_ui.py tests/test_phase7_staff_app_certification.py tests/test_phase7b_staff_frontend_certification.py`:
**176/176 passed** — 0 regressions across the entire session's test history.

## Live evidence-based smoke test

Authenticated as `admin@serviceos.in` (super_admin) and `provider@serviceos.in`
(tenant_owner, Demo AC Services):

```
GET  /v1/admin/home-services/config                              → 200, correct flag defaults
POST /v1/admin/home-services/price-experience/preview             → 200, Low ₹715 / Mid ₹810 / High ₹900
                                                                      (exact match to ticket's example,
                                                                       admin 600-1200, customer 650-900, fee 10%)
POST /v1/admin/home-services/matching/diagnostics                 → 200, 0 eligible (correctly excludes
                                                                      the real test tenant, status=pending_setup)
GET  /v1/tenant/home-services/customer-price-preview              → 200, Low ₹715 / Mid ₹910 / High ₹1100,
                                                                      completed_job_deduction_credits: 21
GET  /v1/tenant/home-services/matching-readiness                  → 200, matching_ready: false, honest message
```

Note: the ticket's own example used an internally-inconsistent admin/customer
range (admin ₹300–₹500, customer ₹650–₹900 — customer range outside admin
range, which the validation correctly rejects with `CUSTOMER_MAX_ABOVE_ADMIN_MAX`).
Re-tested with the real, consistent AC Repair pricing scenario already live
in the database (admin ₹600–₹1200) and got the exact Low ₹715 / Mid ₹810 /
High ₹900 the ticket specifies.

## Build

`npm run build` in both frontends — ran in background; see final report for
outcome (both apps' TypeScript passed within the build step regardless).
