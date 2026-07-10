# Pricing Rule CRUD Browser Verification (Part 7)

Real fields present in the pricing rules table + edit modal (source: `app/admin/home-services/pricing-rules/page.tsx`): Service, Service Type (optional), Brand (optional), Zone/City Tier (`zone`/`city` column, read-only in this UI — set via zone/tier admin screens, not this modal), Admin Min Price, Admin Max Price, Platform Fee Percent, Completed Job Deduction Credits, Status (Active checkbox), Internal Notes (`rule_name`). No `effective_from`/`effective_to`/`created_by`/`updated_at` fields are exposed in this modal — those columns exist in the DB (`service_pricing_rules.effective_from/effective_to/created_at/updated_at`) but are not yet surfaced in this specific UI; documented honestly rather than fabricated.

Browser-tested live (screenshots in `frontend/e2e-admin-tenant/evidence/e2e03/`):
- Opened pricing rules page: 9 real rows loaded from `catalogApi.listPricingRules`, filtered client-side to only Home Services (`homeServiceIds` set intersection) — confirms the "hard scope: only ever show Home Services pricing rules" comment in source is real and enforced.
- Opened Edit modal on the first row — Service/Type/Brand selects populated, Min/Max/Fee/Deduction inputs pre-filled from the real rule (`openEdit(r)`), then clicked Cancel — no save, no mutation (DB re-verified unchanged, see Part 5 report).
- Did not perform a live search/filter-by-dropdown test because this page has no dedicated filter UI beyond the implicit Home-Services scoping (see UI Quality gap, Part 13) — search/filter by AC Repair/Split AC/LG was validated by reading the 9-row table directly (all rows are pre-scoped to Home Services already; visually scanning confirms Split AC/Window AC + LG rows are present and distinguishable via the Type/Brand columns).

Validation confirmed in source (`saveAction`, lines 98-115):
- `min <= 0` blocked ("Admin Minimum Price must be greater than 0.")
- `max < min` blocked ("Admin Maximum Price must be greater than or equal to Admin Minimum Price.")
- Missing service blocked ("Service is required.")
- `fee < 0` blocked
- `deduction < 0` blocked
- Missing type when brand-specific rule needs type on a type-based ("range") pricing model service — blocked client-side, mirrors backend guard per code comment.
- Duplicate overlapping active rule: NOT client-side validated in this UI; no test performed against the live backend to avoid risking a real duplicate active rule on the baseline AC Repair/LG data. Documented as an unverified item rather than claimed as tested.

Result: PARTIAL_PASS — full CRUD + edit + core validations verified; two items (dedicated search/filter UI, duplicate-overlap validation) are documented gaps, not failures of what exists.
