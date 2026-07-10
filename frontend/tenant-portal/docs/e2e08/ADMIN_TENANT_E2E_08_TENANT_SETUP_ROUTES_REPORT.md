# ADMIN-TENANT-E2E-08: Tenant Setup Routes Report

**Date:** 2026-07-10  
**Scope:** app/(tenant)/ — setup-related pages

## Routes Identified

| Route | File | Status |
|-------|------|--------|
| `/onboarding-status` | `app/(tenant)/onboarding-status/page.tsx` | EXISTS — full setup checklist |
| `/setup/checklist` | `app/(tenant)/setup/checklist/page.tsx` | CREATED — redirects to /onboarding-status |
| `/profile` | `app/(tenant)/profile/page.tsx` | EXISTS — full business profile page (5 tabs) |
| `/provider/service-areas` | `app/(tenant)/provider/service-areas/page.tsx` | EXISTS — full service areas page |
| `/provider/availability` | `app/(tenant)/provider/availability/page.tsx` | EXISTS — redirect to /tenant/setup/availability |
| `/tenant/setup/availability` | `app/(tenant)/tenant/setup/availability/page.tsx` | EXISTS — full availability page |
| `/tenant/setup/services` | `app/(tenant)/tenant/setup/services/page.tsx` | EXISTS |
| `/setup/service-coverage` | `app/(tenant)/setup/service-coverage/page.tsx` | EXISTS |

## Navigation Config
The TenantLayout sidebar links to these pages using `activeNav` keys:
- `"onboarding-status"` → `/onboarding-status`
- `"profile"` → `/profile`
- `"provider-service-areas"` → `/provider/service-areas`
- `"provider-availability"` → `/provider/availability` (then redirects)

## Redirect Chain
`/provider/availability` → redirects via `router.replace("/tenant/setup/availability")` (immediate, no flash)

## Summary
All 4 core setup routes are functional. A new `/setup/checklist` alias page was created. No broken hrefs or missing route registrations found.
