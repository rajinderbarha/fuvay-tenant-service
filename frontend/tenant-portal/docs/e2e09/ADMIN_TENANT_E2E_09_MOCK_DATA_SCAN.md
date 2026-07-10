# E2E-09 Mock Data Scan

## Scanned Files
- `app/(tenant)/provider/service-coverage/page.tsx`
- `app/(tenant)/provider/service-setup/page.tsx`
- `app/(tenant)/tenant/setup/services/page.tsx`

## Checks Performed

### 1. Hardcoded Service Names
- **service-coverage**: Uses `svcLabel()` which resolves real names from `homeServicesSetupApi.listAvailable()`, only falls back to `Service #<id>` if API returns nothing — not a mock, it's a safe fallback
- **tenant/setup/services**: Uses `safeText(service.service_name)` — real API field

### 2. Fake Pricing
- No hardcoded price values anywhere in scope
- Admin floor/ceiling/fee values come from `homeServicesSetupApi.getTypePricing()` → `HsTypePricing`
- Brand pricing comes from `homeServicesSetupApi.getBrandPricing()` per type

### 3. Mock Enabled Services List
- No hardcoded mock services array — all service lists come from:
  - `homeServicesSetupApi.listEnabled()` (tenant-enabled services)
  - `homeServicesSetupApi.listAvailable()` (admin catalog)
  - `providerOfferingsApi.listEnabled()` (old deprecated page)

### 4. Hardcoded Status Values
- KPI counts are computed from real API responses
- Bookability status from `providerStatusApi.get()`

## Status: PASS — no mock data found
