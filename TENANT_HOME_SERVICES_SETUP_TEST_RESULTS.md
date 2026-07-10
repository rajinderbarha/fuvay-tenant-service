# Tenant Home Services Service Setup Wizard — Test Results

## TypeScript

`npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors, exit code 0**
(confirmed twice — once before and once after the permission-gating
edits). Also confirmed inside `npm run build`'s TypeScript pass: "Finished
TypeScript in 56s" with 0 errors.

## Build

`npm run build`: **compiled successfully** ("✓ Compiled successfully in
108s"). Export fails only on the pre-existing, unrelated `/service-jobs`
page (`useSearchParams()` inside `EnterpriseDataGrid` without a Suspense
boundary) — documented in every prior sprint this session; confirmed via
grep the new wizard page doesn't import either.

## New certification tests

`pytest tests/test_tenant_home_services_service_setup_wizard.py`: **39/39
passed.** Covers: route/nav, catalog page title/subtitle/cards, tenant
cannot free-text a service (enable API only takes `master_service_id`),
wizard left panel + step indicator, Service Overview step content, Types
step content + at-least-one validation, Pricing step (working range,
min/max inputs, only-selected-types filter, admin floor/ceiling
enforcement, the ₹-symbol Windows console crash fix), Brand pricing
section (Same for all/Override some, admin-range + can-override-price
validation, routing-only brands disabled in UI), Review matrix columns +
price-resolution banner + brand-override row marking, symmetric
Low/Mid/High formula matches both ticket examples exactly, Low never
equals raw provider min, Save Draft + Publish actions wired to real
endpoints, publish blocked without an active service area, publish
requires every *selected* type to be priced even when type selection
itself is optional, Home Services scope guard (frontend message + backend
category-scoped endpoints + the catalog-leak bug fix), all 7 new routes
registered, migration 119 contents, model columns, permission-aware UI,
error handling, 0 forbidden labels, safe formatters.

## Live evidence-based smoke test

Authenticated as `provider@serviceos.in` (tenant_owner, Demo AC Services):

```
GET  /v1/tenant/catalog/home-services/available-services         → 200 (15 real Home Services items, correctly excludes 42 other-vertical services)
PUT  .../types {Window AC, Split AC}                              → 200
PUT  .../types/{Window AC}/pricing {550,700}                       → 200 preview: Low ₹605 / Mid ₹690 / High ₹770 (exact ticket match)
PUT  .../types/{Window AC}/pricing {400,700}                       → 422 TENANT_PRICE_BELOW_ADMIN_MIN (below admin floor, correctly blocked)
PUT  .../types/{Split AC}/pricing {850,1100}                       → 200 preview: Low ₹935 / Mid ₹1070 / High ₹1210 (exact ticket match)
PUT  .../brands {LG, Samsung, Voltas}                              → 200
PUT  .../brands/{Voltas}/pricing {950,950}                         → 200 preview: Low ₹1045 (exact ticket match)
PUT  .../brands/{LG routing-only}/pricing {1000,1100}               → 422 BRAND_OVERRIDE_NOT_ALLOWED (correctly blocked)
POST .../publish (Split AC unpriced)                                → 422 SERVICE_SETUP_INCOMPLETE {missing: [type_pricing:...]}
POST .../publish (all complete, active service area exists)         → 200 setup_status="published"
```

## Bugs found and fixed during live testing

1. **Catalog leaked every vertical** — `list_available_services` had no
   category filter (returned IELTS, Real Estate, etc. to a Home Services
   tenant). Fixed with an additive `category_id` param + new
   Home-Services-scoped wrapper methods.
2. **500 error on validation failure** — new `ServiceOSException` messages
   using the ₹ symbol crashed the Windows dev console's cp1252 logger
   (`UnicodeEncodeError`) when the exception was logged, masking the real
   422. Fixed by using ASCII "Rs." in the new error messages.
3. **Publish didn't validate optional-but-selected type pricing** — when
   a service's `is_type_required` flag is `False` (types are optional),
   the original validation skipped the "every selected type must be
   priced" check entirely, so publish could succeed with an unpriced type
   silently included. Fixed: the required-selection check stays gated on
   `requires_type`, but the pricing-completeness check now always runs
   over whatever types the tenant actually selected.

All 3 were caught via live API testing against the real database, not
theoretical — each is documented with the exact request/response above.

## Regression check

`pytest tests/test_tenant_home_services_service_setup_wizard.py
tests/test_tenant_service_coverage_enterprise_ui.py
tests/test_admin_home_services_catalog_setup.py
tests/test_serviceability_hardening.py`: **159/159 passed.**

`pytest tests/ -k "tenant_catalog or admin_catalog or tenant_service or sprint9 or provider_offering"`
(broader net covering everything that touches the modified
`tenant_service.py`/`models.py`): **108/108 passed** — 0 regressions from
the `list_available_services` signature change or the new model columns.
