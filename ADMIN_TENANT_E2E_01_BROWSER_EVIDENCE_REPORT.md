# ADMIN_TENANT_E2E_01 — Browser Evidence Report

All evidence at `frontend/e2e-admin-tenant/evidence/`.

| Route | Role | Loaded | API calls observed | Main data shown | Screenshot | Errors/request_id |
|---|---|---|---|---|---|---|
| /login → /admin/dashboard | Super Admin | yes | POST /v1/auth/login + dashboard data calls | admin dashboard KPIs | admin-login-dashboard.png | none |
| /admin/dashboard | Super Admin | yes | dashboard data | KPI cards | _admin_dashboard.png | none |
| /admin/tenants | Super Admin | yes | tenants list | tenant table | _admin_tenants.png | none |
| /admin/home-services/service-catalog | Super Admin | yes | catalog summary | Command Center tour + summary cards (15 services, missing types/brands counts) | _admin_home-services_service-catalog.png | none |
| /admin/home-services/pricing-rules | Super Admin | yes | pricing rules list | — | _admin_home-services_pricing-rules.png | none |
| /admin/finance/usage-credits | Super Admin | yes (slow ~51s first compile) | usage credits list | — | _admin_finance_usage-credits.png | none |
| /login → /dashboard | Tenant Owner | yes | POST /v1/auth/login + /v1/tenant/dashboard/runtime | tenant name "Demo AC Services", KPI cards, setup readiness 8/8 | tenant-login-dashboard.png | none (bug found+fixed, see TENANT_LOGIN report) |
| /dashboard | Tenant Owner | yes | runtime + provider status | dashboard | tenant_dashboard.png | none |
| /provider/status | Tenant Owner | yes | checklist data | setup checklist | tenant_provider_status.png | none |
| /tenant/setup/services | Tenant Owner | yes | services data | service setup | tenant_tenant_setup_services.png | none |
| /provider/service-coverage | Tenant Owner | yes | coverage data | coverage | tenant_provider_service-coverage.png | none |
| /provider/service-areas | Tenant Owner | yes | areas data | service areas | tenant_provider_service-areas.png | none |
| /provider/availability | Tenant Owner | yes | availability data | availability | tenant_provider_availability.png | none |
| /jobs | Tenant Owner | yes | jobs data | jobs list | tenant_jobs.png | none |
| /finance/usage-credit-ledger | Tenant Owner | yes | ledger data | usage credit ledger | tenant_finance_usage-credit-ledger.png | none |
| /login → /dashboard | Tenant Read Only | yes | POST /v1/auth/login | dashboard (no UI distinction) | tenant-readonly-login.png | none |
| PUT /v1/provider/business-profile (API, no UI) | Tenant Read Only | n/a | direct API call | mutation succeeded (200) — real gap, see READONLY report | n/a (JSON: readonly-mutation-attempt.json) | request_id present, status 200 (not 403 — the gap itself) |

Raw request logs: `admin-login-requests.json`, `tenant-login-requests.json`.
Raw route-smoke logs: `admin-route-smoke.log`, `tenant-route-smoke.log`.

## Result
Full evidence trail captured for every route tested in Parts 6, 7, 8, 9, 10.
