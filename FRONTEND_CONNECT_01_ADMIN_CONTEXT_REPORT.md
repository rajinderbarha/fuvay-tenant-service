# FRONTEND-CONNECT-01 — Admin Context Report

## Existing mechanism
Admin pages authenticate via `serviceos_admin_token` (separate localStorage namespace from tenant tokens) and hit `/v1/admin/*` endpoints, which never require `tenant_id` unless the route itself is a tenant-detail route (e.g. `getAdminTenantDetail(tenantId)` takes an explicit `tenantId` argument — never reads it from any tenant-context localStorage key). Verified by reading `adminTenantApi.get()` and the 8 new admin module wrappers — none reference `getTenantId()`.

## New addition (this sprint)
`frontend/super-admin/lib/api-foundation/admin-context.ts`:
- `isAdminRoute(pathname)` — `pathname.startsWith("/admin")`.
- `AdminAccessDeniedError` — carries the spec's exact 403 message + request_id.
- `requireAdminAccess(hasAccess, requestId?)` — throws `AdminAccessDeniedError` when a permission check fails.

Live-verified: an admin-authenticated request against a tenant-only endpoint (`GET /v1/provider/status`) correctly returns `403` rather than silently falling back to a tenant API — confirms the backend enforces this boundary regardless of frontend behavior, and the frontend's `ApiPermissionDeniedState`/`toApiError()` path renders it correctly (message + request_id + no fallback to fake data).

## No silent fallback to tenant APIs
Grepped `frontend/super-admin/lib/api.ts` for any call that reads a tenant-scoped localStorage key (`serviceos_tenant_*`) — none found. Admin and tenant portals are fully separate Next.js apps (`super-admin` vs `tenant-portal`) with separate `lib/api.ts` files and separate localStorage namespaces, so there is no code path where an admin page could accidentally call a tenant API with tenant context.

## Files
- `g:\serviceos\frontend\super-admin\lib\api-foundation\admin-context.ts` (new, created this sprint)
