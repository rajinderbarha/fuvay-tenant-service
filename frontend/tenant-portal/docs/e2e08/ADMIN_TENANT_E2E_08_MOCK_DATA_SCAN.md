# ADMIN-TENANT-E2E-08: Mock Data Scan

**Date:** 2026-07-10  
**Scope:** Setup pages (onboarding-status, profile, service-areas, availability)

## Findings

### onboarding-status/page.tsx
No mock data. All data from `providerOnboardingApi`, `providerPackageApi`.

### profile/page.tsx
| Location | Value | Classification |
|----------|-------|----------------|
| Line ~739 | "Air Conditioner Services" (Category field) | HARDCODED — should come from API |
| Line ~1083 | "Air Conditioner Services" (Edit modal category) | HARDCODED — same |
| Line ~56 (initial state) | `useState("Your Business")` in dashboard/page.tsx | IN dashboard page (not profile), gets overwritten by API |
| profile/page.tsx line ~586 | `safeText(biz?.business_name,"Your Business")` | VALID FALLBACK — not mock data |
| profile/page.tsx line ~592 | `"Home Services"` | MINOR HARDCODE — plan type text |

### provider/service-areas/page.tsx
No mock data. All data from `providerServiceAreasApi`, `providerStatusApi`, `tenantSetupApi`.

### tenant/setup/availability/page.tsx
No mock data. Preset configurations (Standard Hours, Weekdays Only, etc.) are valid UI presets, not mock API data. All availability rules loaded from `providerAvailabilityApi`.

## Summary
- 2 hardcoded category strings ("Air Conditioner Services") in `profile/page.tsx` — P2 quality issue
- "Your Business" and "Home Services" appear as safe fallbacks when API data is null
- No mock/fake API responses or stub data found in setup pages
- No `setTimeout` mocks or fake delays found
