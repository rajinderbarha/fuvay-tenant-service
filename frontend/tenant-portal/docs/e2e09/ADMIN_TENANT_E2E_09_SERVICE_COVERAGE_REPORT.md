# E2E-09 Service Coverage Report

## Page: `/provider/service-coverage`
**File**: `app/(tenant)/provider/service-coverage/page.tsx`

## API Usage
- `homeServicesSetupApi.listEnabled()` — fetches real tenant-enabled services
- `homeServicesSetupApi.listAvailable()` — fetches master service catalog for name lookup
- `myStatusApi.getServiceAreas()` — real area data
- `providerStatusApi.get()` — real bookability status
- `myStatusApi.getAuditLog(10)` — real activity log

## Real Service Names
- `svcLabel()` function resolves service names: first checks `tenant_display_name`, then `nameMap[master_service_id]` (populated from `listAvailable()`), only falls back to `Service #<uuid-prefix>` if both are missing
- This is correct behavior — names come from real API responses

## Type/Brand Configuration Panel
- Slide-over `ConfigPanel` with 4 tabs: **Types & Brands**, **Service Options**, **Service Areas**, **Readiness**
- `TypesBrandsTab` fetches types and brands via `homeServicesSetupApi.getTypes()` / `.getBrands()` per `tenant_service_id`
- Available brands fetched via `providerBrandApi.getAvailableForService(master_service_id)`
- Brand coverage is correctly documented as service-level (not per-type) — a comment explains the architecture clearly and links per-type brand pricing to `/tenant/setup/services`

## KPI Cards
- Available Services, Published, Draft/Setup Pending, Needs Attention — all computed from real API data

## Status: PASS — real APIs, real data, correct architecture
