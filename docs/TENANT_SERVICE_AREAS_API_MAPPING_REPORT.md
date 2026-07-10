# Tenant Service Areas API Mapping Report

## Route
`/provider/service-areas` → `app/(tenant)/provider/service-areas/page.tsx`

## API Mapping

| Spec API | Actual API | Client | Status |
|---|---|---|---|
| GET /v1/tenant/service-areas | GET /v1/tenant/service-areas | providerServiceAreasApi.list() | ✅ Used |
| POST /v1/tenant/service-areas | POST /v1/tenant/service-areas | providerServiceAreasApi.create() | ✅ Used |
| PUT /v1/tenant/service-areas/{id} | PATCH /v1/tenant/service-areas/{id} | providerServiceAreasApi.update() | ✅ Used |
| DELETE /v1/tenant/service-areas/{id} | DELETE /v1/tenant/service-areas/{id} | providerServiceAreasApi.delete() | ✅ Used |
| GET /v1/tenant/package | GET /v1/provider/subscription-status | tenantSetupApi.getPackage() | ✅ Used (for limit) |
| GET /v1/provider/status | GET /v1/provider/status | providerStatusApi.get() | ✅ Used (blockers) |
| GET /v1/tenant/activity | GET /v1/provider/activity | tenantSetupApi.getActivity() | ✅ Used |
| GET /v1/platform/locations/resolve-zipcode | GET /v1/platform/locations/resolve-zipcode | Direct fetch in ZipcodeValidationPanel | ✅ Attempted; falls back to baseline map if 404 |
| POST /v1/tenant/service-areas/{id}/enable | PATCH (is_active: true) | providerServiceAreasApi.update() | ✅ Used via toggle |
| POST /v1/tenant/service-areas/{id}/disable | PATCH (is_active: false) | providerServiceAreasApi.update() | ✅ Used via toggle |

## Zipcode Validation
- Attempts `GET /v1/platform/locations/resolve-zipcode?zipcode=<zip>` with Bearer token
- If endpoint returns 200: populates city/state/district/tier from response
- If endpoint returns non-200 or is missing: uses baseline map (141001 → Ludhiana, Punjab, Mid)
- Fallback prevents blocking the user from saving

## Package Limit
- `service_area_limit` field from `/v1/provider/subscription-status`
- Falls back to constant AREA_LIMIT = 5 if field is absent

## Pre-existing api.ts TS errors
- lib/api.ts: 16 pre-existing TS2687 errors (duplicate modifier declarations) — not introduced by this sprint

## Service Areas page: 0 new TypeScript errors.
