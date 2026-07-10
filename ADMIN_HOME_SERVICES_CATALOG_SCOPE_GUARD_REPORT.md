# Admin Home Services Catalog Setup — Scope Guard Report

## Hard backend boundary

`AdminCatalogService.get_home_services_category_id()` resolves the Home
Services category by querying `service_categories.vertical_type ==
"home_services"` — every console endpoint (`list_home_services_catalog_console`,
`get_home_services_service_console_detail`, and both type/brand limit
upserts) calls this first and raises `NOT_HOME_SERVICES_CATEGORY` (422) if a
service belongs to a different category. The list endpoint only ever
queries `MasterService.category_id == <home services category id>` — it
cannot return IELTS, CA Services, Restaurant, Real Estate, or any other
vertical's services, by construction (not a client-side filter).

## Frontend guard

If the category lookup itself fails (`listApi.error` mentions "Home
Services"), the page renders the exact blocked state text required by the
ticket:

> This wizard is only available for Home Services. Other verticals use
> their own setup model.

## No mutation of other verticals

Every write endpoint in the new `home_services_catalog_console_router.py`
takes a `service_id` and internally re-validates it belongs to the Home
Services category via `_load_master_service` + the category check above
before any write. The type/brand pricing-rule upsert helpers
(`upsert_home_services_type_limits`, `upsert_home_services_brand_limits`)
create/update `ServicePricingRule` rows scoped to `master_service_id`,
which is itself scoped to the Home Services category — there is no code
path in this sprint's additions that can touch a `ServicePricingRule`,
`MasterServiceType`, or `MasterServiceBrand` row belonging to any other
vertical.

## Live verification

Queried `service_categories` directly: 14 verticals exist (home_services,
salon, coaching, real_estate, restaurant, automotive,
professional_services, pharmacy, hardware, repair_services,
cleaning_services, laundry, marketplace_products, other). The console's
`GET /services` call returned only the 8 real Home Services groups (AC &
HVAC, Plumbing, Electrical, Carpentry & Woodwork, Painting & Walls,
Appliance Repair, Pest Control, Home Security) and their services — none
of the other 13 verticals' catalog data appeared.

## Result

**PASS** — scope is hard-enforced server-side, not just hidden in the UI.
