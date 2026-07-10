# FRONTEND-CONNECT-01 — Live API Smoke Report

Backend (`localhost:8000`) and Postgres were already running; verified with `curl.exe -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` → `200`.

## 1. Admin overview endpoints (unauthenticated → 401)
```
GET /v1/admin/dashboard/home-services-summary
→ 401 {"error_code":"UNAUTHORIZED","request_id":"req_d10c527ddff8", ...}
```

## 2. Admin login (200) + authenticated overview call
```
POST /v1/auth/login {"email":"admin@serviceos.local","password":"Password123!"} → 200, access_token issued
GET /v1/admin/dashboard/home-services-summary (Bearer <admin token>)
→ 200 {"success":true,"data":{"home_services_providers":1,"bookable_providers":1,"service_catalog_health":{"status":"healthy","active_services":15}, ...}}
```
Real data returned — this is exactly the endpoint `getAdminHomeServicesOverview()` (`lib/api-foundation/admin-modules.ts`) calls.

## 3. Tenant setup checklist endpoint — 401 then 403 (role mismatch)
```
GET /v1/provider/status (no auth) → 401 UNAUTHORIZED, request_id req_2e4e19f018f4
GET /v1/provider/status (admin Bearer token, wrong role/no tenant context) → 403 PERMISSION_DENIED, detail:"No tenant context", request_id req_cb89f244e704
```
This is exactly the endpoint `getTenantSetupChecklist()` (`lib/api-foundation/tenant-modules.ts` → `myStatusApi.getStatus()` → `providerStatusApi.get()`) calls.

## 4. Validation error (422)
```
POST /v1/auth/login {"email":"not-an-email"} → 422 VALIDATION_ERROR
{"errors":[{"field":"body.email","message":"Value error, Invalid email address","received":"not-an-email"},
           {"field":"body.password","message":"Field required", ...}], "request_id":"req_62bf91cf41fa"}
```
Confirms field-level errors (`field_errors`/`errors` array) plus `request_id` are present on 422 — this is what `parseErrorResponse()`/`toApiError()` in `lib/api-foundation/error-model.ts` expect.

## Endpoint-to-module mapping used for this smoke (documented per spec item 17)
| New API module function | REST endpoint curled |
|---|---|
| `getAdminHomeServicesOverview()` | `GET /v1/admin/dashboard/home-services-summary` + `GET /v1/admin/home-services/service-catalog/services` |
| `getTenantSetupChecklist()` | `GET /v1/provider/status` |

## Security check
No response body across all 6 calls above echoes the bearer token or any localStorage key. `request_id` is present on every error response (401 x2, 403 x1, 422 x1).
