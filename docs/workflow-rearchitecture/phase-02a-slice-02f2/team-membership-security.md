# Team and Membership Security — Workstream 6

## Scope
`create_team_member`, `update_team_member`, `delete_team_member`,
`activate_team_member`, `deactivate_team_member`, `create_member_login` —
all in `app.engines.provider_portal.router`, all backed by the
`provider_team_members` table.

## Findings

### 1. All 6 endpoints are role-gated to `tenant_owner`/`super_admin` only
No staff delegation exists today — `require_tenant_owner` (now wrapped by
`require_tenant_owner_mutation`) excludes `staff` and `technician` entirely.
Confirmed via direct HTTP test (`TestUnauthorizedRolesRejected`) and source
reading. This means Workstream 6's "staff cannot grant permissions they
lack authority to grant" / "staff cannot promote to tenant_owner" concerns
are moot for this specific table — no staff persona can call these
endpoints at all, so there is no delegation surface to police.

### 2. Real, confirmed cross-tenant data-leak bug — FOUND AND FIXED
`update_team_member`, `activate_team_member`, `deactivate_team_member` each
correctly scoped their `UPDATE` by `tenant_id=:tid`, but the read-back
`SELECT` immediately after used only `WHERE id=:id`, with **no tenant
filter**. A cross-tenant `member_id` would safely no-op the `UPDATE` (the
`WHERE tenant_id=:tid` clause ensures no row from another tenant is
touched), but the unfiltered `SELECT` would then return and leak that other
tenant's team-member row (name, phone, email, designation, skills) in the
response. **Fixed**: all 3 read-backs now filter by `tenant_id=:tid` and
return 404 if the row isn't found in the caller's own tenant.

### 3. Deactivation did not revoke sessions for a linked login — FOUND AND FIXED
`provider_team_members.user_id` is a nullable FK to `users` (confirmed via
`app/engines/home_service_assignment/staff_model.py`), meaning a team
member CAN have a real login account. `deactivate_team_member` flipped
`status='inactive'` but never touched that linked user's sessions — an
already-issued JWT for a deactivated team member kept authenticating,
identical to the gap Slice 2F/2F-1 found and fixed for
`AuthService.deactivate_staff`. **Fixed**: when `user_id` is present,
active `UserSession` rows are now revoked in both the database
(`revoked_at`) and Redis (`serviceos:session:revoked:{id}`), mirroring the
proven pattern exactly.

### 4. `create_member_login` is an unimplemented stub
Returns `{"member_id": ..., "credentials": None}` — no `users` row is
created, no password is generated, no `provider_team_members.user_id` is
set. This means the whole "create-login" flow does not actually work today.
Not fixed this slice (new engineering behavior is out of scope for a
mutation-enforcement slice) — flagged in `known-limitations.md`.

### 5. No permission/role-escalation surface exists
`update_team_member`'s allowed-fields set (`full_name, phone, email,
designation, member_type, can_receive_assignment, skills,
supported_offering_ids, supported_type_ids, supported_brand_ids,
service_area_ids`) contains no RBAC role or permission field — `designation`
is a free-text/display field on the team-member roster row, structurally
incapable of modifying `users.role` or any `StaffPermission` row (different
tables entirely). Confirmed: **designations cannot modify RBAC**, matching
the security model's explicit requirement.

### 6. Duplicate invitations / inactive-membership mutation
Not applicable — this table has no "invitation" concept (no pending/invited
status found in the allowed fields or the `status` values used:
`active`/`inactive`/soft-deleted via `deleted_at`). `create_team_member`
does not check for an existing row with the same email/phone before
inserting, so duplicate roster entries are possible — this is a business-
data-quality gap, not an authorization gap, and was not fixed this slice
(out of scope: no new product behavior).

## Session-revocation and canonical-role preservation
Confirmed unchanged and still enforced (per the brief's preservation list):
`AuthService.update_permissions`'s permission-reduction revocation,
`AuthService.deactivate_staff`'s DB+Redis revocation, and canonical-role
validation in the seed/remediation scripts — none of these were touched
this slice; the new `deactivate_team_member` fix is a parallel, independent
mechanism for a different table (`provider_team_members`/its linked
`user_id`), not a modification of the existing `AuthService` methods.
