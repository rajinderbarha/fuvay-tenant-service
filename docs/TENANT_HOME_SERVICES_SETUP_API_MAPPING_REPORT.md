# Tenant Home Services Setup — API Mapping Report

## APIs Used vs Spec

| Spec Route | Actual API Call | Endpoint |
|-----------|----------------|----------|
| GET /v1/tenant/home-services/catalog/available | `homeServicesSetupApi.listAvailable()` | `GET /v1/tenant/catalog/home-services/available-services?tenant_id=…` |
| GET /v1/tenant/home-services/services | `homeServicesSetupApi.listEnabled()` | `GET /v1/tenant/catalog/home-services/enabled-services?tenant_id=…` |
| POST /v1/tenant/home-services/services/setup-draft | `homeServicesSetupApi.enable({ master_service_id })` | `POST /v1/tenant/catalog/enable-service?tenant_id=…` |
| PUT /v1/tenant/home-services/services/{id}/setup types | `homeServicesSetupApi.setTypes(id, typeIds)` | `PUT /v1/tenant/catalog/enabled-services/{id}/types` |
| PUT /v1/tenant/home-services/services/{id}/setup pricing | `homeServicesSetupApi.setTypePricing(id, typeId, min, max)` | `PUT /v1/tenant/catalog/enabled-services/{id}/types/{typeId}/pricing` |
| PUT /v1/tenant/home-services/services/{id}/setup brands | `homeServicesSetupApi.setBrandPricing(id, brandId, min, max)` | `PUT /v1/tenant/catalog/enabled-services/{id}/brands/{brandId}/pricing` |
| POST /v1/tenant/home-services/services/{id}/publish | `homeServicesSetupApi.publish(id)` | `POST /v1/tenant/catalog/enabled-services/{id}/publish` |
| POST /v1/tenant/home-services/services/{id}/disable | `homeServicesSetupApi.disable(masterServiceId)` | `POST /v1/tenant/catalog/disable-service?tenant_id=…&master_service_id=…` |
| POST /v1/tenant/home-services/price-options/preview | `homeServicesSetupApi.pricePreview({ tenant_min_price, tenant_max_price })` | `POST /v1/tenant/catalog/price-options/preview` |
| GET /v1/tenant/service-areas | `providerServiceAreasApi.list()` | `GET /v1/tenant/service-areas` |

## Data Flows

**Service Catalog:**
- `listAvailable()` returns `{ services: AdminMasterServiceRow[] }` with admin-approved services only
- Tenant cannot create free-text services — catalog is admin-controlled

**Type Setup:**
1. `getTypes(tenantServiceId)` → shows available types
2. `setTypes(tenantServiceId, typeIds)` → saves selection
3. `getTypePricing(tenantServiceId)` → loads floor/ceiling + existing tenant prices

**Pricing:**
1. Tenant inputs min/max per type
2. `pricePreview({ tenant_min_price, tenant_max_price })` → returns Low/Mid/High
3. `setTypePricing(id, typeId, min, max)` → persists on Next

**Brand Override:**
1. `getBrandPricing(tenantServiceId)` → lists brands with `can_override_price`
2. `setBrandPricing(id, brandId, min, max)` → persists overrides
3. `pricePreview(...)` → per-brand Low/Mid/High

**Publish:**
1. `saveDraft(tenantServiceId)` → saves without going live
2. `publish(tenantServiceId)` → goes live (requires active service area)

## Price Resolution

```
brand override price → type price → service base price
```

Most specific wins. Platform fee applied by backend before returning customer price options.
