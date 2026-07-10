# Phase 7 — Staff/Technician App Bug Fix Report

## Bugs found and fixed

1. **CRITICAL tenant-isolation gap in the staff job-list endpoint.**
   `FieldOpsService.list_jobs` (`app/engines/field_ops/service.py`) only
   overrode the client-supplied `tenant_id` query parameter with the JWT's
   real tenant_id for `role == "tenant_owner"`. `staff`/`technician` roles
   had no equivalent override — a technician could pass an **arbitrary**
   `tenant_id` in the query string and have it used directly in the
   `WHERE Job.tenant_id == tenant_id` filter. (The `staff_id` filter was
   already correctly forced to the actor's own ID, which limited practical
   exposure, but this remained a real, confirmed gap against this exact
   ticket's named hard gate.) Fixed by extending the override condition to
   `("tenant_owner", "staff", "technician")`. Live-confirmed: a request
   with a garbage `tenant_id` now returns the identical (correct, own-tenant,
   empty) result as one with the real tenant_id — no behavioral difference,
   no leak.

2. **CRITICAL: the real, seeded technician account was invisible on the
   tenant owner's own Staff page**, and any attempt to view technician
   skills crashed with a `500`. Two compounding causes:
   - `AdminTenantService.list_staff` / `_load_tenant_staff` / the
     staff-count query (`app/engines/tenant_engine/admin_service.py`, 3
     occurrences) filtered `User.role == "staff"` — a literal string that
     excludes every real seeded account (the actual seeded role is
     `"technician"`, a discrepancy this codebase's own `ROLE_PERMISSIONS`
     dict already flags in a code comment). Fixed all 3 occurrences to
     `User.role.in_(("staff", "technician"))`. Live-confirmed: `GET /v1/
     tenant/staff` now correctly returns "Demo Staff."
   - The `provider_team_members` table (skills/coverage backing store)
     **did not exist in the live database at all** — its own model
     docstring claims it was "created by Sprint 11 migrations," but no such
     migration exists anywhere in this repo. `GET /v1/provider/team-members`
     returned a raw `500` (`relation "provider_team_members" does not
     exist`). Created migration `113` (idempotent-guarded, matching this
     session's established pattern) to create the table, then seeded a
     real row for the real technician via the actual, audited `POST /v1/
     provider/team-members` API (not raw SQL) with `skills: ["AC Repair"]`,
     and linked its `user_id` to the technician's real account (the create
     endpoint doesn't accept `user_id` in its payload, so this one linkage
     step used a direct, documented SQL `UPDATE`). Live-confirmed: the
     endpoint now returns `200` with the correct skill data.

## End-to-end proof (after fixes, real backend + real Postgres)

```
Login as staff@serviceos.in (role=technician, tenant=Demo AC Services)
→ GET /v1/staff/me/jobs?tenant_id=<real> → 200, empty (no jobs assigned yet)
→ GET /v1/staff/me/jobs?tenant_id=<garbage> → 200, IDENTICAL empty result (isolation fix confirmed)
→ GET /v1/provider/team-members → 200, real skill data (was 500 before the migration fix)
→ (as tenant owner) GET /v1/tenant/staff → 200, "Demo Staff" now visible (was empty before the role-filter fix)
```

## Bugs found, not fixed (documented as the primary remaining blocker)

- **No dedicated technician self-service frontend exists anywhere** — see
  `PHASE_7_STAFF_APP_FRONTEND_REPORT.md` for full detail. This is a
  feature-build gap, not a bug to patch, and is the primary reason this
  sprint's final recommendation is not an unqualified READY.
- **No self-service session/device-management endpoint** for staff (only
  tenant-owner-managed staff lock/unlock/revoke-sessions exists).
- Two unrelated files (`package_commerce/public_router.py`,
  `location_engine/router.py`) still have the `request_id`-placeholder
  pattern from earlier sprints — neither is staff-facing, so left as a
  carried-forward, out-of-scope note rather than fixed under this ticket.
