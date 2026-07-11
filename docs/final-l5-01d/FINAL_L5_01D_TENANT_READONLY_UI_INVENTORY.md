# FINAL-L5-01D — Tenant Read Only UI Precision Inventory

Real Chromium session as `readonly@demo-ac-services.local`. Spec: `e2e/super-admin/final-l5-01d-readonly-precision.spec.ts`.

## Root cause found and fixed first
`isReadOnly()` (`components/shared/ReadOnlyBanner.tsx`) checked for role string `"tenant_read_only"` (with underscore), but the canonical backend role (confirmed in `app/core/permissions.py`) is `"tenant_readonly"` (no underscore) — **they never matched**. Additionally, the login handler (`app/login/page.tsx`) never persisted the user's role to `localStorage` at all, so no page could ever detect read-only status client-side regardless of the string-matching bug. Both fixed this sprint (see UX report).

## Per-page inventory (post-fix)

| Route | Mutation controls present | Expected behavior | Actual behavior (post-fix) | Result |
|---|---|---|---|---|
| `/jobs` (migrated this sprint) | None on list page (table is read-only by design) | Banner shown | **Banner shown** | PASS |
| `/jobs/[id]` (migrated this sprint) | Assign/Reassign/Schedule/Cancel buttons | Hidden for read-only | **Hidden** (`{!readOnly && (...)}` gate added) | PASS |
| `/services` | Save/Edit/Delete-class controls | Banner shown, controls disabled | **Banner shown**, 0 enabled mutation buttons detected | PASS |
| `/settings` | Save-class controls | Banner shown, controls disabled | **Banner shown**, 0 enabled mutation buttons detected | PASS |
| `/service-areas` | **"+ Add Zone" button** | Hidden or disabled | **Banner shown, but the Add Zone button remains visible AND enabled** | **FAIL — real, pre-existing gap, not fixed this sprint (out of Jobs/Bookings scope)** |
| Business Profile, Availability, Service Types, Brands, Provider Price Ranges, Coverage, Publish Readiness, Team, Technicians | Various | Not individually inventoried this sprint | Not tested | Not covered — time constraint |

## Assessment
The two pages this sprint's mission explicitly targets (Tenant Jobs list/detail) are now correctly gated, and the underlying infrastructure bug (role never persisted; role-string mismatch) that silently broke read-only UX **everywhere** in the app is fixed — which is why `/services` and `/settings` also improved from flaky/false-negative banner detection to a consistent, real pass. The **Service Areas "Add Zone" button** is a genuine, real remaining gap, found via the exact same real-browser method — documented honestly rather than hidden, and not fixed this sprint since Service Areas is outside the Jobs/Bookings scope this mission defines.
