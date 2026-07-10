# Phase 7B — Remaining Blockers

None of these block the `READY_STAFF_TECHNICIAN_APP_FOUNDATION_FRONTEND_BACKEND_CERTIFIED`
recommendation for this phase's stated scope (a foundation frontend using already-certified
backend APIs) — they are explicitly out-of-scope gaps documented per this session's "document
honestly, don't fabricate" convention.

## 1. No staff document upload/verification endpoint

`/staff/documents` shows an honest "not yet available" state. No backend endpoint exists for a
technician to upload or view their own verification documents. Confirmed absent in both Phase 7
and Phase 7B research.

## 2. No staff self-service session/device management endpoint

`/staff/security/sessions` shows an honest "not yet available" state. No backend endpoint exists
for a technician to view or revoke their own active sessions. Confirmed absent in both Phase 7
and Phase 7B research. (Admin-side session management for tenant users exists per Phase 0E, but
nothing self-service for the logged-in user themselves.)

## 3. No staff-scoped activity/audit endpoint

`/staff/activity` shows an honest "not yet available" state. The only activity/audit endpoints
in the codebase (`security/router.py`'s `/activity` and `/audit-log`) are `require_super_admin`
gated. No tenant- or self-scoped equivalent exists for a technician to view their own action
history.

## 4. No dedicated "my skills" endpoint

`staffSelfApi.getMySkills()` reuses the general `GET /v1/provider/team-members` list and filters
client-side by matching `user_id`. This works correctly for the current single-technician
fixture but would need a dedicated `/v1/staff/me/skills` (or similar) endpoint, or server-side
filtering, to scale cleanly to tenants with many technicians without over-fetching.

## 5. Availability is read-only for technicians by design, not just by omission

Investigated during this sprint: the backend's `POST/PUT/DELETE /v1/provider/availability*`
endpoints are `require_tenant_owner`-gated. If a future phase wants technicians to manage their
own working hours, a new technician-scoped mutation path is a real backend change, not just a
frontend addition.

## 6. Pre-existing, unrelated build failure on `/service-jobs`

`npm run build` fails on the pre-existing `/(tenant)/service-jobs` page due to a
`useSearchParams()` Suspense-boundary issue inside `components/enterprise/EnterpriseDataGrid.tsx`
— confirmed unrelated to any file touched in Phase 7B (no `/staff/*` page imports
`EnterpriseDataGrid` or `useSearchParams`). Not fixed in this sprint as it is out of scope for
the technician app; flagged for a future sprint.

## 7. `tenantSetupApi.getActivity` (pre-existing, tenant-owner-facing) also points at the
   confirmed-404 `/v1/provider/activity` endpoint

Discovered as a side effect of Bug 4's investigation. This is a pre-existing tenant-owner
dashboard method, not one of this sprint's 13 staff pages, so left unchanged — flagged for
whichever future phase owns the tenant-owner dashboard's activity feed.

## 8. No ESLint config in `frontend/tenant-portal`

`npx eslint` fails immediately with "couldn't find an eslint.config.js" — no lint tooling is
configured for this project at all (pre-existing, not introduced this sprint). `npx tsc --noEmit`
was used as the primary static-correctness gate instead.
