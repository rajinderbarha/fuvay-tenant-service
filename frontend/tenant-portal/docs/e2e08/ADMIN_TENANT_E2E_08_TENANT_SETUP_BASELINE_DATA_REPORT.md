# ADMIN-TENANT-E2E-08: Tenant Setup Baseline Data Report

**Date:** 2026-07-10  
**Method:** Static analysis only (no headless browser available)

## API Contracts Observed (via lib/api.ts usage in pages)

### Business Profile
- GET `/v1/provider/business-profile` — via `businessProfileApi.get()`
- PUT `/v1/provider/business-profile` — via `businessProfileApi.update()`
- POST `/v1/provider/business-profile/submit-review` — via `businessProfileApi.submitForReview()`

### Service Areas
- GET `/v1/provider/service-areas` — returns `{ areas: ProviderServiceArea[] }`
- GET `/v1/provider/service-areas/limits` — returns `{ max_service_areas, remaining_service_areas }`
- POST `/v1/provider/service-areas` — create
- PUT `/v1/provider/service-areas/{id}` — update
- DELETE `/v1/provider/service-areas/{id}` — delete
- POST `/v1/provider/service-areas/{id}/set-primary` — set primary
- POST `/v1/provider/service-areas/validate` — validate area

### Availability
- GET `/v1/provider/availability` — returns `{ rules: ProviderAvailabilityRule[] }`
- POST `/v1/provider/availability` — create rule
- PUT `/v1/provider/availability/{id}` — update rule
- DELETE `/v1/provider/availability/{id}` — delete rule
- POST `/v1/provider/availability/preset/{preset_id}` — apply preset
- DELETE `/v1/provider/availability/preset/{preset_id}` — remove preset

### Onboarding Checklist
- GET `/v1/provider/onboarding/status` — returns `ProviderOnboardingStatus`
- GET `/v1/provider/onboarding/items` — returns `{ items: ProviderOnboardingItem[] }`
- POST `/v1/provider/onboarding/refresh` — refresh status

## Data Shapes
All pages use typed interfaces from `lib/api.ts`. No hardcoded mock data found in setup pages.
All API calls go through `apiFetch` (centralized in `lib/api.ts`), not raw `fetch()`.
