# Admin Home Services Catalog Setup — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. Issues / Options / Zones tabs are read + link-out, not full inline CRUD

These three tabs show a real, live, service-filtered list from the
existing (pre-existing, certified) `/v1/admin/issue-types`,
`/v1/admin/service-options`, and `/v1/admin/tiers` endpoints, with a
"Manage in X →" link to each capability's dedicated, already-working admin
screen. Building three more full create/edit forms inside this console
would duplicate the source of truth and double the surface for bugs.
If the product wants fully inline editing for these three, that's a
follow-up scoped to this console specifically.

## 2. "Pricing Model" is its own General-tab field, not a separate tab

The ticket lists "Pricing Model" as tab 2, distinct from "General" (tab
1). Since `pricing_model` is a single field on the same `MasterService`
row as the rest of the General fields, it's shown inside the General tab
rather than as its own tab with no other content — a presentation
simplification, not a missing capability.

## 3. `pricing_model` enum values differ from the ticket's wording

Backend `VALID_PRICING_MODELS = {"fixed", "range", "post_assessment",
"hourly"}`. The console's `PRICING_MODEL_LABELS` maps `"range"` →
"Type-based" and `"post_assessment"` → "Consultation" for display, since
renaming the backend enum would be a much larger, unrelated migration
across every consumer of `pricing_model`.

## 4. No dedicated "Home Services Overview" page yet

The nav's new "Overview" item currently points at the existing Customer
Price Experience page (`/admin/home-services/price-experience`) since no
separate overview/dashboard page exists yet. Documented rather than
building a placeholder page with no real content.

## 5. Zone/tier-scoped type and brand pricing rules share the same
   upsert path as the global default

The Types & Pricing and Brands tabs write a tier-less (`tier_id=None`)
default `ServicePricingRule`. Per-tier overrides (Tier 1 vs Tier 2 vs
Tier 3 floor/ceiling for the same type) are supported by the underlying
`ServicePricingRule.tier_id` column and the existing `/v1/admin/pricing-rules`
CRUD, but this console's UI doesn't yet expose a tier selector on the
Types & Pricing/Brands editors — a tier-aware pricing rule can be created
via the existing Pricing Rules admin screen today. Follow-up: add a tier
selector to this console's editors directly.

## 6. Permission constants reused rather than newly minted

The ticket lists dotted permission names
(`admin.home_services.catalog.read`, etc.). Rather than add a parallel set
of permission constants with identical semantics to the ones already
enforced on this exact data (`P.CATALOG_PRICING_READ`,
`P.CATALOG_PRICING_WRITE`, `P.PRICING_BARGAIN_EVALUATE_PREVIEW`), the new
router reuses those existing, already-role-mapped constants — avoiding a
second parallel permission system for the same underlying tables.

## 7. Pre-existing, unrelated build/tooling gaps

Same `useSearchParams`/`EnterpriseDataGrid` Suspense issue on
`/admin/refund-requests` (unrelated to this page), no ESLint config, no
`npm test` script — all previously documented, all confirmed untouched by
this sprint.

## 8. 13 pre-existing, unrelated pytest failures

See Test Results report — confirmed unrelated to this sprint's changes
(different frontend pages, and one expecting a "Bargain Rules" nav label
that a prior, already-certified sprint in this session intentionally
removed).
