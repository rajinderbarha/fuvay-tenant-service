# Service-Layer and In-Handler Audit — Slice 2F-4

## Services reached by this module's 10 mutations
`AdminTenantService` (profile/settings/users/staff) and `AuthService`
(lock/unlock/session-revoke).

## AdminTenantService
- `_load_tenant_user`/`_load_tenant_staff` both filter by
  `User.tenant_id == tenant_id` — confirmed via direct source reading and
  a regression test (`test_load_tenant_user_filters_by_tenant_id`,
  `test_load_tenant_staff_filters_by_tenant_id`). The `tenant_id` itself
  comes from `_tenant_id(user)` in the router (JWT-derived), never from a
  client-supplied parameter — a user-supplied tenant ID cannot override
  the principal's tenant.
- `create_user`/`create_staff` write `tenant_id=tenant_id` (the caller's
  own tenant) to the new row — no cross-tenant creation possible.
- Also called by `tenant_engine.admin_router` (confirmed
  `require_super_admin`-gated, a stronger caller, not a bypass — see
  `selected-module-alternate-routes.md`). No other caller was found.

## AuthService
- `_can_admin_manage_user` (shared helper for `lock_user`, `unlock_user`,
  `admin_revoke_all_sessions`, and several other admin-facing methods)
  enforces: `super_admin` may manage anyone; `tenant_owner` may only
  manage users within their own tenant (`target.tenant_id == admin.tenant_id`)
  and may NOT manage a `super_admin` target (privilege-escalation
  protection); any other role is rejected outright. Confirmed unchanged,
  not modified this slice.
- `_revoke_all_user_sessions`/`admin_revoke_all_sessions` both perform DB
  (`revoked_at`) AND Redis (`serviceos:session:revoked:{id}`) revocation —
  confirmed already correctly implemented, matching the pattern this
  workflow-rearchitecture effort has fixed elsewhere (Slice 2F/2F-1/2F-2/
  2F-3B's `deactivate_staff` fixes) — no gap found here.
- Called from `tenant_engine.portal_router` only for the tenant-scoped
  flow audited this slice; not independently re-verified for every other
  caller across the repository (out of scope — see
  `known-limitations.md`).

## Real bug found and closed
`AuthService(db=db, request_id=..., actor_id=uuid.UUID(user.user_id)...)`
was called with an `actor_id` keyword argument that
`AuthService.__init__(self, db, request_id="—", ip_address=None)` has
never accepted — a hard `TypeError` on every real call to `lock_staff`,
`unlock_staff`, `revoke_staff_sessions`, and the 2 read-only endpoints
`staff_login_history`/`staff_security_status` (5 call sites total, all in
this router). **Fixed**: removed the invalid `actor_id` kwarg from all 5
construction sites — `AuthService`'s `lock_user`/`unlock_user`/
`admin_revoke_all_sessions`/`get_audit_log`/`get_full_security_status`
methods all take `admin`/target IDs as explicit call arguments; none of
them ever read `self.actor_id`, so nothing else needed to change.

## Not claimed
This is not a repository-wide service-layer audit — scoped to the
services and handlers directly connected to this module's 10 mutations.
