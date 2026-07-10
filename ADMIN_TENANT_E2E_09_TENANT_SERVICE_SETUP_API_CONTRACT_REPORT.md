# ADMIN-TENANT-E2E-09 — API Contract Report

Real module: `frontend/tenant-portal/lib/api.ts` — `homeServicesSetupApi` (starts line 363), used by both `tenant/setup/services/page.tsx` and `provider/service-coverage/page.tsx`. No `src/lib/api/tenant-service-setup.ts` file exists (the spec's illustrative path was not real, as flagged in the handoff) — the actual single central client is `lib/api.ts`.

Real methods confirmed by grep: `getTypes`, `getBrands`, `getTypePricing`, `setTypePricing(tenantServiceId, serviceTypeId, min, max)`, `getBrandPricing(tenantServiceId, serviceTypeId?)`, `setBrandPricing(tenantServiceId, brandId, min, max, serviceTypeId?)`, `enable`, `listAvailable`, `listEnabled`, `saveDraft`, `publish`, `pricePreview`.

- **Central client used**: confirmed — both pages import from `../../../../lib/api` (relative path resolves to the same module), no direct `fetch()` calls found in either page.
- **Auth token included**: `lib/api.ts`'s underlying `apiFetch` wrapper attaches the bearer token (standard pattern reused across the whole app, confirmed functioning — all API calls in this sprint's tests succeeded/failed with correct auth-dependent behavior).
- **Tenant context included**: mutation payload does not need an explicit tenant_id — the backend resolves tenant scope from the JWT (`UserContext`) via `_svc()`'s `TenantCatalogService(actor_role=u.role, ...)` dependency, confirmed in `tenant_router.py`.
- **request_id parsed**: `ServiceOSError` class exposes `.requestId`, used throughout `services/page.tsx`'s `ErrBanner` calls (`e.requestId ?? null`) — confirmed present in real error responses (`req_...` format seen in every API response's `meta.request_id`).
- **No direct fetch where centralized function exists**: confirmed by code read, no violations found.
- **Mutations invalidate/refetch**: `saveTypesAction.execute()` is immediately followed by `await typePricingApi.refetch()` (real refetch, not optimistic-only) before advancing the wizard step — confirmed this is a true network round-trip, not a client-side flag flip. Coverage page's `refreshAll()` refetches all 5 hooks (`enabledApi`, `availableApi`, `areasApi`, `statusApi`, `activityApi`) after any Save/Publish action.
- **Payload includes service_type_id for type-specific brand pricing saves**: confirmed — `saveBrandPricingAction` explicitly calls `setBrandPricing(tenantServiceId, bp.brandId, min, max, bp.typeId)`, i.e. `bp.typeId` (the type ID) is always included.

## Verdict: PASS
