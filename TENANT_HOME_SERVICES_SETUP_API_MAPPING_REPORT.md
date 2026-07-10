# Tenant Home Services Service Setup Wizard — API Mapping Report

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/tenant/home-services/catalog/available` | **New** — `GET /v1/tenant/catalog/home-services/available-services` (wraps the pre-existing `list_available_services`, adding a mandatory Home Services category filter — see the real bug fixed below) |
| `GET /v1/tenant/home-services/catalog/{service_id}` | `GET /v1/admin/master-services/{service_id}/types` + `/brands` (pre-existing, `get_current_user`-gated, safe for tenant read) for the Service Overview step's pricing-model/brands/types summary |
| `GET /v1/tenant/home-services/services` | **New** — `GET /v1/tenant/catalog/home-services/enabled-services` (Home-Services-scoped enabled list) |
| `POST /v1/tenant/home-services/services/setup-draft` | `POST /v1/tenant/catalog/enable-service` (pre-existing — enabling a service starts it in `setup_status="draft"` per migration 119's default) |
| `PUT /v1/tenant/home-services/services/{tenant_service_id}/setup` | Composed from 4 pre-existing/new calls: `PUT .../types` (type selection), **new** `PUT .../types/{service_type_id}/pricing`, `PUT .../brands` (brand selection), **new** `PUT .../brands/{brand_id}/pricing` |
| `POST /v1/tenant/home-services/services/{tenant_service_id}/publish` | **New** — `POST /v1/tenant/catalog/enabled-services/{id}/publish` — validates completeness (types priced, brand overrides complete, active service area exists) before flipping `setup_status` to `published` |
| `POST /v1/tenant/home-services/services/{tenant_service_id}/disable` | `POST /v1/tenant/catalog/disable-service` (pre-existing, unchanged) |
| `POST /v1/tenant/home-services/price-options/preview` | **New** — `POST /v1/tenant/catalog/price-options/preview` — wraps `compute_symmetric_customer_price_tiers` (same formula as the Admin Catalog Console, live-verified against both ticket examples) |
| `GET /v1/tenant/service-areas` | `providerServiceAreasApi.list()` (pre-existing, from the Service Coverage Areas sprint) — used to gate Publish |
| `GET /v1/tenant/activity` | Not wired into this page (no dedicated activity feed on this wizard yet — see Remaining Blockers) |

## New endpoints added this sprint (all under `/v1/tenant/catalog`)

- `GET /home-services/available-services`, `GET /home-services/enabled-services` — Home-Services-only catalog/enabled lists
- `GET /enabled-services/{id}/type-pricing`, `PUT /enabled-services/{id}/types/{service_type_id}/pricing`
- `GET /enabled-services/{id}/brand-pricing`, `PUT /enabled-services/{id}/brands/{brand_id}/pricing`
- `POST /price-options/preview`
- `POST /enabled-services/{id}/publish`, `POST /enabled-services/{id}/save-draft`

## Real bug found and fixed: catalog leaked every vertical to every tenant

`TenantCatalogService.list_available_services` (pre-existing, used by the
older `masterCatalogApi`/`/provider/offerings` flow too) had **no category
filter at all** — live-verified it returned 57 services spanning IELTS,
Real Estate, Restaurant, Salon, Automotive, Coaching, and Home Services,
all mixed together, to a Home Services tenant. Fixed by adding an
*additive, optional* `category_id` parameter (existing callers unaffected
— confirmed via the full backend regression suite, 108/108 passing) and
new `list_home_services_available`/`list_home_services_enabled` wrapper
methods that always resolve and pass the real Home Services category id.
Live-verified: the new endpoint returns exactly 15 real Home Services
items (AC Repair, AC Installation, Plumbing, Electrical, Pest Control,
Home Deep Cleaning, etc.) — zero non-Home-Services services.

## Summary

Most of the enable/disable/type-selection/brand-selection plumbing already
existed and was real. This sprint's actual new backend work: per-type and
per-brand tenant price-range storage + validation against the real
admin-configured floor/ceiling (written by the Admin Home Services Catalog
Console sprint), the symmetric Low/Mid/High preview, publish-time
completeness validation, and the Home-Services category scope fix — all
live-verified end-to-end against the real seeded AC Repair service
(Window AC 550-700 → Low 605/Mid 690/High 770; Split AC 850-1100 → Low
935/Mid 1070/High 1210; Voltas brand override 950/950 → Low 1045 — all
exact ticket matches).
