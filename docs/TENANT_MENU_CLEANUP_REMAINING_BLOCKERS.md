# Tenant Menu Cleanup — Remaining Blockers

## P0 Blockers

None.

## P1 Items (Non-blocking)

### 1. Service Coverage Not in Sidebar

`/provider/service-coverage` page still exists and is functional but is no longer in the sidebar.
Access is possible only via direct URL or Setup Wizard step links.

**Impact:** Tenants cannot navigate to Service Coverage from the sidebar.
**Mitigation:** The Setup Checklist links to `/provider/service-coverage` for the "coverage_configured" step.
Users can still access it from there.

### 2. `provider_price_override` vs Separate Min/Max

The `EnableOfferingPayload` supports `provider_price_override` (single value) but not separate `provider_min_price`/`provider_max_price`.
The pricing preview uses min/max inputs; only `min` is saved as `provider_price_override`.

**Impact:** Max price is captured in the UI for preview purposes only but not persisted via the offerings API.
The `homeServicesSetupApi.setTypePricing` endpoint supports full min/max per service type — this would require connecting the offering `provider_enabled_offering_id` to the tenant service catalog `tenant_service_id`.

**Recommendation:** Future sprint — link offering ID to tenant catalog service ID and call `setTypePricing` for full min/max persistence.

## P2 Items (Nice-to-have)

### 1. Admin-Defined Price Floor/Ceiling Not Shown

The pricing step does not show the admin-defined floor/ceiling for the provider's allowed range.
This information is in `HsTypePricing.admin_floor_price` / `admin_ceiling_price` but requires a `tenantServiceId`.

### 2. Service Coverage Deprecation Message

`/provider/service-coverage` has no deprecation notice and is still accessible directly.
Low priority since it's not in the sidebar and remains a valid configuration page.
