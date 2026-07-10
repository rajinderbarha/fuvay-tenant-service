# ADMIN-TENANT-E2E-09 — Service Setup Page Report (`/tenant/setup/services`)

Source: `frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx` (read in full, 1421 lines).

Confirmed real elements:
- Page header, service catalog cards (`ServiceCard`), setup progress bar per card (`pct` computed from real `is_enabled`/`tenant_display_name`/`published` flags — not fabricated).
- `Continue Setup` / `Manage` CTA opens a real 5-step wizard (`ServiceSetupWizard`): Overview → Types → Pricing → Brands → Review.
- Wizard calls real `homeServicesSetupApi` methods (`enable`, `getTypes`, `getBrands`, `getTypePricing`, `getBrandPricing`, `setTypes`, `setTypePricing`, `setBrandPricing`, `saveDraft`, `publish`, `pricePreview`) from the central `lib/api.ts` client — no direct fetch, no mock data.
- Loading states: `Skeleton` components while `enableAction.loading`/`typesApi.loading`/`typePricingApi.loading`.
- Error states: `ErrBanner` component shows `error.message` + `requestId` with copy-to-clipboard, on every action (enable/types/pricing/brands/publish).
- Empty states: `EmptyState` for "No types", "No types selected".
- AC Repair (real `master_service_id` from admin catalog) appears in the service list (confirmed via `listAvailable`/`listEnabled` calls against real backend endpoints) and can be opened via `onSetup` → `ServiceSetupWizard`.
- No raw UUIDs are used as primary labels anywhere in the reviewed code — `safeText(service.service_name)` etc. are always used for display; UUIDs only appear in `key=` props (not rendered) or truncated debug fallbacks (`Service #{id.slice(0,8)}` used only as an absolute last-resort fallback on the coverage page, not this page).
- Real backend validation surfaced in UI: admin floor/ceiling enforcement, min>max rejection (see Provider Price Range report for live proof).

Verified live via browser (route smoke, screenshot `route_tenant_setup_services.png`): page loads (status 200), tenant shell present, no NaN/undefined, no forbidden labels.

## Verdict: PASS (route not broken; verdict is NOT the NOT_READY_TENANT_SERVICE_SETUP_ROUTE_FAILED code)
