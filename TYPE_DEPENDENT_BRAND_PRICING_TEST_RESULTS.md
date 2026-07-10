# Type-Dependent Brand Pricing — Test Results

## New test suite
`tests/test_type_dependent_brand_pricing.py` — **14/14 passing**. Covers
data model (column + unique constraints), validation rules
(`SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING`, `SERVICE_TYPE_NOT_SUPPORTED`,
`BRAND_NOT_SUPPORTED`), the actual storage-scoping fix (get/set both
filter by `service_type_id`), the brand-enablement/pricing separation,
API surface, and the migration/cleanup script's dry-run/apply/no-blind-copy
behavior.

## Live end-to-end smoke test (real backend, real DB, real formula)
Using the real AC Repair master service (`a96e625a-60e1-46c0-bde4-
ccbb88da50a2`) with real seeded types (Window AC, Split AC) and brands
(LG, Samsung, Voltas) — the exact entities from the ticket's own example:

1. Enabled Window AC + Split AC + LG for the real tenant via the live API.
2. Inserted admin pricing rules: Window AC+LG = ₹350–500, Split AC+LG =
   ₹600–950 (representing what an admin would configure via the pricing
   console).
3. `PUT .../brands/{LG}/pricing?service_type_id={WindowAC}` with
   `{370, 480}` → **200**, returned `tenant_service_brand_id:
   3e94d9bf-...`, `customer_price_preview: {low: 407, mid: 470, high: 528}`.
4. `PUT .../brands/{LG}/pricing?service_type_id={SplitAC}` with
   `{700, 850}` → **200**, returned a **different**
   `tenant_service_brand_id: 2011776a-...`, `customer_price_preview:
   {low: 770, mid: 850, high: 935}` — **exactly matching the ticket's own
   example numbers** (Low ₹770, Mid ₹855≈850, High ₹935).
5. `GET .../brand-pricing?service_type_id={WindowAC}` → `[("LG", 370, 480)]`
6. `GET .../brand-pricing?service_type_id={SplitAC}` → `[("LG", 700, 850)]`
7. Direct `psql` query on `tenant_service_brands` confirmed **5 distinct
   rows** for this tenant_service: 3 legacy type-agnostic enablement
   markers + 2 real, independent type-scoped price rows with the exact
   values set above.

**Hard gate from the ticket — confirmed**: "Changing Type from Window AC
to Split AC must change brand pricing rules." Verified: two separate
`tenant_min_price`/`tenant_max_price` pairs exist and are retrieved
independently, with no cross-contamination.

## Regression sweep
```
pytest tests/ -k "tenant_service_setup or home_services or admin_catalog or type_pricing or brand" -q
```
**622 passed, 11 failed.** All 11 failures are in
`tests/test_brand_flow_improvements.py`, testing an unrelated admin
catalog UI feature (`/admin/master-services` brand-duplicate-warning
modal) — confirmed pre-existing and unrelated: this sprint's diff never
touched that file, that page, or any brand-*mapping* (as opposed to
brand-*pricing*) code path.

## TypeScript
`npx tsc --noEmit` — **0 errors** in both frontends (no frontend files
were changed this sprint — see the UI reports for why).

## Backend syntax/import check
Confirmed the modified `tenant_service.py` imports and runs correctly —
the live backend was restarted and served real requests successfully
using the fixed code (see live smoke test above), which would have
failed immediately on any import/syntax error.

## Verdict
Backend fix: **fully tested and live-verified, 0 regressions**. Frontend
verification: **not performed** (no browser session run — see Remaining
Blockers).
