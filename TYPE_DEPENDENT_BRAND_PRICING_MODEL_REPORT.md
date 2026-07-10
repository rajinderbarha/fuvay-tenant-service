# Type-Dependent Brand Pricing — Data Model Report

## Root cause
`TenantServiceBrand` (`app/engines/admin_catalog/models.py`) was keyed
only by `(tenant_service_id, brand_id)` — one price range per brand per
service, shared across every service type. The API layer
(`set_brand_pricing`/`get_brand_pricing_for_setup` in `tenant_service.py`)
already accepted and threaded a `service_type_id` parameter through to
read the admin-approved floor/ceiling (via `ServicePricingRule`, which
already had `service_type_id` + `brand_id` columns from an earlier
sprint), but had nowhere to *persist* the tenant's own type-scoped range
— so setting "LG" pricing for Window AC and then again for Split AC
silently overwrote the same row. This matches the ticket's example
exactly.

## Fix — migration 120 (`alembic/versions/120_type_dependent_brand_pricing.py`)
1. Added `service_type_id` (nullable UUID) to `tenant_service_brands`.
2. Widened the unique constraint from `(tenant_service_id, brand_id)` to
   `(tenant_service_id, service_type_id, brand_id)` —
   `uq_tsb_service_type_brand`.
3. Added a previously-missing unique constraint to `service_pricing_rules`:
   `(master_service_id, service_type_id, brand_id, tier_id)` —
   `uq_spr_service_type_brand_tier` (the admin side already had the
   columns but no uniqueness guarantee at all).

`NULL service_type_id` is preserved for two legitimate cases: (a) fixed
(non-type-based) services, where brand pricing is correctly
service-scoped only, and (b) the brand *enablement* marker row (see
below) — pricing rows are always type-scoped for type-based services.

## Known limitation of the new constraint (documented, not silently hidden)
Postgres unique constraints treat `NULL` as distinct from every other
`NULL` — so `uq_spr_service_type_brand_tier` does **not** prevent
duplicate rows when `tier_id IS NULL` (the common case for a "global,
no tier" admin rule). Confirmed live: an `--apply` cleanup run on the
real dev DB found 2 legacy global-brand rules that had NOT been blocked
by a manual duplicate insert during testing until the exact combination
matched down to a non-null value. A real fix would need a partial unique
index (`WHERE tier_id IS NOT NULL`) plus a separate application-level
duplicate check for the tier-less case — not implemented this sprint
(see Remaining Blockers).

## Second real fix: brand-enablement vs. brand-pricing separation
`get_tenant_service_brands` (the "which brands does this tenant support"
list used by the brand-selection step, distinct from pricing) was
restricted to `service_type_id IS NULL` rows only — otherwise, once a
brand has per-type pricing rows, this list would show duplicate entries
for the same brand (one per type). Enablement stays type-independent by
design (a tenant either supports LG or doesn't); pricing is what's now
correctly type-scoped.

## Live DB verification
```sql
SELECT tenant_service_id, service_type_id, brand_id, tenant_min_price, tenant_max_price
FROM tenant_service_brands WHERE tenant_service_id = '015efedb-dd92-41f4-97ef-cc2745437760';
```
Returned 5 rows for the real AC Repair tenant service: 3 legacy
type-agnostic enablement markers (NULL type) + 2 real, independent
type-scoped price rows (Window AC/LG = 370–480, Split AC/LG = 700–850) —
confirmed distinct `id`s, confirmed correct values retrieved
independently via GET.

## Verdict
Data model: **fixed and live-verified**. Brand pricing is now genuinely
dependent on service type at the storage layer, not just threaded
through the API as an unused parameter.
