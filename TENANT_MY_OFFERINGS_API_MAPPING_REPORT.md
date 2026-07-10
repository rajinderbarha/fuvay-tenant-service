# Tenant My Offerings — API Mapping Report

| Ticket suggestion | Real endpoint used | Notes |
|---|---|---|
| `GET /v1/tenant/context` | `useTenant()` (localStorage) | No dedicated context endpoint. |
| `GET /v1/tenant/offerings` | `GET /v1/provider/offerings/enabled` | Real endpoint (was broken — fixed, see Catalog Diagnostic Report). |
| `GET /v1/tenant/offerings/available` | `GET /v1/provider/offerings/available` | Real endpoint (was broken — fixed). |
| `GET /v1/tenant/offerings/readiness-issues` | Derived client-side from `readiness_blockers` on each row of `GET /v1/provider/offerings/enabled` | No separate issues-list endpoint exists; blockers are per-offering fields, not a distinct resource. |
| `POST /v1/tenant/offerings` | `POST /v1/provider/offerings/enabled` | Real endpoint (fixed — `ON CONFLICT` bug). |
| `GET/PUT /v1/tenant/offerings/{id}` | `GET/PUT /v1/provider/offerings/enabled/{id}` | Real endpoints (fixed — missing `provider_enabled_offering_id` alias). |
| `POST .../enable`, `POST .../disable` | `POST .../activate`, `POST .../deactivate` | Real endpoints, different verb names. |
| `DELETE /v1/tenant/offerings/{id}` | Not implemented in backend | No delete endpoint exists for enabled offerings; only activate/deactivate. Documented as a gap — the page does not offer a Delete action since no working backend call exists (an unwired button would violate "no mock runtime data"). |
| `GET /v1/tenant/catalog/available-services` | `GET /v1/provider/offerings/available` | Same real endpoint, now correctly sourced from `master_services`. |
| `GET /v1/tenant/catalog/home-services/service-groups` | `service_group_name` field on each available offering row (joined server-side) | No standalone service-groups-list endpoint was needed; group name is embedded per offering. |
| `GET /v1/tenant/catalog/home-services/master-services` | `GET /v1/provider/offerings/available` | Same. |
| `.../master-services/{id}/service-types` | `GET /v1/admin/master-services/{id}/types` | Real, `get_current_user`-gated (tenant-readable despite the `/admin` path prefix). |
| `.../master-services/{id}/brands` | `GET /v1/provider/brands/services/{id}/available` | Real, dedicated provider-facing endpoint (`admin_catalog/brand_provider_router.py`). |
| `.../master-services/{id}/issue-types` | `GET /v1/admin/master-services/{id}/issues` | **New** — added this session; no equivalent existed (see Catalog Diagnostic Report, Bug 4). |
| `.../master-services/{id}/service-options` | `GET /v1/catalog/master/service-options?master_service_id={id}` | Real, public catalog-read endpoint. |
| `GET /v1/tenant/service-areas` | `GET /v1/tenant/service-areas` (via `myStatusApi.getServiceAreas`) | Matches exactly — reused from the My Status sprint. |
| `GET /v1/tenant/staff` | `GET /v1/provider/team-members` (via `myStatusApi.getTeamMembers`) | Real endpoint, more accurate than `staffApi.list()` (role filter gap, documented in earlier phases). |
| `GET /v1/tenant/pricing/platform-preview` | `POST /v1/pricing/tenants/{id}/price-preview` | Real, working backend pricing pipeline (city floor, tenant price, brand/zone/dynamic adjustments) — used inside the enable wizard. |
| `GET /v1/tenant/setup/checklist` | Not separately fetched on this page | The My Status page (previous sprint) owns setup-checklist rendering; this page focuses on offerings specifically. |
| `GET /v1/tenant/activity` | `GET /v1/tenants/{tenant_id}/audit-log` (via `myStatusApi.getAuditLog`) | Reused from the My Status sprint. |

## New API client additions (`lib/api.ts`)

- `offeringCoverageApi` — `getTypes`, `getIssues`, `getOptions`.
- `offeringPricingApi` — `preview`.
- `AvailableOffering` interface extended with `slug`, `service_group_id`, `service_group_name`.

## Backend endpoints fixed this sprint

- `GET /v1/provider/offerings/available` — rewired from `master_offerings` (empty) to
  `master_services` (real).
- `GET /v1/provider/offerings/enabled` — rewired the same way; `provider_enabled_offering_id`
  aliased.
- `POST /v1/provider/offerings/enabled` — `ON CONFLICT` clause fixed to match the partial
  unique index.
- 5 other `provider_enabled_offerings` read points — `provider_enabled_offering_id` aliased.

## Backend endpoint added this sprint

- `GET /v1/admin/master-services/{service_id}/issues` — new, mirrors the existing `types`/
  `brands` mapping-list pattern exactly.
