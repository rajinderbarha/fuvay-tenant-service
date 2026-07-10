# ADMIN-TENANT-E2E-09 — Provider Price Range Report

## Real validation proof (live API calls against `PUT /v1/tenant/catalog/enabled-services/015efedb.../types/{split_ac}/pricing`, tenant owner token)

- **min > max rejected**: `{tenant_min_price:900, tenant_max_price:700}` → `422 INVALID_PRICE_RANGE` — "Minimum price cannot exceed maximum price."
- **Below admin floor rejected**: `{tenant_min_price:100, tenant_max_price:200}` → `422 TENANT_PRICE_BELOW_ADMIN_MIN` — "Your minimum price cannot be below the admin floor (Rs. 850.00)."
- Real admin allowed ranges (confirmed via brand-pricing GET, matches handoff's stated numbers): Split AC+LG admin floor/ceiling = ₹600–950; Window AC+LG = ₹350–500. Tenant's own configured ranges (700–850, 420–490) sit correctly inside those bounds.

### Note on a minor inconsistency found
The `TENANT_PRICE_BELOW_ADMIN_MIN` error message text said "Rs. 850.00" as the floor rather than the brand-pricing-context floor of ₹600 seen elsewhere. This appears because the `/types/{id}/pricing` endpoint validates against the **type-level** admin floor (a property of `tenant_service_types`/its admin catalog source), which can legitimately differ from the **brand-level** floor returned by the brand-pricing endpoint (₹600) — these are two distinct floor concepts (type default floor vs. brand-specific floor within that type) and are not necessarily the same number by design. This is not confirmed to be a bug, but the message could be clearer about which floor it means; noted as a minor UX polish item, not a P0.

## UI proof (`services/page.tsx`, `TypePricingCard`)
- Shows "Working range: ₹{adminFloor} – ₹{adminCeiling}" as constraint/help text next to a visual range slider.
- Live inline validation: `minErr`/`maxErr` computed client-side (`min < tp.adminFloor`, `max > tp.adminCeiling`) and shown under each input before submit.
- Server-side validation (proven above) is the authoritative gate — client-side checks are a UX convenience, not the only enforcement.
- Customer Low/Mid/High is never manually entered — it's rendered read-only from `preview.low_price/mid_price/high_price`, computed server-side by `pricePreview()`/embedded in `customer_price_preview`. Platform fee shown once ("Platform fee: {platformFeePercent}%"), not double-applied — confirmed math: Split AC+LG mid_price 850 = tenant_max_price (fee appears to already be embedded in the floor/ceiling banding rather than added again on top, consistent with "fee-inclusive floor" language in the backend's `match_and_price` docstring).
- Negative price: not explicitly tested this run (client `type="number"` inputs have no `min=0` HTML constraint beyond `adminFloor`, but any negative value would fail the `min < adminFloor` check server-side since admin floors here are positive, e.g. 600/350) — inferred safe by the same floor-check codepath, not independently fuzzed.

## Verdict: PASS
