# Tenant Service Coverage Areas — Test Results

## TypeScript

`npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors, exit code 0.**
(Also confirmed a second time as part of `npm run build`'s TypeScript pass:
"Finished TypeScript in 64s" with 0 errors.)

## Build

`npm run build`: **compiled successfully** ("✓ Compiled successfully in
68s"). Export fails only on the pre-existing, unrelated `/service-jobs`
page (`useSearchParams()` inside `EnterpriseDataGrid` without a Suspense
boundary) — documented in every prior sprint this session; confirmed via
grep that no file touched this sprint imports `EnterpriseDataGrid` or
`useSearchParams`.

## New certification tests

`pytest tests/test_tenant_service_coverage_enterprise_ui.py`: **44/44
passed.** Covers: route/sidebar (including the new "Coverage" nav group),
breadcrumb, header actions, hero (status/badge states, meta chips),
circular slots-used ring (not hardcoded), KPI cards, Action Required panel
text, table columns/search/tabs/footer, "Not configured" fallback (never a
bare dash), row actions (View/Edit/Set Primary/Delete), Add Service Area
drawer (subtitle, area-type selector with no "online" option, Validation
Preview), real pincode-141001-resolves-to-Ludhiana/Tier-2 lookup table,
real duplicate-check and package-limit-check wiring, edit-drawer pincode
immutability hint, Detail drawer's 4 sections, Delete confirmation
(bookability warning + last-active-area escalation), Set Primary
confirmation modal + real endpoint wiring, backend CRUD/limits/validate/
set-primary routes exist, PUT (not PATCH) on update, `id` field (not
`area_id`) matching the real backend, migration 117 contents, permission
gating, SectionError request-id/retry, no bare "Unexpected error", 2
responsive breakpoints, 0 forbidden labels, safe formatters present.

## Live evidence-based smoke test

Authenticated as `provider@serviceos.in` (tenant_owner, Demo AC Services,
tenant `34b427a7-b2be-496c-b826-6d51bb181248`):

```
GET  /v1/tenant/service-areas                                 → 200 (1 real area: 141001/Ludhiana/Punjab, is_primary=true)
GET  /v1/tenant/service-areas/limits                           → 200 {"max_service_areas":5,"used_service_areas":1,"remaining_service_areas":4}
POST /v1/tenant/service-areas/validate {zipcode:"141001", ...} → 200 resolved_city="Ludhiana", resolved_zone_tier="tier_2", is_duplicate=true (correct — already exists)
POST /v1/tenant/service-areas/validate {zipcode:"141002", ...} → 200 resolved_city="Ludhiana", resolved_zone_tier="tier_2", is_duplicate=false, serviceable=true,
                                                                       bookability_impact="This area can receive Home Services bookings."
POST /v1/tenant/service-areas/{id}/set-primary                  → 200 is_primary=true
POST /v1/tenant/service-areas {zipcode:"141002", ...}            → 201, then GET limits → used=2/5, remaining=3
DELETE /v1/tenant/service-areas/{new_id}                         → 200 deactivated=true, then GET limits → back to used=1/5, remaining=4
```

The 141001 → Ludhiana / Tier 2 resolution matches the ticket's example
exactly, using real, live data (not mocked).

## Regression check

`pytest tests/test_tenant_service_coverage_enterprise_ui.py
tests/test_tenant_business_profile_enterprise_ui.py
tests/test_deactivate_manual_bargain_auto_price_options.py
tests/test_home_services_only_bargain_scope.py
tests/test_provider_first_matching_and_price_choice.py
tests/test_bargain_customer_range_platform_fee.py
tests/test_tenant_my_offerings_enterprise_ui.py
tests/test_tenant_my_status_enterprise_ui.py`: **197/197 passed.**

`pytest tests/test_serviceability_hardening.py` (full pre-existing
serviceability suite): **44/44 passed** after fixing 2 test-mock setups
(`test_12_create_service_area_city_coverage_success`,
`test_20_create_service_area_persists_zone_id`) that only mocked a single
`db.execute` return value — my new real limit-check inside
`create_service_area` now issues an additional query, so those 2 mocks
needed a second `scalar_one=0` value added. This is a mock-setup fix, not
a product bug; confirmed by the fact the identical flow works correctly
against the real database (see smoke test above).

`pytest tests/ -k "serviceability or service_area or tenant_engine"`
(broader net): **105/107 passed before the mock fix, 107/107 after.**
