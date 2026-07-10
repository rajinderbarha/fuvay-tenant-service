# ADMIN-TENANT-E2E-09 — Service Type Selection Report

Real backend endpoints (verified in `app/engines/admin_catalog/tenant_router.py`):
- `GET /v1/tenant/catalog/enabled-services/{tenant_service_id}/types` — loads real admin-catalog-approved types for the service.
- `PUT /v1/tenant/catalog/enabled-services/{tenant_service_id}/types` — persists tenant's selected type list.

Confirmed via direct psql against `tenant_service_types` (tenant `015efedb-dd92-41f4-97ef-cc2745437760`, AC Repair): both Split AC (`c86dfcf3-...`) and Window AC (`e27f6591-...`) rows exist and are `is_enabled=t`. This is real, persisted, currently-active data — not a fixture created for this test.

Frontend (`services/page.tsx`): Types step (`step === "types"`) renders each type from `typesApi.data.types`, lets the tenant toggle (unless `is_required`), shows "Required"/"Default" badges from real flags, and validates "Select at least one type to continue" before allowing Next. `saveTypesAction.execute()` calls the real `setTypes` endpoint, followed by `typePricingApi.refetch()` — i.e. type selection genuinely feeds into the pricing step's data (confirmed causal, not cosmetic).

On the Service Coverage page's `TypesBrandsTab`, the same type list is independently rendered and toggle-able for coverage purposes (separate save path, `homeServicesSetupApi.setTypes`), with an explicit UI note directing users to Service Setup for type-specific brand pricing.

## Verdict: PASS
