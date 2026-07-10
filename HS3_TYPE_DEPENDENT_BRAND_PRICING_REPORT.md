# HS3 — Type-Dependent Brand Pricing Report

## Prior state
The core data-model fix (migration 120: `service_type_id` on
`tenant_service_brands`, unique constraints on both
`tenant_service_brands` and `service_pricing_rules`) was already
completed and live-verified in an earlier sprint this session ("FIX —
Home Services Type-Dependent Brand Pricing"). HS3's job was to verify
and complete the **admin-side** enforcement, which had two real gaps.

## Real gaps found and fixed this sprint

### Gap 1 — brand override without type was allowed on the admin side
`AdminCatalogService.create_pricing_rule` had no check preventing an
admin from creating a brand-scoped pricing rule (`brand_id` set) with no
`service_type_id`, for a type-based service (`pricing_model == "range"`)
— exactly the "AC Repair + LG (no type)" wrong-scope example from the
ticket. **Fixed**: raises `SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING`
(422), live-verified:
```json
{
  "error_code": "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING",
  "detail": "Service type is required when adding brand pricing for a type-based service.",
  "status": 422
}
```
Matching the ticket's exact required error shape.

### Gap 2 — duplicate detection incomplete
Migration 120 added a DB unique constraint
(`uq_spr_service_type_brand_tier` on `master_service_id, service_type_id,
brand_id, tier_id`), but Postgres treats multiple `NULL`s as distinct in
a unique constraint — so duplicate "global, no tier" rules (the only
kind that exist in this dev environment, since no tiers are seeded) were
**not** actually blocked. **Fixed**: added an explicit application-level
duplicate check (correctly handling `NULL` tier/type/brand) before
insert, raising `DUPLICATE_TYPE_BRAND_PRICING_RULE` (409). The DB
constraint is kept as a defense-in-depth fallback (caught via
`IntegrityError` and translated to the same error code).

## Live verification (real backend, real DB, real seed data)
Using the real AC Repair service (Window AC / Split AC / LG / Samsung —
the exact entities from the ticket's own example):

1. `POST /v1/admin/pricing-rules` with `brand_id=LG`, no `service_type_id`
   → **422 SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING** ✅
2. `POST` Window AC + LG (already existed from the prior sprint's live
   test) → **409 DUPLICATE_TYPE_BRAND_PRICING_RULE** ✅ (confirms the
   duplicate check works against real pre-existing data, not just a
   fresh insert)
3. `POST` Split AC + Samsung (new, unused combo) → **201, created
   successfully** with a distinct `rule_id`, confirming valid new
   type+brand combinations are not blocked. ✅

## Pricing hierarchy — confirmed already correct
`_find_admin_pricing_rule` (tenant-side, `tenant_service.py`) already
implements exact-match resolution scoped by `service_type_id` +
`brand_id` — confirmed unchanged and correct from the prior sprint's
live verification (Window AC/LG and Split AC/LG resolve to different
rules with different ranges).

## Verdict
Type-dependent brand pricing: **fully enforced on both the tenant side
(prior sprint) and the admin side (this sprint)**, live-verified against
real data with all three test scenarios (missing-type rejection,
duplicate rejection, valid-new-combo acceptance) passing.
