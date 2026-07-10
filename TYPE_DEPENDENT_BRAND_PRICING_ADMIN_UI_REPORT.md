# Type-Dependent Brand Pricing — Admin UI Report

## Not built this sprint
The ticket's Admin UI requirements (5-step Select Service → Select Type →
Select Tier/Zone → Set Type Base Range → Add Brand Overrides flow on
`/admin/home-services/pricing-rules`, with a Type column before Brand in
the pricing rule table, and an "Add Brand Price Override" form) were
**not implemented this sprint**. Given the scope of the ticket (data
model fix, tenant API fix, migration/cleanup script, and full backend
test coverage), the admin UI rebuild was deprioritized in favor of
fixing the actual data-correctness bug first — a UI that lets an admin
correctly configure type-scoped brand pricing is only meaningful once
the underlying storage/API actually respects that scoping, which is
what this sprint delivered and live-verified.

## What already exists on the admin side
`app/engines/admin_catalog/bargain_engine.py` and the `ServicePricingRule`
model already support `service_type_id` + `brand_id` scoped rules (used
correctly by the fixed tenant-side `_find_admin_pricing_rule` lookup,
confirmed live). The admin console page at
`/admin/home-services/pricing-rules` (`frontend/super-admin/app/admin/
home-services/pricing-rules/page.tsx`) was not inspected or modified
this sprint — its current column layout (whether Type already precedes
Brand, or whether it needs the ticket's requested rework) is unverified.

## Verdict
Admin UI: **not started**. Documented as the primary remaining blocker
for full ticket completion — see
`TYPE_DEPENDENT_BRAND_PRICING_REMAINING_BLOCKERS.md`.
