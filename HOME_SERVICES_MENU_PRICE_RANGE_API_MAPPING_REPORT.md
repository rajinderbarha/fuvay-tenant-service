# Home Services Menu + Price Range — API Mapping Report

## Admin APIs

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/admin/home-services/pricing-rules` | `GET /v1/admin/pricing-rules` (pre-existing, real, full filter support) — the new `/admin/home-services/pricing-rules` **page** calls this and client-side-filters to the real Home Services `master_service_id` set (via `homeServicesCatalogConsoleApi.listServices()`, itself hard-scoped server-side) |
| `POST /v1/admin/home-services/pricing-rules` | `POST /v1/admin/pricing-rules` (pre-existing, real) |
| `PUT /v1/admin/home-services/pricing-rules/{rule_id}` | `PUT /v1/admin/pricing-rules/{rule_id}` (pre-existing, real) |
| `GET /v1/admin/home-services/catalog` | `GET /v1/admin/home-services/service-catalog/services` (built in the prior "Admin Home Services Catalog Setup" sprint, hard-scoped to the real Home Services category) |

No new backend endpoints were needed for Part A — the real
`ServicePricingRule` CRUD already existed and already worked; this
sprint's job was presenting it inside a properly Home-Services-scoped
admin page and nav position, not building new persistence.

## Tenant APIs

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/tenant/home-services/catalog/available` | `GET /v1/tenant/catalog/home-services/available-services` (built in the prior sprint) |
| `GET /v1/tenant/home-services/pricing-rules/allowed` | `GET /v1/tenant/catalog/enabled-services/{id}/type-pricing` and `/brand-pricing` (built in the prior sprint — returns `admin_floor_price`/`admin_ceiling_price` per type/brand) |
| `POST /v1/tenant/home-services/price-options/preview` | `POST /v1/tenant/catalog/price-options/preview` (built in the prior sprint) |
| `POST /v1/tenant/home-services/services/setup-draft` | `POST /v1/tenant/catalog/enable-service` (pre-existing; starts `setup_status="draft"`) |
| `PUT /v1/tenant/home-services/services/{id}/pricing` | `PUT /v1/tenant/catalog/enabled-services/{id}/types/{service_type_id}/pricing` and `/brands/{brand_id}/pricing` (built in the prior sprint) |
| `POST /v1/tenant/home-services/services/{id}/publish` | `POST /v1/tenant/catalog/enabled-services/{id}/publish` (built in the prior sprint) |

All tenant-side endpoints already existed from the immediately preceding
sprint and needed no changes for this ticket — re-verified live (see
`TENANT_PROVIDER_PRICE_RANGE_SETUP_REPORT.md`).

## Summary

This ticket's actual new API-consumption surface is 4 new admin frontend
pages (`/admin/home-services/pricing-rules`, `/service-areas`,
`/completed-job-deduction`, `/settings`), all composing real, pre-existing
endpoints (`/v1/admin/pricing-rules`, `/v1/admin/tiers`,
`/v1/admin/home-services/service-catalog/*`, `/v1/admin/home-services/config`)
rather than requiring new backend work.
