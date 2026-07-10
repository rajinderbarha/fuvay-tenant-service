# ADMIN-TENANT-E2E-09 — Browser Evidence Report

Evidence directory: `frontend/e2e-admin-tenant/evidence/e2e09/`

| Route | Role | Tenant Context Shown | Action | API Call Observed | Data Shown | Screenshot | Errors/request_id | Result |
|---|---|---|---|---|---|---|---|---|
| `/dashboard` | tenant_owner | "Demo AC Services" | page load | GET dashboard KPIs | Real KPI cards (skeleton→data) | `route_dashboard.png`, `dashboard-tenant-name.png` | none | PASS |
| `/tenant/setup/services` | tenant_owner | via nav sidebar | page load | `listAvailable`/`listEnabled` | AC Repair + other master services | `route_tenant_setup_services.png` | none | PASS |
| `/provider/service-coverage` | tenant_owner | via nav sidebar | page load | `listEnabled`, `getServiceAreas`, `providerStatusApi.get` | Coverage KPI cards, service grid | `route_provider_service-coverage.png`, `service-coverage-page.png` | none | PASS |
| `/setup/service-coverage` | tenant_owner | redirect | page load | (redirect, no independent call) | redirects to `/provider/service-coverage`, identical content | `route_setup_service-coverage.png` | none | PASS (confirms legacy redirect) |
| `/onboarding-status` | tenant_owner | via nav sidebar | page load | provider status API | onboarding status content | `route_onboarding-status.png` | none | PASS |
| `/provider/service-coverage` | tenant_readonly | via nav sidebar | page load (mutation buttons rendered but not clicked, to avoid destructive test on shared tenant) | same as owner | 15 Publish buttons rendered, no client-side role gating observed | `readonly-service-coverage.png` | none | PARTIAL — UI does not hide mutation actions for read-only role (see Read-Only Role Security report) |

Direct API evidence (non-screenshot, logged to `.log` files in the same directory):
- `type-brand-pricing.log` — proves Split AC+LG (700–850) vs Window AC+LG (420–490) are independently persisted.
- `price-range-validation.log` — proves min>max and below-floor are both rejected with 422 + real `error_code`/`request_id`.
- `readonly-security.log` — proves a `tenant.readonly` token reaches business-logic validation (422) rather than being blocked at 403, documenting the real access_scope gap.
- `route-smoke.log` — raw status/length log for every route hit this sprint (includes the one transient 404 retry, left in for transparency).

## Verdict: PASS — evidence captured for all in-scope routes and roles
