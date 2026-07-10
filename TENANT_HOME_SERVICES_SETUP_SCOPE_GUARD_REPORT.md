# Tenant Home Services Service Setup Wizard — Scope Guard Report

## Frontend guard

`app/(tenant)/tenant/setup/services/page.tsx` checks
`useTenant().vertical === "home_services"` before rendering anything else.
If false, it renders the exact required blocked-state text:

> This setup wizard is available only for Home Services. This vertical
> uses a different setup model.

## Backend hard boundary

The catalog list itself is now hard-scoped server-side (not just hidden by
the frontend guard) — `TenantCatalogService.list_home_services_available`
/ `list_home_services_enabled` always resolve the real Home Services
`ServiceCategory` (`vertical_type == "home_services"`) and filter every
query by that category id. This is the same real bug/fix documented in
the API Mapping report: previously, even if a non-Home-Services tenant
somehow reached this page, the underlying list endpoint the old wizard
used had no category filter and would have shown every vertical's
catalog. The new Home-Services-scoped endpoints this wizard actually
calls cannot return IELTS, CA Services, Restaurant, Real Estate, or any
other vertical's services — confirmed live: 15 real items returned, all
from the Home Services category, out of 57 total active services across
all verticals in the database.

## No mutation of other verticals

`set_type_pricing` / `set_brand_pricing` / `publish_service` all load the
target `TenantService` and re-derive `master_service_id` from it before
touching any `ServicePricingRule` row — there is no code path in this
sprint's additions that can write to a service, type, or brand belonging
to a different vertical, since the tenant can never select one in the
first place (the catalog they choose from is scoped, and `enable_service`
already validates `master_service_id` against a real, existing
`MasterService`).

## Live verification

Confirmed via direct query: 14 verticals exist in `service_categories`.
The wizard's catalog call (`GET /v1/tenant/catalog/home-services/available-services`)
returned only real Home Services items (AC Installation, AC Repair, AC
Service, Pipe Repair, Drain Unblocking, Electrical Fault Fix, Interior
Wall Painting, General Pest Control, etc.) — none of the other 13
verticals' services appeared.

## Result

**PASS** — scope is guarded both in the UI (readable blocked-state
message) and hard-enforced server-side (the data itself is filtered, not
just hidden).
