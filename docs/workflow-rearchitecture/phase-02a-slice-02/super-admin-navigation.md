# Super-Admin Navigation Implementation

## Existing architecture (verified, not built this slice)
`frontend/super-admin/components/layout/AdminLayout.tsx` already implements a real, backend-driven permission system predating this slice (marked `FINAL-L5-05M`/`FINAL-L5-05N` in code comments):
- `usePermissions()` fetches real permissions from `GET /v1/auth/me` — never hardcoded, never computed client-side.
- `isNavItemPermitted()` fails closed (`perms === null` → hidden) while loading, checks `SUPER_ADMIN_ONLY` sentinel against `role === "super_admin"` for routes still gated by the coarse backend check, and checks real permission-string membership (`perms.includes(item.requiredPermission)`) otherwise.
- `isNavItemVisible()` additionally gates a handful of items by tenant module/vertical entitlement (`effective_menu`), independent of the permission gate.
- `FLAT_NAV_HREFS` + `resolveActiveNavId()` + `getRequiredPermissionForRoute()` give every reachable `/admin/*` route (including ones with no direct nav entry) an inherited permission requirement via longest-prefix matching — a single source of truth rather than a second hand-maintained route table (which is exactly what caused the original nav-config.ts drift this system was built to replace).

This means Workstream 2's core requirement — real permission-aware filtering for super_admin/admin_operations/admin_finance/admin_security/admin_readonly, with placeholder roles excluded and mutation actions hidden from admin_readonly — is **already implemented and backend-driven**, not something this slice needed to build. Verified by reading the full 789-line file rather than assumed.

## What this slice changed
Added 6 nav items (see `navigation-before-after.md`), each with a `requiredPermission` matching the pattern above:
- `bookability` → `SUPER_ADMIN_ONLY` (matches its sibling Home Services diagnostic items)
- 5 finance items → `finance:hub:read` (matches the existing `finance` item's own permission, and matches what the pages themselves check internally via `perm.has("finance:hub:export")` for their export actions)

No new permission strings were invented — both values reuse permission keys already defined and checked elsewhere in the same file/pages.

## Known architectural gap (not fixed this slice — out of scope)
Per Phase 1A's `backend-blockers.md` item 7: most backend `admin_router.py` files still gate on the strict `require_super_admin` check (not the newer `require_permission`), so a nav item visible to `admin_operations`/`admin_finance`/`admin_security`/`admin_readonly` under a real permission string may still hit a 403 from the backend if that specific route hasn't been migrated to `require_permission` yet. This is a backend authorization architecture gap spanning ~29 files — explicitly out of scope for a navigation-and-routing slice. The frontend's fail-closed, real-permission-driven nav is correct and consistent with what the backend *does* enforce today; closing the remaining backend gap is tracked as a separate future backend workstream.

## Verification performed
Read the full `AdminLayout.tsx` (789 lines) rather than relying on Phase 1's summary. Confirmed via direct source inspection which pages exist (`find` on `app/admin/*`) vs. which have `NAV_GROUPS` entries (line-by-line read), correcting Phase 1's stale claims about `analytics`/`reports`/`real-estate`/`coaching` already being handled correctly.
