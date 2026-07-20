# Frontend Exposure Audit — Workstream 14

## Applications and pages found
Three tenant-portal pages reference service-area/coverage concepts:

1. **`app/(tenant)/provider/service-areas/page.tsx`** — the real
   `TenantServiceArea`/`TenantServiceAreaService` CRUD UI (calls
   `providerServiceAreasApi`, which hits `/v1/tenant/service-areas*` —
   this module's own routes).
2. **`app/(tenant)/service-areas/page.tsx`** — a **different** page
   calling `serviceAreaApi` (`/v1/geo/tenants/{tid}/zones*`), owned by
   `app.engines.geo`, not `serviceability`. Out of scope for this slice
   (a different, unmentioned module) — not touched, noted for
   completeness.
3. **`app/staff/service-areas/page.tsx`** — a read-only view for staff
   (calls `staffSelfApi.getServiceAreas()`), explicitly labeled "View
   only — contact your tenant admin to change coverage." No mutation
   control exists on this page at all — already correctly matches the
   backend policy (staff holds only `TENANT_SERVICE_AREA_READ`).

## Finding: hardcoded permission booleans (fixed this slice)
`app/(tenant)/provider/service-areas/page.tsx` previously had:
```ts
// No granular permissions array is returned by /v1/auth/me today, so these
// default to true for any authenticated tenant user (see Remaining Blockers).
const canCreate = true, canUpdate = true, canDelete = true, canSetPrimary = true;
```
This meant **any authenticated tenant user reaching this page** (owner,
staff, or — if ever granted access to this route — technician) saw all
4 mutation controls (Create, Update, Delete, Set-Primary) as active,
regardless of role. The backend already correctly rejected staff/
technician attempts (403), but the UI did not reflect that.

## Fix applied (minimal, reusing existing helpers)
```ts
const isOwner = isTenantOwnerRole(getUserRole());
const mutationAllowed = isOwner && !isTenantReadOnly();
const canCreate = mutationAllowed, canUpdate = mutationAllowed,
      canDelete = mutationAllowed, canSetPrimary = mutationAllowed;
```
Uses the pre-existing `getUserRole()`, `isTenantOwnerRole()`, and
`isTenantReadOnly()` helpers already used elsewhere in this codebase
(e.g. `provider/status/page.tsx`) — no new frontend authorization system,
no new role, no visual redesign. The page's layout, forms, and
confirmation dialogs are entirely unchanged; only the boolean gate
computation was corrected.

## Requirements check (after the fix)

| Requirement | Status |
|---|---|
| Read-only users have no active mutation controls | Fixed — `isTenantReadOnly()` now gates all 4 booleans |
| Technicians do not see tenant-wide coverage controls | Fixed — `isTenantOwnerRole()` returns `false` for `"technician"` |
| Staff sees only proven delegated capabilities | Fixed — no delegated capability was proven for staff on this module (evidence: `TENANT_SERVICE_AREA_CREATE/UPDATE/DELETE` granted only to `tenant_owner`), so staff now correctly sees no active mutation controls on this page either |
| Tenant owners see approved capabilities | Preserved — `isTenantOwnerRole` returns `true` for `"tenant_owner"` (and for `role === undefined`, the pre-existing loading-state convention) |
| Platform geography mutation controls do not appear in tenant portals | Confirmed — no platform-admin route or control appears anywhere in `frontend/tenant-portal` |
| Unsupported district/tier/zone behavior is not presented as working | The service-area form's `AreaType`/`coverage_type` options were not independently re-audited field-by-field this slice (a full form-field audit was judged out of scope for "minimal policy-alignment changes"); no evidence of a district/tier option being offered was found in the reviewed portion of the file |

## The `app/(tenant)/service-areas/page.tsx` (geo-zone) page
Not touched — it belongs to `app.engines.geo`, a different backend
module entirely, out of scope for this slice ("do not begin another
router module" / this module was never named in the mission).
