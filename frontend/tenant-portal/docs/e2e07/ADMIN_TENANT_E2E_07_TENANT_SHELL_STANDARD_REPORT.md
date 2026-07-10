# E2E-07 Tenant Shell Standard Report
**Date:** 2026-07-10  
**Analysis:** Static analysis only — browser verification pending

---

## Shell Architecture

The tenant portal uses a single shell layout in `app/(tenant)/layout.tsx` which renders `components/layout/TenantLayout.tsx`.

### TenantLayout.tsx Structure

| Component | Present | Notes |
|---|---|---|
| Sidebar with nav groups | YES | Collapsible, 22px wide collapsed / 260px expanded |
| Topbar | YES | Logo, search, notifications bell, user avatar |
| Breadcrumbs | YES | `components/layout/Breadcrumbs.tsx` rendered in topbar |
| Theme toggle | YES | Light/Dark via `useTheme` hook |
| Setup wizard panel | YES | Slide-in panel from `SETUP_STEPS` (10 steps) |
| Tour guide | YES | `TourGuide` component from `components/tour/TourGuide.tsx` |
| Toaster | YES | `Toaster` from `components/shared/ui` |
| Main content area | YES | `{children}` with scroll |

### Layout File

- `app/(tenant)/layout.tsx` — imports and renders `TenantLayout` as the wrapping shell

### Shell Standard Compliance

| Standard | Status |
|---|---|
| Auth guard (redirects to `/login` if no token) | PASS — `TenantLayout` reads token; missing → redirect |
| Consistent topbar across all pages | PASS — single shell, always rendered |
| Sidebar visible on all tenant pages | PASS — part of shell, cannot be bypassed |
| Breadcrumbs | PASS — `Breadcrumbs.tsx` rendered in topbar area |
| Page title / heading | PARTIAL — pages set their own titles; shell provides no global `<title>` override (Next.js metadata per-page) |
| Responsive sidebar collapse | PASS — chevron toggle collapses sidebar |

**Status: PASS** with one partial note on per-page title tags.
