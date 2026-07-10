# HS2 — Catalog-Only Scope Report

## Dependency status
- HS0 (`READY_HS0_HOME_SERVICES_PROJECT_CLEANUP_CERTIFIED`) — real, certified
  this session.
- HS1 — no such sprint exists in this repo's real history (same pattern as
  the fictional A1 dependency accepted in earlier admin sprints this
  session). Documented as an accepted, pre-existing risk pattern; HS2
  proceeded per the ticket's own instruction ("continue only if
  instructed" — continuing per the same standing session convention).

## Real scope violation found and fixed (the ticket's auto-fail condition)
Before this sprint, `/admin/home-services/service-catalog` **mixed deep
pricing logic directly into the catalog UI**:
- The "Types & Pricing" tab had a full floor/ceiling/platform-fee/
  completed-job-deduction edit form per type.
- The "Brands" tab had a "Set Override Limits" floor/ceiling/fee form per
  brand.
- A "Zones / Tiers" tab existed purely for tier-scoped pricing.
- A "Customer Price Preview" tab computed and displayed a live Low/Mid/
  High calculation from provider min/max/fee inputs.

This is exactly the condition the ticket says must trigger
`NOT_READY_HS2_CATALOG_SCOPE_FAILED`.

## Fix applied
- Removed all floor/ceiling/fee/deduction input forms from the Types and
  Brands tabs — they now show catalog-only fields (visibility,
  selectability, status, and whether brand price-override is allowed
  later) plus a link: *"Pricing is configured in Pricing Rules." → Open
  Pricing Rules*.
- Removed the "Zones / Tiers" tab entirely (tier-scoped pricing is
  Pricing Rules' responsibility, not the catalog's).
- Rewrote the "Customer Preview" tab to show only the catalog experience
  (service name/description, type selector, brand question) — no
  provider-min/max/fee inputs, no computed price, no Low/Mid/High output.
- Renamed tabs to the ticket's required labels: General, Types, Brands,
  Questions / Issues, Options / Add-ons, Customer Preview, Activity.
- Removed the misleading "manual bargain disabled... platform derives
  Auto Low/Mid/High" banner from the page header (that's a pricing
  concept, doesn't belong in a catalog-only page).

## Confirmed absent post-fix
- No floor/ceiling/platform-fee input fields anywhere in the page
  (grep-verified, and enforced by a new test:
  `test_types_tab_has_no_pricing_form`).
- No Low/Mid/High computed result anywhere in the page.
- No tier/zone pricing configuration.

## Home Services isolation
The page's scope guard (`scopeBlocked`, checking for a "Home Services"
error substring from the backend) was not modified — confirmed unchanged
and still gates the entire console to Home Services only. No IELTS/CA
Services/Restaurant/Real Estate/Food/Marketplace/Subscription/Listing
category code paths exist in this file (confirmed via read-through — the
file only ever queries `homeServicesCatalogConsoleApi`, `masterDataApi`
filtered by `master_service_id`, and no cross-vertical calls).

## Verdict
Scope violation: **found and fixed**. The catalog console is now
genuinely catalog-only — pricing configuration is referenced (link-out)
but never performed inside it.
