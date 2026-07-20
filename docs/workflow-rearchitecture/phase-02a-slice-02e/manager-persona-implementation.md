# Manager Persona Implementation

## Status: mechanism proven working; no new account created or reactivated

## What was proven (not built new)
`AuthService.invite_staff` and `AuthService.update_permissions` (both pre-existing, predating this slice) already implement the complete pipeline:
1. `invite_staff(tenant_id, inviter_id, email, full_name, phone, permissions)` creates a `role="staff"` user and, for each `perm in permissions`, inserts a `StaffPermission(user_id=..., tenant_id=..., permission_key=perm, is_granted=True, granted_by=inviter_id)` row, plus an audit event (`staff.invited`).
2. `update_permissions(tenant_id, target_user_id, granting_user_id, permissions: dict[str, bool])` updates or inserts `StaffPermission` rows for an existing staff member, verifies `user.tenant_id == tenant_id` before allowing any change, and writes an audit event (`staff.permissions_updated`).
3. Both are reachable via real, existing API endpoints: `POST /v1/staff/invite` (permission-gated by `require_permission(P.AUTH_STAFF_INVITE)`) and `PATCH /v1/staff/{user_id}/permissions`.

**Before this slice's fix, granting permissions through either endpoint had zero effect** — the grant was persisted correctly but never reached `PermissionChecker.has()` at authorization time. **After this slice's fix, it works**, confirmed by `tests/test_phase2e_effective_permissions.py::TestFullRoundTripPermissionOverrides`.

## Manager permission configuration (candidate, not yet applied to a real account)
No canonical "manager template" object was introduced — per the rule against hidden role aliases, "manager" is simply a set of individual `P.*` grants applied via `update_permissions`. A candidate set, evaluated against the brief's responsibility list:

| Responsibility | Candidate permission | Included in candidate set? |
|---|---|---|
| View team jobs | (no existing `P.*` constant found for team-wide, as opposed to own-job, visibility) | **Not proven** — would need a new permission constant + service-layer filter change, out of scope |
| Assign technicians | (no existing constant found in this pass) | Not proven |
| Review inspections | Same as "view team jobs" — own-job scoped today | Not proven |
| Review quotes | `P.FIELD_OPS_QUOTES_MANAGE` (already in base `staff` bundle, own-job scoped) | Already available, not exclusive to "manager" |
| Manage availability | Not located this slice | Not proven |
| View customers | Not located beyond `P.CHAT_READ` (own-chat only) | Not proven |
| Respond to complaints | Not located this slice | Not proven |
| View business details | `P.SETTINGS_READ` (already in base bundle) | Already available |
| Manage staff, if delegated | `P.STAFF_MANAGE`, `P.AUTH_STAFF_MANAGE` (exist, confirmed real constants) | **Provable and grantable today** |
| View finance, if delegated | Not located this slice | Not proven |
| Modify finance, if delegated | Not located this slice | Not proven |
| Modify business settings, if delegated | Not located this slice | Not proven |

**Honest conclusion:** the *mechanism* for granting individual permissions is now fully functional, but a genuine "manager" persona needs several permission constants for team-wide (not own-job-scoped) job/quote/customer visibility that either don't exist yet or weren't located in this slice's search. `P.STAFF_MANAGE` is the one clearly real, grantable permission directly matching a brief-listed responsibility ("manage staff, if delegated").

## Why no demo account was created or reactivated
Building a full, correct manager persona requires the missing team-wide-visibility permissions above, which are out of this slice's scope to invent. Reactivating `manager@demo-ac-services.local` with only `P.STAFF_MANAGE` granted (the one responsibility provably available) would represent a small fraction of what "manager" implies, risking a misleading impression that the persona is complete. Proving the *mechanism* via tests, without prematurely declaring a specific account "done," was judged the more honest choice — consistent with `manager-demo-account-decision.md`.

## Frontend
Not touched this slice — `frontend-access-alignment.md` explains why no manager-specific navigation changes were made without a real account to reflect.
