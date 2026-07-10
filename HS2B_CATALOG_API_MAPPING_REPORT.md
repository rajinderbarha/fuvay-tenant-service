# HS2B — API Mapping Report

## Additions this sprint
No new endpoints were added. This sprint's backend change was a fix
inside an existing method (`hard_delete_service_type`), not a new route.

## Real Group CRUD endpoints (pre-existing, now linked from the catalog console)
`GET/POST/PUT/DELETE /v1/admin/service-groups[/{id}]`,
`POST /v1/admin/service-groups/{id}/activate|deactivate|archive`,
`GET /v1/admin/service-groups/summary|export` — all real, all
confirmed via source read this sprint (see Service Group CRUD Report).

## Delete endpoints (real, confirmed)
- `DELETE /v1/admin/master-services/{id}` (soft) +
  `DELETE /v1/admin/master-services/{id}/hard-delete` (usage-checked).
- `DELETE /v1/admin/service-types/{id}` (soft) +
  `DELETE /v1/admin/service-types/{id}/hard-delete` (usage-checked —
  **fixed this sprint**, was previously unchecked).
- Brand and Issue Type: soft-delete only, no hard-delete route found.

## Ticket's suggested vs. real
The ticket's suggested `DELETE /v1/admin/home-services/catalog/...`
namespace doesn't exist — the real endpoints live under
`/v1/admin/service-groups`, `/v1/admin/master-services`,
`/v1/admin/service-types`, `/v1/admin/brands` (or similar, generic,
non-Home-Services-prefixed catalog routes), filtered by `category_id`
at the query/service layer rather than having a dedicated Home Services
URL namespace. This matches the mapping already documented in the
original HS2 sprint's API report — unchanged this sprint.

## No mock data
Confirmed: all new UI this sprint (Provider Setup Rules tab, health
cards, permission gates) derives from real, already-fetched API
responses (`HsConsoleServiceDetail`, `HsConsoleService`,
`usePermissions()` → `authApi.me()`). No new mock/static data introduced.

## Verdict
API integration: **real**, consistent with the original HS2 API mapping
report; one real backend bug fixed (service-type hard-delete usage
check).
