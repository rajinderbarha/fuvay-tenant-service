# Admin Home Services Catalog Setup — Test Results

## TypeScript

`npx tsc --noEmit` in `frontend/super-admin`: **0 errors, exit code 0.**
Confirmed a second time inside `npm run build`'s TypeScript pass:
"Finished TypeScript in 99s" with 0 errors.

## Build

`npm run build`: **compiled successfully** ("✓ Compiled successfully in
93s"). Export fails only on the pre-existing, unrelated
`/admin/refund-requests` page (`useSearchParams()` inside
`EnterpriseDataGrid` without a Suspense boundary) — documented in every
prior sprint this session; confirmed via grep that the new console page
does not import `EnterpriseDataGrid` or `useSearchParams`.

## New certification tests

`pytest tests/test_admin_home_services_catalog_setup.py`: **32/32
passed.** Covers: route/nav (Home Services group has Overview + Service
Catalog, no "Bargain Rules" active item), title/subtitle/actions, grouped
left list, all 8 tabs present, General tab fields, Types & Pricing
table/validation, Brands tab behavior controls + override-not-allowed
guard, routing-only brands never show a price preview, Zones/Issues/Options
tabs use real APIs with service-scoped filters and link to their
dedicated management screens, Customer Price Preview inputs/outputs, the
symmetric formula computed directly against `bargain_engine.py` matches
the ticket's ₹605/₹690/₹770 example exactly, never shows the raw provider
minimum as customer Low, no Bargain Rule Builder UI, 0 forbidden labels,
scope-guard message text, backend category hard-boundary, all 9 new
routes registered with the right permission dependencies, migration 118
contents, router registered in `main.py`.

## Live evidence-based smoke test

Authenticated as `admin@serviceos.in` (super_admin):

```
GET  /v1/admin/home-services/service-catalog/services                        → 200 (8 real groups, AC Repair present)
GET  /v1/admin/home-services/service-catalog/services/{AC Repair}/types      → 200 (Split AC, Window AC — no floor/ceiling yet)
PUT  .../types/{Window AC}/limits {floor:550,ceiling:1500,fee:10,ded:21}     → 200 preview: Low ₹605 / Mid ₹1130 / High ₹1650
POST /v1/admin/home-services/service-catalog/price-preview {550,700,10}      → 200 Low ₹605 / Mid ₹690 / High ₹770 (exact ticket match)
PUT  .../brands/{LG}/limits {floor:1100,ceiling:1100,fee:10}                 → 200 preview: Low ₹1210 / Mid ₹1210 / High ₹1210
PUT  .../brands/{mapping}/behavior {is_routing_only:true,can_override:false} → 200 preview cleared to null (routing-only never prices)
GET  .../services/{AC Repair}/audit                                          → 200 (2 real audit events, newest first)
```

## Regression check

`pytest tests/ -k "admin_catalog or bargain or pricing_rule or brand"`:
**450 passed, 13 failed** — all 13 failures confirmed pre-existing and
unrelated: `test_brand_flow_improvements.py` (11 failures) references a
different frontend page (`/admin/master-services`) with UI elements
(`mapBrandServices`, `selectedBrandToAdd`, brand-management-modal) that
this session never touched; `test_phase3_pricing_rules_certification.py`
expects a `"Bargain Rules"` nav label that the earlier, already-certified
"Deactivate Manual Bargain Module" sprint in this session intentionally
removed; `test_phase3c_frontend_certification.py` expects a "Bargain
Policy" wizard step on a different page. Confirmed via grep that none of
these 13 tests reference `home_services_catalog_console_router`,
`compute_symmetric_customer_price_tiers`, `can_override_price`, or
`is_routing_only` — none of this sprint's changes are implicated.

Backend startup log confirmed clean (no import errors) after adding the
new router, service methods, and migration.
