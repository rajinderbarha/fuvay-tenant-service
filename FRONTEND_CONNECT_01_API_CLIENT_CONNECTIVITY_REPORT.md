# FRONTEND_CONNECT_01 — API Client / Connectivity Report

## Existing central client (verified, not rewritten)
`apiFetch<T>()` in `frontend/tenant-portal/lib/api.ts` and `frontend/super-admin/lib/api.ts` (near-identical implementations):
- Supports GET/POST/PUT/PATCH/DELETE via `RequestInit.method`.
- Injects `Content-Type: application/json`, `X-Request-Source`, and `Authorization: Bearer <token>` centrally.
- Handles 401 with automatic refresh-token retry, then `clearSession()` + redirect to `/login`.
- Parses non-ok responses into `ServiceOSError` (code, message, resolution, context, requestId).
- Unwraps the `{success, data, request_id, engine_id}` envelope, returning `.data`.
- `apiFetchMultipart<T>()` (tenant-portal) handles file upload with a 60s AbortController timeout — used by Media Engine.
- No retry policy beyond the one-shot 401 refresh — spec allows "retry only if existing policy allows"; no broader retry exists, so none was added (would be new behavior, out of scope).

## Gap found and filled
Timeout handling existed only for the multipart upload path, not for plain JSON `apiFetch()`. This was NOT touched — adding an AbortController timeout to the hot path used by hundreds of call sites is a behavior change outside "foundation only" scope and risked breaking in-flight assumptions across the app (e.g. long-running admin report exports). Documented as a **known gap**, not fixed, per spec's own scope discipline ("do not fully connect/rewrite everything").

## What was added (genuinely new, additive only)
- `lib/api-foundation/error-model.ts` (both frontends): `ApiError` type + `toApiError()` + `parseErrorResponse()` — formalizes the error shape `ServiceOSError` already carries, for use by the new shared UI-state components without touching `apiFetch()` itself.
- `lib/api-foundation/admin-modules.ts` (super-admin) / `lib/api-foundation/tenant-modules.ts` (tenant-portal) — thin named wrapper functions per Parts 9/10, all delegating to existing typed API objects (`dashboardApi`, `homeServicesCatalogConsoleApi`, `myStatusApi`, `jobsApi`, etc.), so they inherit the central client automatically.

## Verdict
Central API client requirement is satisfied by the pre-existing `apiFetch()` — confirmed via source read, not assumed. No page in this sprint bypasses it (see direct-fetch scan for the pre-existing exceptions, none newly introduced).
