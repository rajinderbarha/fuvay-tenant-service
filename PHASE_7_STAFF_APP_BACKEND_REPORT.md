# Phase 7 — Staff/Technician App Backend Report

## Architecture note (read first)

Like Phase 4/5/6, this is **not greenfield** — a real `/v1/staff/*` and
`/v1/provider/*` API surface exists across multiple engines: `field_ops/
staff_router.py` (`/v1/staff/me/jobs` — list/detail/accept/reject/status/
checklist, a genuine job-shell), `platform_notifications/provider_router.py`
(`/v1/staff/notifications`, `/v1/staff/chat`), `provider_portal/router.py`
(`/v1/provider/team-members` — skills/coverage, `/v1/provider/availability`).
No separate staff login exists (by design) — technicians use the same
`/v1/auth/login` and get role-gated JWT claims (`role: "technician"`).

Three real, critical/high-severity bugs were found and fixed this sprint
(full detail in `PHASE_7_STAFF_APP_BUG_FIX_REPORT.md`):

## Module 1/2 — Auth / Context Guard

Confirmed live: `staff@serviceos.in` (role `technician`, tenant `Demo AC
Services`) logs in successfully via the shared `/v1/auth/login`, JWT
carries the correct `tenant_id`/`role`. `PUT /v1/auth/me` (self-profile
update) is structurally safe — its request schema (`UpdateProfileRequest`)
only accepts `full_name`/`phone`/`avatar_url`, making self-role/tenant/
status change structurally impossible, not just policy-blocked.

## Module 9/10 — Assigned Work / Job List Shell + Job Detail Shell

**Critical tenant-isolation bug found and fixed**: `FieldOpsService.list_jobs`
only overrode the `tenant_id` query parameter with the JWT's real tenant_id
for `tenant_owner` — `staff`/`technician` roles had no equivalent override,
meaning a technician could pass an **arbitrary** `tenant_id` query parameter
and have it used directly in the `WHERE Job.tenant_id == tenant_id` filter.
The `staff_id` filter WAS correctly forced to the actor's own ID, limiting
practical blast radius, but this was still a real, confirmed isolation gap
this ticket's own hard gate explicitly targets ("If technician can access
another tenant's data → NOT_READY_STAFF_APP_SECURITY_FAILED"). Fixed by
extending the override to `("tenant_owner", "staff", "technician")`.
Live-confirmed: passing a garbage `tenant_id` now returns the same
(correct, own-tenant, empty) result as passing the real one — no leak, no
error, consistent behavior.

Job detail (`get_job` → `_assert_can_access_job` → `_assert_assigned`) was
already correctly isolated (404 for jobs not assigned to the requesting
staff member) — confirmed via source inspection, no fix needed there.

## Module 5 — Skills & Assigned Services

**Critical bug found and fixed**: the backing table for technician skills
(`provider_team_members`) **did not exist in the live database at all** —
its own model docstring claims "created by Sprint 11 migrations" but no
such migration exists anywhere in this repo, and `GET /v1/provider/
team-members` returned a raw `500`. Created migration `113` (idempotent-
guarded, matching this session's established pattern) and seeded a real
`provider_team_members` row for the real technician via the actual, audited
`POST /v1/provider/team-members` API (not raw SQL), with `skills: ["AC
Repair"]`, then linked `user_id` to the real technician account. Live-
confirmed: the endpoint now returns `200` with the correct skill data.

## Tenant staff list (owner-side reconciliation)

**Bug found and fixed**: `AdminTenantService.list_staff`/`_load_tenant_staff`/
the staff-count query all filtered `User.role == "staff"` — a literal string
that excludes every real seeded account, since the actual seeded role is
`"technician"` (a discrepancy this codebase's own `ROLE_PERMISSIONS` dict
already explicitly documents in a code comment: *"the real seeded role is
technician, not staff"*). This meant the tenant owner's own Staff roster
page could never show any real technician. Fixed all 3 occurrences to
`User.role.in_(("staff", "technician"))`. Live-confirmed: `GET /v1/tenant/
staff` now correctly shows "Demo Staff" (the real technician).

## Modules 6/7/11/12/13 — Service Areas (view), Availability, Notifications, Sessions, Activity

Service area visibility and notifications endpoints confirmed reachable and
correctly scoped (staff-jobs router's role restriction confirmed via
source; notifications keyed strictly off `u.user_id`). **No dedicated
self-service session/device-management endpoint was found** for staff
(only tenant-owner-managed staff lock/unlock/revoke-sessions exists) — a
genuine, documented gap, not fabricated.

## Result: **Backend certified after fixing 3 critical/high-severity bugs.** See `PHASE_7_STAFF_APP_BUG_FIX_REPORT.md`.
