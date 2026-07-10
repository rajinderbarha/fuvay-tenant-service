# Remaining Blockers (ADMIN-TENANT-E2E-03)

No P0/P1 blockers found. Non-blocking items, documented honestly rather than hidden:

1. **price-experience page is a manual what-if calculator, not a live rule-bound lookup.** An admin cannot click "show me Split AC + LG Ludhiana's real customer price" directly — they must know and type the numbers (700/850/10%). The calculation itself is correct and backend-verified (real API round-trip via `autoPriceOptionsApi.previewPriceExperience`). Suggested follow-up (not done this sprint, would exceed "safe scoped fix"): add a rule picker that pre-fills the form from a selected `service_pricing_rules` row.
2. **service-areas page shows tier-level aggregates only** (Small/Mid/Large cards), not a per-zipcode table inline. Granular Ludhiana/141001 detail requires navigating to the linked `/admin/pricing-tiers` page. This is an existing, intentional scope split (confirmed via the on-page "Manage tier definitions and city/zipcode mapping →" link) rather than a bug.
3. **No dedicated search/filter UI** on service-catalog (left-rail list) or pricing-rules (9-row table) pages. Both are currently small enough to scan visually; would need new UI work to add, out of "safe scoped fix" size for this sprint.
4. **Duplicate overlapping active pricing rule validation** was not live-tested against the backend (to avoid risking creation of a real conflicting active rule on the AC Repair/LG baseline data). Client-side form has no explicit check for this case either — unverified, not confirmed broken.
5. **No `npm test` script** configured in `frontend/super-admin/package.json` — pre-existing gap from prior sprints, unrelated to this sprint's scope.
6. Two stray "AC Repair Duplicate Test" service rows exist in the DB from an earlier catalog-bugfix sprint (ids `c6894687-...`, `f91f0ee8-...`) — not created by this sprint, left untouched (out of scope to clean up test-artifact rows from prior sprints).

None of the above block certification — all 4 in-scope routes work, render real data, use the real API client, have no forbidden labels, no mock data, pass tsc/build/Playwright, and Part 5's critical type-specific brand pricing separation is proven at both DB and UI layers.
