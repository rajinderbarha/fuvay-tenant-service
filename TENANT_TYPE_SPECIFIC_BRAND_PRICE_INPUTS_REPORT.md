# Tenant Type-Specific Brand Price Inputs — Final Report

## 1. Root cause
The tenant Service Setup wizard's `/tenant/setup/services` page had a
real, confirmed type-blind brand pricing UI:
- `BrandPricingState` (the local React state shape) had **no `typeId`
  field at all** — it was a flat list of brands, period.
- Brand pricing was fetched **once, type-agnostically**
  (`getBrandPricing(tenantServiceId)`, no `service_type_id` argument).
- Saving called `setBrandPricing(tenantServiceId, bp.brandId, min, max)`
  — again, **no `service_type_id`**.
- The Review & Publish matrix rendered the exact same flat
  `brandPricingState` list under **every** type row via
  `brandPricingState.filter(b => b.enabled && b.canOverride)` — with no
  type filter at all, so one LG override displayed identically under
  both Window AC and Split AC.

This is exactly the bug the ticket describes. Notably, the **backend**
(fixed in an earlier "Type-Dependent Brand Pricing" sprint this
session — migration 120, real `service_type_id` column and unique
constraint on `tenant_service_brands`) and the **API client**
(`lib/api.ts`'s `getBrandPricing`/`setBrandPricing` already accepted an
optional `serviceTypeId` parameter) were both already fully ready —
the bug was entirely confined to this one page never using the
parameter that already existed.

## 2. Tenant UI fix result
Fixed. `BrandPricingState` now has `typeId`/`typeName`. Brand pricing is
fetched once per selected type (`fetchBrandPricingForTypes`, one
`getBrandPricing(tsid, typeId)` call per type, results tagged with
`typeId`). Step 4 now renders one section per type
("Brand Overrides for Window AC" / "Brand Overrides for Split AC"),
each with its own admin range, type range, and brand override rows —
matching the ticket's exact required UI structure.

## 3. Brand override modal result
No separate modal exists in this page's current architecture (brand
override rows are inline, not modal-based) — the ticket's "Add Brand
Override Modal" section describes a UI pattern not used here. The
inline row equivalent (`BrandOverrideRow`, now rendered inside each
type's section) achieves the same functional requirement: type context
is implicit and locked (the row only ever exists inside its type's
section, and every save call includes that type's ID) — service type
cannot be changed or omitted from within a row.

## 4. Review matrix result
Fixed. Brand rows are now filtered by `b.typeId === tp.typeId` instead
of showing every brand under every type. Added the ticket-required
"No brand override — using type price / Add override" row for brands
that support override but haven't been configured for that specific
type, with a CTA back to Step 4.

## 5. Backend model result
Already correct (prior sprint) — `TenantServiceBrand.service_type_id`
real column, unique constraint on
`(tenant_service_id, service_type_id, brand_id)`.

## 6. API result
Already correct (prior sprint) — `PUT .../brands/{brand_id}/pricing?service_type_id=`
real, functioning endpoint. This sprint's fix was purely wiring the
frontend to actually pass the parameter that was already accepted.

## 7. Validation result
Already correct (prior sprint) —
`SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING` for type-based services
missing a type, `SERVICE_TYPE_NOT_SUPPORTED` for an invalid/unselected
type (ticket's suggested `INVALID_SERVICE_TYPE_FOR_SERVICE` — same
meaning, established naming difference, not renamed to avoid breaking
already-certified tests), boundary validation
(`TENANT_PRICE_BELOW_ADMIN_MIN`/`_ABOVE_ADMIN_MAX`), duplicate handling
via upsert-by-natural-key.

## 8. Customer price preview result
Fixed automatically as a consequence of the type-scoping fix — each
type's brand override row now calls the preview API with that row's own
values, so Window AC + LG and Split AC + LG each get their own,
independently-correct Low/Mid/High preview (confirmed live: ₹440/480/528
vs ₹770/850/935).

## 9. Live verification result
All 8 required scenarios passed — see
`TENANT_TYPE_SPECIFIC_BRAND_PRICE_LIVE_VERIFICATION_REPORT.md`.

## 10. Regression test result
400/400 passing across the combined Home-Services/tenant-setup/type-
dependent/wizard test sweep; 13/13 new tests for this fix; 0
regressions.

## 11. TypeScript output
0 errors, both frontends.

## 12. Build output
Not run (established port-conflict constraint this session);
`tsc --noEmit` used as the build-health gate.

## 13. Bugs found
The core bug: type-blind brand pricing UI in the tenant Service Setup
wizard, causing one brand override to visually and functionally apply
to every service type simultaneously.

## 14. Bugs fixed
Fully fixed: state model, fetch, save, Step 4 UI, and Review matrix all
now correctly scope brand overrides by service type. Live-verified
end-to-end (save, retrieve, update-doesn't-cross-contaminate, publish
preserves both).

## 15. Remaining blockers
See `TENANT_TYPE_BRAND_OVERRIDE_REMAINING_BLOCKERS.md`.

## Final recommendation

`READY_TENANT_TYPE_SPECIFIC_BRAND_PRICE_INPUTS_CERTIFIED`
