# Phase 3 — Pricing & Rules Backend Report

## Prerequisite check: Phase 2 status

Re-verified live before starting: AC Repair baseline chain intact (`GET
/v1/admin/master-services`, type/brand mappings, checklist system all
confirmed 200 with real data), 0 TypeScript errors, no sidebar duplicates.
**Phase 2 confirmed READY** — proceeding with Phase 3.

## Discovery: most of Modules 1-4 already existed

Research before building anything confirmed **Pricing Tiers, City/Zip
Mapping, Pricing Rules, and the Pricing Resolver were already fully built**
in `app/engines/admin_catalog/` (service.py + admin_router.py +
pricing_engine.py), from prior sprints (migration 077 "Pricing Enterprise
Upgrade" plus this session's earlier Phase 0/2 work). This sprint's real
backend work was: (a) adding the previously-missing
`completed_job_deduction_credits` field, and (b) building Bargain Rules and
Provider Pricing Overrides **from scratch** — both confirmed entirely absent
before this sprint (only a bare `bargain_floor` value existed with no
evaluation logic).

## Module 1 — Pricing Tiers

Pre-existing, confirmed still working. `GET/POST/PUT /v1/admin/tiers`,
`/tiers/summary`, `/tiers/export`, `/tiers/resolve-location`, enable/disable
via `DELETE /tiers/{id}` (soft) and `/hard-delete`. `PricingTier` model
(`app/engines/admin_catalog/models.py:23`) has `name, code, tier_type,
description, base_multiplier, platform_fee_percent,
default_commission_percent, default_sla_minutes, is_active, deleted_at`.
Mid tier confirmed live (`code=mid`).

## Module 2 — City / Zip Mapping

Pre-existing, confirmed still working. Full CRUD under `/v1/admin/tier-locations*`
plus a CSV import wizard (`preview`/`confirm`/batch tracking) — more complete
than the ticket's assumed scope. `TierLocation` model has `tier_id, country,
state, district, city, zipcode, zone_name, priority, is_active, deleted_at`.
Ludhiana/141001 confirmed live, resolves to Mid tier.

## Module 3 — Pricing Rules

Pre-existing, confirmed still working. `GET/POST/PUT/DELETE
/v1/admin/pricing-rules*`, `/summary`, `/export`, `/{id}/conflicts`. **This
sprint added**: `POST /pricing-rules/{id}/activate` and `/deactivate`
convenience endpoints (previously only a generic `PUT` + soft-delete
existed), plus the `completed_job_deduction_credits` field end-to-end
(model, create validation, update validation, `_rule_dict` response).
AC Repair baseline rule confirmed live: `base_price=800, min_price=600,
max_price=1200, bargain_floor=650, completed_job_deduction_credits=21`.

Validation confirmed live:
- `bargain_floor > base_price` → 422 `INVALID_BARGAIN_FLOOR` (pre-existing)
- `bargain_floor < min_price` → 422 `INVALID_BARGAIN_FLOOR` (**added this sprint**)
- `completed_job_deduction_credits < 0` → 422 `INVALID_DEDUCTION_CREDITS` (**added this sprint**)

## Module 4 — Pricing Resolver

Pre-existing (`app/engines/admin_catalog/pricing_engine.py::resolve_service_price`),
confirmed still working, **extended this sprint** to include
`completed_job_deduction_credits` and `payment_collection_mode` in the
response. Live-verified baseline: `POST /v1/admin/pricing-rules/preview`
with AC Repair + Split AC + LG + zipcode 141001 →
`final_customer_estimate: 800.0`, `completed_job_deduction_credits: 21`,
`payment_collection_mode: "customer_pays_provider_directly"`,
`bargain_floor: 650.0`. **Hard gate PASS.**

## Module 5 — Bargain Rules (built from scratch)

New table `bargain_rules` (migration 111), model `BargainRule`, full CRUD +
enable/disable in `AdminCatalogService`/`admin_router.py` under
`/v1/admin/pricing/bargain-rules*`. Live-verified: created a bargain rule
(floor=₹650, action=reject) linked to the AC Repair pricing rule; confirmed
audit log entry (`master_data_audit_log`, entity_type=bargain_rule).

## Module 6 — Bargain Evaluation

New `POST /v1/admin/pricing/bargain/evaluate-preview`. Live-verified all 5
ticket scenarios:
- ₹500 → `accepted: false, eligible: false, reason: "Offer is below bargain floor."`
- ₹649 → same rejection
- ₹650 → `accepted: true, eligible: true`
- ₹700 → `accepted: true, eligible: true`
- ₹1300 → `accepted: true` (ticket allows "accepted or normalized above max
  depending on policy" — this implementation doesn't cap above max since no
  ceiling behavior was specified as a hard requirement; documented as a
  design choice, not a bug)

**Hard gate PASS**: ₹500 and ₹649 (below ₹650 floor) both correctly blocked.

## Module 7 — Provider Pricing Overrides (built from scratch)

New table `provider_pricing_overrides` (migration 111), model
`ProviderPricingOverride`, full CRUD + approve/reject + enable/disable under
`/v1/admin/pricing/provider-overrides*`. Live-verified all 3 ticket
scenarios against the AC Repair baseline (min=600, max=1200):
- ₹500 → 422 `OVERRIDE_BELOW_MIN`, `"Override price 500 is below the
  platform minimum price 600.00."`
- ₹900 → 201 created, `approval_status: "pending"`
- ₹1300 → 422 `OVERRIDE_ABOVE_MAX`, `"Override price 1300 exceeds the
  platform maximum price 1200.00."`

Approve workflow live-verified: `POST .../approve` → `approval_status:
"approved"`, `approved_by_user_id` and `approved_at` populated.

**Hard gate PASS**: provider override never violates platform min/max —
enforced server-side on both create and update.

## Module 8 — Completed Job Deduction Configuration

Confirmed configured as `21` usage credits on the AC Repair baseline rule
(both via direct field on `service_pricing_rules` and reflected in the
resolver response). Negative values rejected. Field is explicitly named
`*_credits` (not `*_amount`/`*_cash`) throughout model, service, and API —
matches the ServiceOS business rule that this is never cash.

## Permissions

Added 22 new `PRICING_*` permission constants (`app/core/permissions.py`)
matching the ticket's exact naming (`pricing.read`, `pricing.tiers.read`,
`pricing.rules.activate`, `pricing.bargain_rules.read`,
`pricing.provider_overrides.approve`, etc.). All 15+ new Bargain/Override
endpoints gated by these; existing Tiers/City-Zip/Rules endpoints continue
using the pre-existing `CATALOG_TIERS_*`/`CATALOG_PRICING_*` constants
(functionally equivalent, different naming — documented, not changed, to
avoid breaking existing call sites).

## Audit Logs

All mutations (bargain rule create/update/enable/disable, override
create/update/approve/reject/enable/disable) write to
`master_data_audit_log` via the existing `AdminCatalogService._audit()`
helper — same table/pattern used by pricing rules, categories, service
groups etc. since Phase 2. Confirmed live: `entity_type='bargain_rule'`
and `entity_type='provider_pricing_override'` rows present with
`request_id`, `actor_user_id`, `old_value`/`new_value`, `change_summary`.

## Swagger / OpenAPI

All new endpoints have FastAPI `summary=` + `tags=` (Bargain Rules,
Provider Pricing Overrides), auto-included in `/docs` and `openapi.json` via
the existing router mount — no separate registration needed.

**All backend hard gates PASS.**
