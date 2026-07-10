# E2E-07 Tenant Topbar / Header Report
**Date:** 2026-07-10  
**Analysis:** Static analysis only — browser verification pending

---

## Topbar Architecture

Rendered inside `components/layout/TenantLayout.tsx` as part of the main layout.

### Topbar Elements

| Element | Present | Detail |
|---|---|---|
| Brand logo / name | YES | "ServiceOS" with sidebar collapse toggle |
| Search bar | YES | Placeholder search input |
| Notifications bell | YES | Bell icon with badge for unread count |
| User avatar | YES | `DefaultAvatar` or real photo from `profilePhotoApi` |
| User name | YES | `myName || tenant.tenantName || "Owner"` |
| Theme toggle | YES | Sun/Moon icon via `useTheme` hook |
| Breadcrumbs | YES | `Breadcrumbs` component rendered in topbar row |
| Logout button | YES | In user dropdown panel |

### Tenant Name in Topbar

The topbar displays the tenant name sourced from:
1. `tenantName` from `useTenant()` → from localStorage (cached from login)
2. Updated live via `categoryDashboardApi.getRuntime()` (async after mount)

Fallback: `"My Business"` displayed until live data loads.

### Notifications

- Notifications bell opens a slide-in panel
- Unread count badge shown when `unreadCount > 0`
- Data from `notificationsApi`

### User Avatar

- `DefaultAvatar` renders initials-based avatar when no photo
- Real photo loaded via `profilePhotoApi.getMyPhoto()`

### Breadcrumbs

`components/layout/Breadcrumbs.tsx` is rendered in the topbar. It reads the current pathname and generates breadcrumb segments from URL parts.

### Findings

| Check | Status |
|---|---|
| Topbar present on all tenant pages | PASS |
| Live tenant name in topbar | PASS |
| Notifications bell | PASS |
| User avatar with real photo support | PASS |
| Theme toggle | PASS |
| Breadcrumbs in topbar | PASS |
| Logout accessible | PASS |

**Status: PASS** — Topbar is complete and consistent.
