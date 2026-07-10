# E2E-09 Service Enablement Report

## Does Tenant Have a Page to Enable/Disable Services?

**YES** — Two paths:

### 1. `/tenant/setup/services` (Primary)
- **File**: `app/(tenant)/tenant/setup/services/page.tsx`
- **API**: `homeServicesSetupApi.enable({ master_service_id })` / `homeServicesSetupApi.disable(masterServiceId)`
- **UX**: Service catalog cards; clicking "Set Up" opens a 5-step wizard that calls `homeServicesSetupApi.enable()` on first open
- **Scope guard**: Home Services only (`isHomeServicesTenant` guard from `lib/verticalGuard.ts`)
- **Disable**: `EnabledServicesList` component has a "Disable" button that calls `homeServicesSetupApi.disable()`

### 2. `/provider/service-setup` (Deprecated)
- Shows a yellow banner: "This page has moved. Open the new Home Services setup flow."
- Has a link to `/tenant/setup/services`
- Still renders the old `ServiceSetupWizard` (different wizard using `providerOfferingsApi`)
- Both the old and new wizards use real API calls — no mocks

## Status: PASS — enablement is fully wired to real backend APIs
