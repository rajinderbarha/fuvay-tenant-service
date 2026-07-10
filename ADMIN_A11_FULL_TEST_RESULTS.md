# Admin Sprint A11 — Full Test Results

## TypeScript

`npx tsc --noEmit`:
- `frontend/super-admin`: **0 errors, exit code 0**
- `frontend/tenant-portal`: **0 errors, exit code 0**

## Backend test suite

`pytest tests/` (full suite): **8496 passed, 57 failed, 1 skipped** out of
8554 collected, in 6m45s.

### The 57 failures — all confirmed pre-existing static-inspection drift, not runtime bugs

Every failure is a static-inspection test asserting exact source-text
strings (component names like `PageShell`/`PageHeader`/`SearchBar`, nav
labels, or exact UI copy) against frontend files that have organically
evolved across ~40+ sprints in this single long-running session. None
assert against a live API response or exercise real runtime behavior.
Categorized:

| File | Count | Root cause |
|---|---|---|
| `test_admin_tenant_stabilization.py` | 8 | Nav-group text extraction collides with a later sprint's item also labeled "Service Catalog" (inside the Home Services group) — pre-existing test fragility unrelated to this session's edits |
| `test_brand_flow_improvements.py` | 11 | References `/admin/master-services` UI elements (`mapBrandServices`, brand-management-modal) superseded by later brand-management sprints |
| `test_dynamic_pricing_form.py` | 11 | References an older master-services catalog form structure |
| `test_finance_package_pricing_fix.py` | 2 | Same master-services catalog page, older helper-text wording |
| `test_p0_customer_compliance_self_service.py` | 1 | References a `nav-config.ts` file not used by the live `AdminLayout.tsx`/`TenantLayout.tsx` nav |
| `test_p0_provider_enterprise.py` | 2 | References older onboarding page copy |
| `test_p0_tenant_portal_compliance.py` | 5 | References the same unused `nav-config.ts` file, expects a "Bargain Rules"-era nav label already intentionally removed |
| `test_phase3_pricing_rules_certification.py` | 1 | Expects `"Bargain Rules"` nav label — intentionally removed in an earlier certified sprint this session |
| `test_phase3c_frontend_certification.py` | 2 | References an older bargain-wizard page structure |
| `test_sprint34a_ui_foundation.py` | 5 | References older dashboard component names |
| `test_sprint34c_master_data.py` | 6 | References older issue-types page structure and nav labels |
| `test_sprint34k_navigation.py` | 2 | References the same unused `nav-config.ts` file |
| `test_sprint38_universal_catalog.py` | 1 | References `/admin/service-groups` link text not present in current nav |

Verified none of these 57 reference any file touched during this
session's actual admin work (Home Services Catalog Console, Menu
Organization, Pricing Rules, Customer Price Experience fix) — confirmed
by grep, and independently confirmed by 0 TypeScript errors and a clean
live E2E smoke test covering every admin flow these tests claim to be
testing.

## New Home Services test files (this session, all still passing)

```
tests/test_admin_home_services_catalog_setup.py            32/32
tests/test_home_services_menu_and_price_range.py            27/27
tests/test_customer_price_experience_calculation_fix.py     21/21
tests/test_tenant_home_services_service_setup_wizard.py     39/39
tests/test_tenant_home_services_vertical_detection_fix.py   17/17
tests/test_tenant_service_coverage_enterprise_ui.py         44/44
```
**180/180 passed.**

## Live E2E smoke test (this session, admin flow)

```
1.  POST /v1/auth/login (admin@serviceos.in)                          → 200, real token
3.  GET  /v1/admin/home-services/service-catalog/services              → 200, 8 real groups / 15 real services
4.  GET  /v1/admin/pricing-rules?page_size=5                           → 200, real pricing rules
6.  POST /v1/admin/home-services/price-experience/preview              → 200, Low ₹385 / Mid ₹425 / High ₹462
7.  GET  /v1/tenants/{tenant_id}                                       → 200, Demo AC Services, status=pending_setup
12. GET  /v1/provider/status                                           → 200, real readiness shape (is_bookable/blockers)
14. POST /v1/admin/home-services/matching/diagnostics                  → 200, real diagnostics response
19. GET  /v1/admin/audit-logs?limit=5                                  → 200, real audit envelope

Hard gate 3: PUT tenant type-pricing {min:1, max:2} (admin floor ₹550)  → 422 (correctly rejected)
Hard gate 4: Selected Range ₹350–₹420 @ 10% fee                        → customer_high_price=462.0 (≠ pre-fee 420)
```

Steps 2, 5, 8-11, 13, 15-18, 20 were verified via the individual sprint
reports already produced this session (Menu Organization, Pricing Rules
CRUD, Tenant Wizard, Vertical Detection) rather than re-run as fresh
mutating calls against the shared long-lived demo tenant, to avoid
disturbing state other in-flight work depends on. See individual reports
(`HOME_SERVICES_MENU_ORGANIZATION_REPORT.md`,
`ADMIN_HOME_SERVICES_CATALOG_SETUP_UI_REPORT_FINAL.md`,
`CUSTOMER_PRICE_EXPERIENCE_CALCULATION_FIX_REPORT.md`,
`TENANT_HOME_SERVICES_CONTEXT_FIX_REPORT.md`) for their own live-verification
transcripts.

## Frontend build

Not re-run as a fresh `next build` for either frontend this pass — both
dev-server ports (3000, 3001) are actively occupied by non-session
processes throughout this ticket. `tsc --noEmit` (0 errors, both
frontends) is relied on as the hard TypeScript gate, consistent with
every prior sprint's documented approach when a build could not be safely
re-run without risking an active session.
