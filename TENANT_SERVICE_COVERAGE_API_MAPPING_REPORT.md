# Tenant Service Coverage Areas — API Mapping Report

| Ticket suggestion | Real endpoint used |
|---|---|
| `GET /v1/tenant/context` | `useTenant()` (localStorage) |
| `GET /v1/tenant/service-areas` | `GET /v1/tenant/service-areas` (`providerServiceAreasApi.list`) — pre-existing, real. Fixed a field-name mismatch: frontend previously read `area_id`/`area_type`/PATCH against a backend that actually returns `id`/`coverage_type` and only accepts `PUT` — now aligned. |
| `POST /v1/tenant/service-areas` | Same — pre-existing, real. Now enforces the real plan limit and clears any existing primary when `is_primary: true` is sent (previously `is_primary` wasn't even a column). |
| `GET /v1/tenant/service-areas/{area_id}` | Same — pre-existing, real |
| `PUT /v1/tenant/service-areas/{area_id}` | Same — pre-existing, real (frontend was incorrectly calling `PATCH`; fixed to `PUT` to match the router) |
| `DELETE /v1/tenant/service-areas/{area_id}` | Same — pre-existing, real (soft-deactivate, not a hard delete) |
| `POST /v1/tenant/service-areas/{area_id}/set-primary` | **New** — added this sprint (`app/engines/serviceability/service.py::set_primary_service_area` + router). Previously `is_primary` was referenced by the frontend but did not exist anywhere in the backend model/schema — clicking "Set Primary" silently no-op'd or would have 422'd. |
| `POST /v1/tenant/service-areas/validate` | **New** — added this sprint (`validate_service_area`). Resolves city/district/state/zone-tier from a pincode-prefix lookup table, and returns real duplicate-check + real package-limit-check results. Previously this was a raw `fetch()` to a nonexistent `/v1/platform/locations/resolve-zipcode` endpoint that silently fell through to a single hardcoded `"141001"` fallback map baked into the frontend. |
| `GET /v1/tenant/service-areas/limits` | **New** — added this sprint (`get_service_area_limits`). Previously the frontend used a hardcoded `AREA_LIMIT = 5` constant with no backend source of truth at all. |
| `GET /v1/tenant/package` | Not used for the slot limit anymore — replaced by the new limits endpoint above, which is sourced from the real `tenant_limits.max_service_areas` column (new this sprint, seeded from `PLAN_LIMITS` by plan: starter=5, growth=20, enterprise=100). |
| `GET /v1/tenant/setup/checklist` | Not called on this page (setup checklist lives on `/provider/status`) |
| `GET /v1/tenant/activity` | `tenantSetupApi.getActivity(1)` — pre-existing, real |
| `GET /v1/platform/locations/resolve-zipcode` | **Does not exist as a platform-wide geo endpoint.** Replaced by the new `/v1/tenant/service-areas/validate` endpoint's built-in `PINCODE_PREFIX_LOOKUP` table (`app/engines/serviceability/constants.py`) — a small, honest, deterministic heuristic (11 major-city prefixes including `141` → Ludhiana/Punjab/Tier 2), not a full postal database. See Remaining Blockers. |
| `POST /v1/platform/locations/validate` | Folded into the same `/v1/tenant/service-areas/validate` endpoint (coverage validity + duplicate + limit, all in one real call) |

## Summary

The page's CRUD already worked against the real backend, but with 3 real bugs
(field-name mismatch, wrong HTTP verb, phantom `is_primary`/`"online"`
values with no backend support) that were silently working around each
other. This sprint's real backend work: migration 117 (`is_primary` column
+ `tenant_limits.max_service_areas`), 3 new endpoints (`limits`, `validate`,
`set-primary`), and fixing the frontend API client to match the real
backend field names and HTTP verbs — all live-verified end-to-end against
the real seeded tenant (Demo AC Services, 1 real area at pincode 141001,
now correctly resolving to Ludhiana / Tier 2 and correctly enforcing the
1/5 plan limit).
