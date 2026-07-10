# E2E-09 Type-Specific Brand Pricing Report

## Implementation Location
**File**: `app/(tenant)/tenant/setup/services/page.tsx`
**Wizard Step**: "4. Brands" (after Types and Pricing steps)

## Architecture

### Type-Specific Brand Pricing State
```typescript
interface BrandPricingState {
  typeId: string; typeName: string;  // ← per-type key
  brandId: string; brandName: string;
  canOverride: boolean;
  enabled: boolean;
  tenantMin: string; tenantMax: string;
  adminFloor: number | null; adminCeiling: number | null;
  preview: HsPricePreview | null;
}
```

### Correct Behavior: Type-Scoped Brand Overrides
- Brand pricing is fetched **per type** via `fetchBrandPricingForTypes()` which calls `homeServicesSetupApi.getBrandPricing(tsid, typeId)` for each selected type
- State key is `(typeId, brandId)` — so **Window AC + LG** is a separate entry from **Split AC + LG**
- UI groups brand override rows by type: one section per type with its own brand list
- Save: `homeServicesSetupApi.setBrandPricing(tenantServiceId, bp.brandId, min, max, bp.typeId)` — passes `typeId` explicitly, so overrides are type-scoped on the backend

### Fix Applied (Pre-existing)
- The page has a large comment documenting a previous bug where brand overrides had no typeId and silently flattened. This was already fixed before E2E-09.

### Service Coverage Page (Different Concern)
- `/provider/service-coverage` handles **service-level brand coverage** (which brands the provider supports for a service overall)
- This is correctly documented as separate from type-specific brand pricing
- A cross-link in the coverage page points to `/tenant/setup/services` for type-specific brand pricing

## Status: PASS — type-specific brand pricing correctly implemented with separate (typeId, brandId) state
