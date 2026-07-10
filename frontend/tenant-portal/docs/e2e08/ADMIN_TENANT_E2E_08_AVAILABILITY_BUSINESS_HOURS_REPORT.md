# ADMIN-TENANT-E2E-08: Availability / Business Hours Report

**Date:** 2026-07-10  
**File:** `app/(tenant)/tenant/setup/availability/page.tsx`  
(accessed via `/provider/availability` redirect → `/tenant/setup/availability`)

## Features
- 4 Quick Preset cards: Standard Hours (Mon–Sat 09–19), Weekdays Only (Mon–Fri 09–18), Emergency Service (All days 08–22), Custom Schedule
- Preset apply/remove with confirm modal
- Weekly Schedule table: Mon–Sun with per-day status (Open/Closed), hours, edit/delete actions
- 5-step Add/Edit Wizard: Who → Days → Hours → Slots → Review & Save
- Slot Preview Panel: shows actual customer-visible booking slots for each day (client-side generation)
- Holidays & Exceptions panel (local-state only; backend endpoint not yet implemented — warned in UI)
- Recent Activity sidebar
- Scope types: All Services / Specific Service / Staff Member / Service Area

## API Usage
- `providerAvailabilityApi.list()` — GET rules
- `providerAvailabilityApi.create(payload)` — POST
- `providerAvailabilityApi.update(id, payload)` — PUT
- `providerAvailabilityApi.delete(id)` — DELETE
- `providerAvailabilityApi.applyPreset(id)` — POST preset (with fallback to manual CRUD if 404)
- `providerAvailabilityApi.deletePreset(id)` — DELETE preset (with fallback)
- `providerStatusApi.get()` — bookability status
- `providerTeamMembersApi.list()` — staff options for scope
- `providerServiceAreasApi.list()` — area options for scope
- `tenantSetupApi.getActivity(1)` — activity

## Time Validation (Fix D)
Step 3 (Hours) validates end > start:
- `validateStep(3)` returns "End time must be after start time." if `w.start >= w.end`
- Visual feedback: border turns danger color, inline error message shown
- `detectIssues()` also catches `r.start_time >= r.end_time` in existing rules (severity: danger, shown in issues banner)

**Verdict: Time validation IS implemented — both in wizard step validation and in post-load issue detection.**

## No direct fetch() calls
## No forbidden labels found
