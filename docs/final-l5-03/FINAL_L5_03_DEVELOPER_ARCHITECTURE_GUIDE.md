# FINAL-L5-03 — Developer Architecture Guide

## Canonical API client usage
Every API call must go through the app's `lib/api.ts` (or `lib/api/client.ts` for customer-app). Never call `fetch()` directly in a page/component unless it's a documented special case (e.g. a pre-signed storage-upload URL — see `media/page.tsx` for the pattern).

## How to add an API module
Add a typed domain object to `lib/api.ts`, e.g.:
```ts
export const myDomainApi = {
  list: (params?: MyParams) => apiFetch<MyListResponse>(`/v1/my-domain?${qs(params)}`),
  get: (id: string) => apiFetch<MyDetail>(`/v1/my-domain/${id}`),
};
```
For `EnterpriseDataGrid`-style paginated list pages, use the shared `apiFetchPaginatedRaw(endpoint, params)` helper (super-admin) instead of hand-rolling a fetch — it inherits auth, 401-refresh, and `request_id` preservation for free.

## How to handle errors
Catch `ServiceOSError`, read `.message`/`.requestId`/`.code`. Never construct a plain `new Error(json?.error?.message)` from a raw response — that discards `request_id` and 401-refresh handling (this was exactly the bug this sprint fixed in 5 pages).

## How to add permissions
- Tenant read-only UI gating: use `isTenantReadOnly()`.
- Tenant-owner-vs-other-role UI gating: use `isTenantOwnerRole(role)`.
- Super-admin permission-string gating: use `usePermissions().has("permission.key")` (see `hooks/usePermissions.ts`) — under-adopted (3 consumers) but the correct pattern to extend, not reinvent.
- Never write a new raw `role === "..."` comparison — check first whether an existing helper covers your case.

## How to use tenant context
`getTenantId()`/`getUserRole()`/`getUserId()` from `lib/api.ts`. Never hardcode a tenant ID in a tenant-facing page. Admin cross-tenant tools may use a documented dev-convenience default for an *input field*, never as a silent fallback that bypasses the actual selected/authenticated tenant.

## How to add a route
Add to `lib/page-registry.ts`/`lib/nav-config.ts` (per-app). Full route-registry redesign is scoped to FINAL-L5-04/05, not this guide.

## How to use shared forms
No schema-validation library exists yet — use controlled inputs + inline required-checks + backend-authoritative validation. Never duplicate a backend business calculation (fee/deduction/pricing) as authoritative in a form; a live preview calling the real backend endpoint is fine, a client-side formula used as the actual submitted value is not.

## How to use shared tables
Use `EnterpriseDataGrid` with a typed `fetchFn: (params: GridParams) => Promise<GridData>` (both types now exported from `EnterpriseDataGrid.tsx`).

## How to add query keys / invalidate caches
No query-cache library exists — each `useApi(fetcher, deps)` instance is independent. To "invalidate" after a mutation, explicitly call `.refetch()` on every affected hook instance (see `TenantLayout.tsx`'s refresh button for the pattern: `statusApi.refetch(); pkgApi.refetch(); creditApi.refetch(); ...`).

## How to write browser tests
Use real Chromium (`chromium.launch()`), zero mocking. Wait for hydration before interacting with any form (`waitFunction` checking for `__reactFiber`/`__reactProps` on the target element) — do not use a fixed `waitForTimeout` as your only wait, since dev-mode Turbopack compiles routes lazily and a fixed delay races against that (root-caused in FINAL-L5-01E). Warm routes with a `curl` before a real test batch when testing a freshly-restarted dev server.

## Deprecated patterns
See `FINAL_L5_03_DEPRECATED_PATTERN_GUIDE.md`.
