# Automatic Price Options — Admin UI Report

## New admin section: Home Services

Sidebar group with 3 pages, replacing the "Bargain Rules" nav item:

### 1. `/admin/home-services/price-experience` — Customer Price Experience

- Hero: live status of Automatic Price Options (enabled), Manual Bargain
  Rules (disabled), Provider-First Matching (enabled), Scope (Home Services
  only) — sourced from the real `GET /v1/admin/home-services/config`
  endpoint, not hardcoded.
- "Customer Low Rule: customer minimum + platform fee" explanation.
- Price Preview panel: admin enters Service/Admin Min/Admin Max/Admin
  Base/Customer Min/Customer Max/Platform Fee → calls
  `POST /v1/admin/home-services/price-experience/preview` (real backend,
  reuses the certified `compute_price_tiers` engine) → shows Low/Mid/High
  cards plus a full breakdown (Customer Minimum, Platform Fee, Minimum/
  Maximum Allowed Customer Offer).
- **Live-verified**: admin range ₹600–₹1200, customer range ₹650–₹900, fee
  10% → Low ₹715 / Mid ₹810 / High ₹900 (exact match to the ticket's
  example). Confirmed the hard rule holds: the preview never shows ₹650 as
  the customer Low — it always shows the fee-inclusive ₹715.

### 2. `/admin/home-services/provider-matching` — Provider Matching

- Status row: "Provider-first matching: Enabled", "Customer manual provider
  selection: Disabled for this flow", "Scope: Home Services only".
- Ranking factors shown as 8 weighted cards matching the certified formula
  exactly (Health Score 20%, Job Completion 20%, Rating 15%, Availability
  15%, Service Match 10%, Area Match 10%, Cancellation 5%, Capacity 5%).
- Actions: Preview Match / View Diagnostics (both link to Matching
  Diagnostics, the real working tool), View Audit (links to the deprecated
  Bargain Rules page's audit trail, kept for continuity), Reset Defaults
  (disabled — no persisted override exists to reset in this phase; honestly
  disabled rather than faked).

### 3. `/admin/home-services/matching-diagnostics` — Matching Diagnostics

- Real input form (category/service/city/zipcode/type/brand) →
  `POST /v1/admin/home-services/matching/diagnostics` (real backend, reuses
  the certified `select_best_provider` + `get_area_market_comparison`
  engines).
- Shows: Eligible/Candidate/Excluded counts, selected provider (customer-safe
  fields + admin-only score breakdown), top candidates ranked, Low/Mid/High
  price preview for the winner, area price comparison.
- **Live-verified** against the real test tenant: correctly shows 0 eligible
  providers with a clear "no eligible provider found" explanation (the test
  tenant genuinely fails the `tenant.status='active'` gate — the diagnostic
  correctly surfaces this rather than fabricating a fake match).

## Pricing Rules page (not modified — documented gap)

`/admin/pricing-rules` was **not** updated to add the ticket's requested
"Auto Low / Auto Mid / Auto High" columns or "Customer Price Range" labeling
to its table. It does not currently use forbidden "Bargain Range" wording
either (checked — no matches), so there is no mislabeling to fix, but the
richer table redesign (Admin Range / Customer Range / Platform Fee / Auto
Low/Mid/High columns per service/type/brand/issue/zipcode row) was not built
this sprint given the scope already covered by the 3 new Home Services pages
and the tenant preview page. Documented honestly in
`AUTO_PRICE_OPTIONS_REMAINING_BLOCKERS.md` rather than claimed as done.
