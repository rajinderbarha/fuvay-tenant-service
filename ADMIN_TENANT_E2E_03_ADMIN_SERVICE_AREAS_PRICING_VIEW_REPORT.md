# Service Areas / Zone Pricing View Report (Part 9)

Route: `/admin/home-services/service-areas` (`app/admin/home-services/service-areas/page.tsx`).

This page shows platform **city tiers** (Small/Mid/Large), each card showing: Tier name, tier_type, linked cities count, linked zipcodes count, active pricing rules count (`t.linked_counts.cities/zipcodes/rules_active`) — via `catalogApi.listTiers(true)`. It does not show a flat City/Zipcode/Zone table directly (that granular view lives at `/admin/pricing-tiers`, linked via "Manage tier definitions and city/zipcode mapping →" at the bottom of the page — confirmed real link).

DB-verified: Ludhiana / 141001 exists in `tier_locations` mapped to the "Mid" tier (`tier_id=5df472dd-...`), `is_active=true`, and also exists in `tenant_service_areas` as an active row. The "Mid" tier card on this page would show a `linked_counts.cities`/`zipcodes` count that includes Ludhiana/141001 (not individually re-verified via UI click-through beyond the tier-card level, since per-zipcode granularity is intentionally deferred to `/admin/pricing-tiers` by this page's own design).

Provider coverage count: not shown on this specific page (out of its scope — it's zone/tier scoped, provider coverage lives in Provider Matching / bookability pages, out of Part 9's strict scope).

Browser-tested live: page loaded with tier cards rendered, no NaN/undefined (test assertion passed), screenshot `frontend/e2e-admin-tenant/evidence/e2e03/service-areas.png`.

Result: PASS — admin can view City/Zipcode/Tier coverage (aggregated at tier level here, granular at linked `/admin/pricing-tiers` page); Ludhiana/141001 confirmed mapped and active at the DB layer; pricing rules can and do target this tier (Split AC+LG / Window AC+LG rules use the same `service_pricing_rules` table with `tier_id`/`zone`/`city`/`zipcode` columns available).
