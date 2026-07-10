# ADMIN-TENANT-E2E-08: Service Areas Report

**Date:** 2026-07-10  
**File:** `app/(tenant)/provider/service-areas/page.tsx`

## Features
- Full enterprise list with search and status filters (All / Active / Inactive)
- Coverage Readiness Hero (dark panel, CoverageRing SVG showing slot-usage %)
- 4 KPI cards: Total Areas, Primary Area, Coverage Health, Validation Issues
- Action Required panel for: no active areas, no primary set, limit reached
- Service area table: Area Name, State, District, City, Pincode, Zone/Tier, Primary, Status, Updated, Actions
- Detail drawer (slide-in right panel) with area summary, bookability impact, package limit impact
- Create wizard with validation preview panel (calls backend `validate` endpoint)
- Edit modal (city/zipcode locked in edit mode — "add new area to change")
- Delete confirm modal with "last active area" warning
- Set Primary confirm modal
- Coverage Summary sidebar + Coverage Rules sidebar + Recent Activity sidebar

## API Usage
- `providerServiceAreasApi.list()` — GET areas
- `providerServiceAreasApi.getLimits()` — GET limits
- `providerServiceAreasApi.create(payload)` — POST
- `providerServiceAreasApi.update(id, payload)` — PUT (also used for toggle is_active)
- `providerServiceAreasApi.delete(id)` — DELETE
- `providerServiceAreasApi.setPrimary(id)` — POST set-primary
- `providerServiceAreasApi.validate(...)` — POST validate (preview panel)
- `providerStatusApi.get()` — bookability status
- `tenantSetupApi.getActivity(1)` — activity feed

## Validation (Front-end)
`validateForm()` in `AreaWizard`:
- zipcode type: zipcode required
- city type: city required
- zone type: zone_name required
- radius type: lat/lng/radius all required
- state always required

## No direct fetch() calls — all via lib/api.ts
## No forbidden labels found

## Issues
- Permission variables `canCreate`, `canUpdate`, `canDelete`, `canSetPrimary` are all hardcoded to `true` (line 825). Granular permissions not yet returned by auth/me. Documented as known limitation in code comment.
