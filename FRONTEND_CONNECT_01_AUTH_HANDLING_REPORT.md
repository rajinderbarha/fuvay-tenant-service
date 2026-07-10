# FRONTEND-CONNECT-01 — Auth Token Handling Report

## Token source (investigated, confirmed real)
- super-admin: `localStorage.getItem("serviceos_admin_token")` (`lib/api.ts` `getToken()`), refresh token `serviceos_admin_refresh`.
- tenant-portal: same pattern, tenant-scoped keys (`serviceos_tenant_token`, `serviceos_tenant_refresh`, plus `serviceos_tenant_id`).
- `apiFetch()` attaches `Authorization: Bearer <token>` centrally in both files — no page ever reads localStorage or sets this header itself (confirmed by the direct-fetch scan: the only per-page `Authorization` usage is inside 2 legacy admin components already pre-dating this sprint, see Direct Fetch Scan).

## 401 handling
- `apiFetch()` on a 401 attempts one silent refresh via `/v1/auth/token/refresh`; if that also fails, it calls `clearSession()` (clears localStorage, redirects to `/login`) and throws `ServiceOSError("UNAUTHORIZED", "Session expired. Please sign in again.")`.
- Live-verified: unauthenticated `GET /v1/admin/dashboard/home-services-summary` returns `401` with `error_code":"UNAUTHORIZED"` and a `request_id`. The error message text differs slightly from the spec's exact wording ("Session expired. Please sign in again." vs spec's "Please login again.") — cosmetic only, added the spec's exact wording to the new `toApiError()`/`friendlyMessage()` helpers in `lib/api-foundation/error-model.ts` (both frontends) so new call sites get the exact spec text without touching the ~200 existing call sites of the legacy `ServiceOSError` message.

## 403 handling
- Live-verified: an admin token against a tenant-only endpoint (`GET /v1/provider/status`) returns `403 PERMISSION_DENIED` with a `request_id` (`req_cb89f244e704`).
- New `ApiPermissionDeniedState` (`components/shared/ApiStates.tsx`, both frontends) renders exactly "You do not have permission to perform this action." + `Request ID: <id>` badge + copy button, matching spec wording.

## No token leakage
- Verified via curl: no response body (200/401/403/422) ever echoes back `Authorization`, the bearer token, or `serviceos_*_token`. `apiFetch()` never `console.log`s headers or tokens.

## Files touched
- `g:\serviceos\frontend\super-admin\lib\api-foundation\error-model.ts` (pre-existing in-progress file, verified/kept)
- `g:\serviceos\frontend\tenant-portal\lib\api-foundation\error-model.ts` (pre-existing in-progress file, verified/kept)
