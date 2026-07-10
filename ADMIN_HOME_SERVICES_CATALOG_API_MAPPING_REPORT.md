# Admin Home Services Catalog Setup — API Mapping Report

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/admin/home-services/catalog` | **New** — `GET /v1/admin/home-services/service-catalog/services` (grouped list, Home Services category hard-scoped) |
| `GET /v1/admin/home-services/catalog/{service_id}` | **New** — `GET /v1/admin/home-services/service-catalog/services/{service_id}` (composes general fields + types + brands) |
| `POST /v1/admin/home-services/catalog` | `POST /v1/admin/master-services` (pre-existing, real — "Add Service" links to the existing master-services admin screen rather than duplicating create-service UI) |
| `PUT /v1/admin/home-services/catalog/{service_id}` | `PUT /v1/admin/master-services/{service_id}` (pre-existing, real) |
| `POST/PUT .../types/{type_id}` | **New** — `PUT /v1/admin/home-services/service-catalog/services/{service_id}/types/{service_type_id}/limits` (upserts a type-scoped `ServicePricingRule` with floor/ceiling/platform fee/deduction credits) |
| `POST/PUT .../brands` | `GET /v1/admin/master-services/{service_id}/brands` (pre-existing list) + **new** `PUT /v1/admin/home-services/service-catalog/services/{service_id}/brands/{mapping_id}/behavior` (can_override_price / is_routing_only) + **new** `PUT .../brands/{brand_id}/limits` (brand-scoped floor/ceiling) |
| `POST/PUT .../issues` | `GET /v1/admin/issue-types?master_service_id=X` (pre-existing, real, filter parameter already supported) — full create/edit deep-links to the existing `/admin/service-setup/issue-types` screen rather than duplicating CRUD |
| `POST/PUT .../options` | `GET /v1/admin/service-options?master_service_id=X` (pre-existing, real) — full create/edit deep-links to `/admin/service-options` |
| `PUT .../pricing-rules` | Composed from the existing `/v1/admin/pricing-rules` CRUD via the new type/brand limit-upsert methods above (reuses `ServicePricingRule`, does not duplicate the table) |
| `POST /v1/admin/home-services/price-experience/preview` | **Not reused** — that endpoint already exists but implements a different (asymmetric) formula for the certified provider-first-matching flow. **New** `POST /v1/admin/home-services/service-catalog/price-preview` implements the ticket's exact symmetric formula (fee applied to both min and max) without touching the existing endpoint. See formula note below. |
| `GET .../audit` | **New** — `GET /v1/admin/home-services/service-catalog/services/{service_id}/audit` (queries the real `master_data_audit_log` table, scoped to this service's own audit rows + its pricing rules' rows) |
| Zones/Tiers | `GET /v1/admin/tiers` (pre-existing, real, `catalogApi.listTiers`) — read + link-out to `/admin/pricing-tiers` for tier CRUD |

## Formula note — two distinct, intentionally separate Low/Mid/High calculators

The already-certified Provider-First Matching flow (`app.engines.home_service_booking.matching_engine.compute_price_tiers`) computes `Low = bargain_floor (min + fee)`, `High = customer_max_price` **unmodified** — fee is only applied to the low end, by design of that flow's semantics (customer_min/customer_max there is the tenant's own negotiation range, not admin floor/ceiling).

This ticket's example (`₹550-₹700 @ 10% → Low ₹605, Mid ₹690, High ₹770`) requires fee applied to **both** ends. Rather than modify the certified, already-in-production `compute_price_tiers` (which would risk regressing Provider-First Matching), a new pure function `compute_symmetric_customer_price_tiers` was added to `bargain_engine.py`, used only by this new console (and available for the Tenant Setup Wizard ticket, which needs the identical formula). Live-verified to produce exactly `₹605 / ₹690 / ₹770` for the ticket's example and `₹935 / ₹1070 / ₹1210` for the second example.

## Summary

Nearly the entire data layer (master services, service types, brands, pricing rules, issue types, service options, pricing tiers) already existed with complete, real admin CRUD from prior sprints. This sprint's actual new backend work: the symmetric price formula, type/brand-scoped floor-ceiling upsert methods reusing `ServicePricingRule`, migration 118 (brand price-override behavior flags), and the consolidated console router — all live-verified end-to-end against the real seeded AC Repair service.
