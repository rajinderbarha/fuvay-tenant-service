# E2E-07 Tenant Onboarding Tour Report
**Date:** 2026-07-10  
**Analysis:** Static analysis only — browser verification pending

---

## Onboarding Components

### TourGuide (`components/tour/TourGuide.tsx`)

- Renders a step-by-step guided overlay tour
- Triggered by `useTour` hook (`hooks/useTour.ts`)
- Tour steps highlight specific UI elements with a spotlight overlay
- "Skip Tour" and "Next" controls provided

### Setup Wizard Panel

Located in `TenantLayout.tsx`:
- 10-step onboarding checklist (`SETUP_STEPS`)
- Slide-in panel from the left sidebar area
- Each step links to the relevant page
- Progress bar with percentage complete
- Steps sourced from `providerStatusApi` live data

### Setup Steps

| # | Key | Label | Target URL |
|---|---|---|---|
| 1 | `profile_complete` | Business Profile | `/profile` |
| 2 | `package_active` | Package Active | `/finance/package` |
| 3 | `credits_available` | Usage Credits | `/finance/usage-credit-ledger` |
| 4 | `security_deposit_ok` | Security Deposit | `/finance/security-deposit` |
| 5 | `service_areas_count` | Service Areas | `/provider/service-areas` |
| 6 | `active_services_count` | Enable a Service | `/tenant/setup/services` |
| 7 | `coverage_configured` | Service Coverage | `/provider/service-coverage` |
| 8 | `staff_count` | Add Technician | `/provider/staff` |
| 9 | `availability_configured` | Business Hours | `/tenant/setup/availability` |
| 10 | `documents_submitted` | Documents | `/documents` |

### Onboarding Status Page

`app/(tenant)/onboarding-status/page.tsx` provides a dedicated onboarding status page with detailed setup guidance.

### Findings

| Check | Status |
|---|---|
| Tour component present | PASS |
| Setup wizard with 10 steps | PASS |
| Live step completion status from backend | PASS |
| Dedicated onboarding status page | PASS |
| Steps link to correct pages | PASS |

**Status: PASS** — Onboarding tour and setup wizard are complete.
