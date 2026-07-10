# E2E-09 API Contract Report

## APIs Used in Service Setup Pages

### `/provider/service-coverage`
| Function | Source | Endpoint |
|----------|--------|----------|
| `homeServicesSetupApi.listEnabled()` | `lib/api.ts` | GET /v1/home-services/setup/enabled |
| `homeServicesSetupApi.listAvailable()` | `lib/api.ts` | GET /v1/home-services/setup/available |
| `homeServicesSetupApi.getTypes(tenantServiceId)` | `lib/api.ts` | GET /v1/home-services/setup/{id}/types |
| `homeServicesSetupApi.getBrands(tenantServiceId)` | `lib/api.ts` | GET /v1/home-services/setup/{id}/brands |
| `homeServicesSetupApi.setTypes(tenantServiceId, typeIds)` | `lib/api.ts` | PUT /v1/home-services/setup/{id}/types |
| `homeServicesSetupApi.setBrands(tenantServiceId, brandIds)` | `lib/api.ts` | PUT /v1/home-services/setup/{id}/brands |
| `homeServicesSetupApi.saveDraft(tenantServiceId)` | `lib/api.ts` | POST /v1/home-services/setup/{id}/draft |
| `homeServicesSetupApi.publish(tenantServiceId)` | `lib/api.ts` | POST /v1/home-services/setup/{id}/publish |
| `offeringCoverageApi.getOptions(masterServiceId)` | `lib/api.ts` | GET /v1/offering-coverage/{id}/options |
| `providerBrandApi.getAvailableForService(masterServiceId)` | `lib/api.ts` | GET /v1/provider/brands/available/{id} |
| `myStatusApi.getServiceAreas()` | `lib/api.ts` | GET /v1/provider/me/areas |
| `providerStatusApi.get()` | `lib/api.ts` | GET /v1/provider/status |
| `myStatusApi.getAuditLog(n)` | `lib/api.ts` | GET /v1/provider/me/audit-log |

### `/tenant/setup/services`
| Function | Source | Notes |
|----------|--------|-------|
| `homeServicesSetupApi.listAvailable()` | `lib/api.ts` | Real catalog |
| `homeServicesSetupApi.listEnabled()` | `lib/api.ts` | Tenant's enabled services |
| `homeServicesSetupApi.enable({ master_service_id })` | `lib/api.ts` | Enable a service |
| `homeServicesSetupApi.disable(masterServiceId)` | `lib/api.ts` | Disable a service |
| `homeServicesSetupApi.getTypes(tenantServiceId)` | `lib/api.ts` | |
| `homeServicesSetupApi.getBrands(tenantServiceId)` | `lib/api.ts` | |
| `homeServicesSetupApi.getTypePricing(tenantServiceId)` | `lib/api.ts` | |
| `homeServicesSetupApi.getBrandPricing(tsid, typeId)` | `lib/api.ts` | Per-type brand pricing |
| `homeServicesSetupApi.setTypes(tsid, typeIds)` | `lib/api.ts` | |
| `homeServicesSetupApi.setTypePricing(tsid, typeId, min, max)` | `lib/api.ts` | |
| `homeServicesSetupApi.setBrandPricing(tsid, brandId, min, max, typeId)` | `lib/api.ts` | Type-scoped |
| `homeServicesSetupApi.saveDraft(tsid)` | `lib/api.ts` | |
| `homeServicesSetupApi.publish(tsid)` | `lib/api.ts` | |
| `homeServicesSetupApi.pricePreview({ min, max })` | `lib/api.ts` | Preview Low/Mid/High |
| `providerStatusApi.refresh()` | `lib/api.ts` | Post-publish bookability |
| `providerServiceAreasApi.list()` | `lib/api.ts` | |

## Direct fetch() Calls
**0 found** — all API calls go through the `lib/api.ts` abstraction layer.

## Status: PASS — all API contracts use lib/api.ts, no raw fetch()
