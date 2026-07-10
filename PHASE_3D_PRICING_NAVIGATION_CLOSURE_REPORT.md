# Phase 3D — Pricing Navigation Closure Report

## Sidebar structure — confirmed live from `components/layout/AdminLayout.tsx`

```
Pricing & Rules
- Pricing Tiers            → /admin/pricing-tiers
- City/Zip Mapping         → /admin/location-mapping
- Pricing Rules            → /admin/pricing-rules
- Bargain Rules            → /admin/pricing/bargain-rules
- Provider Pricing Overrides → /admin/pricing/provider-overrides
```

Matches the ticket's required structure exactly (labels identical; URL
paths differ from the ticket's assumed `/admin/pricing/tiers` style but are
the real, working routes — documented in
`PHASE_3D_BACKEND_E2E_ASSERTIONS_REPORT.md`).

## Forbidden: no pricing pages nested inside Home Services

Checked `GET /v1/admin/catalog/navigation/effective-menu?vertical_key=home_services`
— the `verticals[0].modules` array (the actual list `VerticalCatalogSection`
in `AdminLayout.tsx` renders under the Home Services sidebar section)
contains exactly 8 modules: Categories, Service Groups, Master Services,
Types & Brands, Service Options, Issue Types, Checklists, Service Setup.
**None** of Pricing Tiers, City/Zip Mapping, Pricing Rules, Bargain Rules,
or Provider Pricing Overrides appear in this list.

**Note on a related finding**: the same API response's separate
`universal_modules` array (a distinct, top-level field, not nested under any
vertical) does list `pricing_tiers` and `location_mapping` entries.
Confirmed via source inspection that `AdminLayout.tsx` **never reads**
`universal_modules` — it is dead data as far as the sidebar is concerned, not
a duplicate-rendering bug. This is worth flagging to a future sprint (either
remove the unused field from the API response or wire it somewhere
intentional), but it does not violate the ticket's hard gate since nothing
observable in the actual rendered sidebar duplicates pricing under Home
Services.

## Forbidden labels in navigation

Grepped `AdminLayout.tsx` for Cash Wallet / Tenant Payout / Withdrawals /
Provider Earnings Wallet — zero matches.

## Catalog "Configure Pricing" / "Configure Bargain" deep-links

**Not implemented.** No `Configure Pricing` or `Configure Bargain` link text
was found anywhere in `app/admin/catalog*` or `app/admin/verticals*`. This
is a real gap versus the ticket's Part 7 ask, but building new catalog
cross-links is a **new feature**, explicitly forbidden by this closure
sprint's own instructions ("Do not add new features"). Documented as a
carried-forward item for a future, dedicated sprint — not fixed here.

## Result: **PASS on the hard gate** (no pricing pages duplicated under Home Services in the actual rendered sidebar; no forbidden labels). **Gap documented, not fixed**: catalog deep-links to pricing/bargain pages don't exist yet.
