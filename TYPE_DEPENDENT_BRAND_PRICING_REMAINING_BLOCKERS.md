# Type-Dependent Brand Pricing — Remaining Blockers

1. **Admin UI not rebuilt** — the ticket's 5-step Service→Type→Tier→
   Type-Range→Brand-Overrides admin flow and the reordered pricing rule
   table (Type before Brand) were not built this sprint. The backend now
   correctly supports type-scoped rules; the admin console UI to manage
   them through the new shape was out of this sprint's time budget.
2. **Admin duplicate-rule API error not implemented** — the DB now
   rejects true duplicate `(service, type, brand, tier)` rows (when
   `tier_id` is non-null — see blocker #4), but the admin router doesn't
   yet catch that integrity error and translate it into the ticket's
   `DUPLICATE_TYPE_BRAND_PRICING_RULE` `ServiceOSException` shape.
3. **Tenant UI not visually re-verified** — no browser session was run
   this sprint; the fix was verified entirely via direct API calls
   against the real backend. The frontend already threads
   `service_type_id` through its existing calls (unchanged this sprint),
   so it should work automatically, but this wasn't visually confirmed.
4. **Unique constraint gap when `tier_id IS NULL`** — Postgres unique
   constraints don't enforce uniqueness among multiple `NULL`s, so
   `uq_spr_service_type_brand_tier` does not prevent duplicate
   "global, no tier" admin rules (the common case in this dev DB, which
   has no tiers seeded). A real fix needs a partial unique index
   (`WHERE tier_id IS NOT NULL`) plus an application-level check for the
   tier-less case. Not implemented this sprint.
5. **Customer-facing booking-time price resolution not touched** — the
   ticket's 5-step fallback chain (type+brand+zone → type+zone →
   service+zone → error) exists conceptually via
   `_find_admin_pricing_rule`'s exact-match logic (verified for the
   type+brand case), but the full booking/matching-engine resolution
   path with zone/tier fallback was not located, reviewed, or modified
   this sprint.
6. **Price preview endpoint not extended with type context** — the
   ticket asks the preview API to accept `service_type_id` explicitly;
   `price_options_preview` in `tenant_service.py` currently accepts a
   raw min/max/fee dict without a type parameter (it's a pure
   calculator, not a lookup, so it doesn't strictly need one — but the
   ticket's exact API shape wasn't matched).
7. **`npm run build` / `npm run lint` / `npm test` not run** — same
   established constraint as prior sprints (dev server ports occupied by
   external processes); `tsc --noEmit` used as the build-health gate
   instead.

## What is solid
The actual data-correctness bug — brand pricing not being dependent on
service type — is fixed at the model, migration, and tenant-API layers,
and live-verified end-to-end against the real database using the
ticket's own AC Repair / Window AC / Split AC / LG example, producing
numbers that match the ticket's example exactly (Low ₹770, Mid ₹850,
High ₹935 for the Split AC + LG case). The migration/cleanup script
found and safely deprecated real legacy global-brand-pricing rows in the
dev DB without guessing a per-type mapping.
