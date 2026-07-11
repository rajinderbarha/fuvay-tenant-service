# FINAL-L5-01D — Tenant Read Only UX Fix Report

## Root cause (two compounding bugs)
1. **Role never persisted**: `app/login/page.tsx`'s login handler stored `user_id`, `tenant_id`, `full_name` in `localStorage` but never `role` — so no client-side code could ever determine if the logged-in user was read-only.
2. **Role-string mismatch**: `components/shared/ReadOnlyBanner.tsx::isReadOnly()` checked for `"tenant_read_only"` (with underscore) while the real backend/seed role is `"tenant_readonly"` (no underscore, confirmed against `app/core/permissions.py`) — even if role had been persisted, the check would never have matched.

## Fixes applied
1. `app/login/page.tsx`: added `localStorage.setItem("serviceos_user_role", u?.role ?? "")` after login.
2. `lib/api.ts`: added `getUserRole()` helper alongside the existing `getTenantId()`/`getUserId()` pattern.
3. `components/shared/ReadOnlyBanner.tsx`: `isReadOnly()` now matches both `"tenant_readonly"` (real) and `"tenant_read_only"` (defensive, in case other roles use the underscored form).
4. `app/(tenant)/jobs/page.tsx` and `app/(tenant)/jobs/[id]/page.tsx` (this sprint's migrated pages): wired `<ReadOnlyBanner role={getUserRole()}/>` at the top, and gated the detail page's Assign/Schedule/Cancel action buttons behind `!isReadOnly(getUserRole())`.

## Requirements checklist

| Requirement | Status |
|---|---|
| Read pages remain accessible | Yes — read-only users can still view Jobs list/detail fully |
| Mutation buttons hidden or disabled | Yes, on the two migrated Jobs pages (verified via real browser: 0 enabled mutation buttons) |
| Form fields read-only where appropriate | N/A for these two pages (no editable form fields present) |
| ReadOnlyBanner appears consistently | **Yes, verified live** — banner now correctly appears on `/jobs`, `/jobs/[id]`, `/services`, `/settings` (the infrastructure fix benefits all pages using this component, not just the two migrated ones) |
| Tooltips/messages explain view-only access | Yes — banner copy: "View-only mode. Your account has read-only access. Contact your administrator to request write permissions." |
| No edit modal can be opened | Confirmed for Jobs detail — Assign/Schedule/Cancel modals are unreachable since their trigger buttons are removed from the DOM (not just visually hidden) |
| Keyboard shortcuts cannot trigger mutation | Not applicable — no keyboard shortcuts exist on these pages |
| Direct API mutation remains blocked by backend | **Confirmed independently** — see backend precision report, 403 on all tested mutation endpoints regardless of frontend state |

## Known remaining gap (real, not hidden)
The **Service Areas "+ Add Zone" button** remains visible and enabled for Tenant Read Only — a pre-existing issue on a page outside this sprint's Jobs/Bookings migration scope. The banner now correctly appears there too (infrastructure fix), but the specific button was not individually gated. Flagged in remaining blockers.

## Result
**PASS for the in-scope pages (Tenant Jobs list/detail).** The underlying infrastructure fix (role persistence + role-string match) is a genuine, high-value bug fix that improves read-only UX correctness across the whole app, verified on 4 pages via real browser testing — not claimed as a full audit of every tenant page.
