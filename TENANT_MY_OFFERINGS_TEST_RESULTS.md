# Tenant My Offerings — Test Results

## TypeScript
`npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors, exit code 0.**

## Build
`npm run build`: My Offerings page and all new `lib/api.ts` additions compile successfully. One
pre-existing, unrelated failure on `/service-jobs` (documented in prior sprints, confirmed
untouched here).

## Lint / `npm test`
No ESLint config and no `test` script exist in `frontend/tenant-portal` (pre-existing, documented
in prior sprints).

## New certification tests
`pytest tests/test_tenant_my_offerings_enterprise_ui.py`: **22/22 passed.** Covers: catalog
query uses `master_services` not the empty legacy table, `ON CONFLICT` fix, alias fix (6 call
sites), new issue-mapping endpoint, header/breadcrumb, hero, 8 KPI cards, empty-state upgrade,
4 tabs with "Unavailable" (not `0`) on failure, error states with request_id, wizard uses real
catalog endpoints, service-area/technician panels, no client-side price calculation, no
free-text service creation, duplicate-offering guard, permission-aware Enable action, 0
forbidden labels, activity timeline.

## Regression check
`pytest tests/test_phase7_staff_app_certification.py tests/test_phase7b_staff_frontend_certification.py tests/test_tenant_my_status_enterprise_ui.py`:
**57/57 passed** — confirms this sprint's backend changes (offerings query rewrite, ON CONFLICT
fix, alias fixes, new issues endpoint) introduced no regression to prior-phase certified
surfaces.

## Live evidence-based smoke test (hard gate)

```
GET  /v1/provider/offerings/available                        → 200, 15 offerings incl. AC Repair
GET  /v1/provider/offerings/enabled                            → 200
POST /v1/provider/offerings/enabled {AC Repair}                 → 200 (was 500, fixed)
GET  /v1/provider/offerings/enabled/{id}                        → 200, provider_enabled_offering_id present
GET  /v1/admin/master-services/{AC Repair id}/types             → 200, Split AC + Window AC
GET  /v1/admin/master-services/{AC Repair id}/brands            → 200, LG + Samsung + Voltas
GET  /v1/admin/master-services/{AC Repair id}/issues            → 200, 8 mappings incl. AC Not Cooling
GET  /v1/catalog/master/service-options?master_service_id=...   → 200, Gas Refill + Emergency Visit
POST /v1/pricing/tenants/{id}/price-preview {Split AC, Ludhiana} → 200, real ₹50 tier_3 floor price
```

**Hard gate satisfied**: AC Repair exists in the platform catalog and appears as an available
offering for the certified tenant.

## Forbidden label scan
0 matches across `page.tsx` — verified via test and manual grep.
