# ADMIN-TENANT-E2E-09 — Type-Specific Brand Pricing Report (CRITICAL — PROVEN)

## Real data proof (live backend call, `GET /v1/tenant/catalog/enabled-services/015efedb-dd92-41f4-97ef-cc2745437760/brand-pricing?service_type_id=...`, tenant owner token)

**Split AC + LG** (`service_type_id=c86dfcf3-53bd-4d83-bf0b-51257f382652`):
```json
{"brand_id":"64a3b25f-...","name":"LG","service_type_id":"c86dfcf3-...",
 "admin_floor_price":600,"admin_ceiling_price":950,
 "tenant_min_price":700,"tenant_max_price":850,
 "customer_price_preview":{"low_price":770,"mid_price":850,"high_price":935}}
```

**Window AC + LG** (`service_type_id=e27f6591-9b8d-4d57-93d0-8ed86c19c8af`):
```json
{"brand_id":"64a3b25f-...","name":"LG","service_type_id":"e27f6591-...",
 "admin_floor_price":350,"admin_ceiling_price":500,
 "tenant_min_price":420,"tenant_max_price":490,
 "customer_price_preview":{"low_price":462,"mid_price":500,"high_price":539}}
```

These are two **entirely distinct rows** in `tenant_service_brands` (`uq_tsb_service_type_brand UNIQUE (tenant_service_id, service_type_id, brand_id)`), each with its own `tenant_min_price`/`tenant_max_price`, confirmed via direct psql — not derived from a single global LG price. `identicalRanges=false` asserted and passed in the automated Playwright/API test.

## UI proof (`services/page.tsx`)
- Brand override rows in the wizard's Brands step are grouped **per selected type** (`typePricingState.map(tp => { rowsForType = brandPricingState.filter(b => b.typeId === tp.typeId) ...})`), each section headed by the type name ("Split AC" / "Window AC") followed by "Brand Overrides for {typeName}".
- Review table shows `↳ {typeName}` beside each brand row — type name is always shown beside brand name, never a single global LG row.
- Code comments in the file explicitly document a prior bug fix: "brand overrides must be scoped to a specific service type (Window AC + LG must be independent from Split AC + LG) — previously this state had no typeId at all, so one LG override applied identically to every type" — confirms this was a real known issue that has already been fixed prior to this sprint.
- Save payload: `homeServicesSetupApi.setBrandPricing(tenantServiceId, bp.brandId, min, max, bp.typeId)` — `service_type_id`/`bp.typeId` is always passed on save (verified in `lib/api.ts` line ~398: `setBrandPricing: (tenantServiceId, brandId, min, max, serviceTypeId?)`).

## Coverage page distinction (important, and correctly separated)
The Service Coverage page's "Types & Brands" tab intentionally does NOT offer per-type brand *enablement* — a code comment explains the backend models brand *enablement* (on/off) as type-independent by design, while brand *pricing* (min/max, the subject of this Part) is genuinely type-scoped and lives only in the Service Setup wizard. The coverage page correctly links out ("Configure that in Service Setup") rather than presenting a misleading per-type brand toggle. This is the correct architecture, not a gap.

## Safety
No destructive test was needed — all edits were read-only `GET` calls plus deliberately-invalid `PUT` attempts (min>max, below-floor) that the backend rejected with 422 before persisting anything. Confirmed via psql before and after: `tenant_service_brands` values for both LG rows are unchanged (700/850 and 420/490).

## Verdict: PASS — TYPE-SPECIFIC BRAND PRICING GENUINELY PROVEN, REAL, TENANT-EDITABLE, INDEPENDENTLY PERSISTED
