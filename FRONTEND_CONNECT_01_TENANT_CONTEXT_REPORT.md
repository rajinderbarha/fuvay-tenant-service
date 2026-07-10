# FRONTEND-CONNECT-01 — Tenant Context Report

## Existing mechanism
`getTenantId()` in `frontend/tenant-portal/lib/api.ts` reads `localStorage.getItem("serviceos_tenant_id")`. Dozens of existing API functions already call it and append `tenant_id` as a query param or body field when present — never fabricated when absent (confirmed by reading ~15 call sites: they either omit the param or pass `tenant_id: tid` where `tid` can be `null`, which the backend then correctly rejects with `403 No tenant context` — verified live, see Live API Smoke report).

## New addition (this sprint)
`frontend/tenant-portal/lib/api-foundation/tenant-context.ts` — added because no explicit `getTenantContext()`/`requireTenantContext()`/`withTenantContext()` existed; pages either called `getTenantId()` directly with no presence check, or (in the case of `hooks/useTenant.ts`, pre-existing) had their own separate context hook for UI state. This file wraps `getTenantId()`:
- `getTenantContext(): TenantContext | null` — returns `{tenantId}` or `null`, never fabricates.
- `requireTenantContext(requestId?)` — throws `TenantContextMissingError` with the spec's exact message: `"Tenant context missing. Please select a business or login again."` (+ `Request ID: <id>` when available).
- `withTenantContext(fn, fallback)` — convenience for call sites that want a fallback instead of a throw.

Wired into 4 of the 12 new `tenant-modules.ts` functions that hit tenant-scoped endpoints (`getTenantServiceAreas`, `getTenantServicesSetup`, `getTenantAvailability`, `getTenantJobs`, `assignTechnician`, `saveTenantAvailability`) — these now call `requireTenantContext()` before issuing the request instead of silently sending `tenant_id: null`.

## Gap not closed this sprint
The dozens of pre-existing call sites in `lib/api.ts` that already do `const tid = getTenantId(); ...tenant_id: tid` were **not** retrofitted to call `requireTenantContext()` — that would mean touching ~40+ existing functions across a 4,100-line file, which is out of scope for "extend, don't bulldoze." They still silently pass `tenant_id: null` when context is missing, relying on the backend's `403 No tenant context` response (which IS handled correctly by the error-model/`ApiPermissionDeniedState` path). Functionally safe (backend never accepts a fake tenant_id), but not the same as failing fast client-side. Tracked in Remaining Blockers.

## Files
- `g:\serviceos\frontend\tenant-portal\lib\api-foundation\tenant-context.ts` (new, created this sprint)
- `g:\serviceos\frontend\tenant-portal\lib\api-foundation\tenant-modules.ts` (pre-existing this sprint, uses `requireTenantContext()`)
