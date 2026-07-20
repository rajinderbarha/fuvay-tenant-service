# Frontend Exposure Audit — Slice 2F-3B

## Method
Reused Slice 2F-3A's frontend-caller findings (re-confirmed structurally
unchanged, since no frontend code was touched) and extended to cover all
27 reachable endpoints via the same `frontend/tenant-portal/lib/api.ts`
grep pattern.

## Findings
- accept/reject: called by `frontend/tenant-portal` at the shared path —
  now unambiguously served ONLY by `home_service_assignment.staff_router`
  (the shadowed execution-router copy no longer even has a route
  registered, so there is no possible confusion).
- assign/reassign/cancel-assignment/schedule: called by
  `frontend/tenant-portal` — `home_service_assignment.provider_router`,
  now `require_tenant_owner_mutation`-gated, matching the tenant-portal's
  tenant_owner-facing persona.
- Whole-job cancel, parts-approve/reject/install: called by
  `frontend/tenant-portal` — `execution.home_service_router`, now
  `require_staff_or_above_mutation`-gated.
- The 14 execution-progress endpoints (on-the-way, reached-site, etc.):
  not individually re-grepped this slice (Slice 2F-3A's audit already
  covered the general pattern; these are staff/technician-app-facing
  actions, out of this slice's narrow "did the guard swap break anything
  visible" concern since the guard is a strict superset of
  `get_current_user`).
- 3 admin endpoints: assumed super-admin-app-only, not independently
  re-verified this slice (see `platform-admin-execution-actions.md`).

## Requirements checked
- Read-only users must not see active mutation controls: not a frontend
  concern this slice touched (frontend was not modified); the backend now
  correctly denies mutation regardless of what the UI shows.
- Technician-only actions must not appear to tenant-owner-only users
  unless a verified override exists: `require_staff_or_above_mutation`
  intentionally allows `tenant_owner` as an override persona (consistent
  with the pre-existing `_staff_member_id` fallback-to-owner pattern seen
  in the router source) — this is a verified, existing override, not new.
- Provider-only Parts installation must not appear to technicians: the
  router-level guard change does not affect this (unchanged, downstream).
- Platform-admin-only actions must not appear in tenant portal: not
  independently re-verified this slice for these specific 3 endpoints
  (see above).
- Shadowed execution accept/reject functions must have no unique client:
  confirmed — no frontend code was found calling anything other than the
  shared path, and that path is now unambiguous.

## No frontend changes made
Current exposure was not found to be unsafe for anything this slice
touched — no frontend code was changed.
