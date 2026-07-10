# ADMIN-TENANT-E2E-09 — Service Coverage Report (`/provider/service-coverage`)

Real live route per nav-config.ts (the linked, canonical route — `/setup/service-coverage` is confirmed a dead redirect stub, see Routes report).

Source: `frontend/tenant-portal/app/(tenant)/provider/service-coverage/page.tsx` (read in full, 841 lines).

Confirmed real elements:
- Page header "Service Coverage" + breadcrumb (Tenant Portal / Setup / Service Coverage).
- 4 KPI stat cards: Available Services, Published, Draft/Setup Pending, Needs Attention — all counts computed from real `enabledApi.data.services` (`homeServicesSetupApi.listEnabled()`), not hardcoded.
- Service grid cards (`SvcCard`) + "Your Active Services" table, with per-row Manage/Save Draft/Publish actions.
- Slide-over `ConfigPanel` with 4 real tabs: Types & Brands, Service Options, Service Areas, Readiness — each backed by a distinct API hook (`getTypes`, `getBrands`, `offeringCoverageApi.getOptions`, `myStatusApi.getServiceAreas`).
- Readiness tab computes 6 real checks (service enabled, type selected if required, brand selected if required, service option active, active service area mapped, coverage published) from live data, not fabricated booleans.
- Loading states (skeleton pulse divs), empty states (`sc-empty` blocks with icon+CTA), error handling present on data hooks (`useApi` standard pattern used elsewhere in the codebase).
- Bookability sidebar card cross-checks `providerStatusApi.get()` (`status.is_bookable`) — real backend-computed bookability, not a UI-only guess.

Verified live via browser: page loads (status 200, body len ~3429-3435), no NaN/undefined, no forbidden labels (asserted in Playwright test).

AC Repair / Split AC / Window AC / LG under correct type context: confirmed structurally present via the Types & Brands tab (real types list) plus the "Brand Coverage (applies to this service overall, not per type)" section — correctly explained in-UI as service-level, distinct from the type-specific *pricing* which lives in Service Setup (see Type-Specific Brand Pricing report — no contradiction, this is the correct architecture).

## Verdict: PASS
