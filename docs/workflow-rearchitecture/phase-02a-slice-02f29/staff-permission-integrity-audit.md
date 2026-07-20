# StaffPermission Integrity Audit - Slice 2F-29

## Defect found and fixed: unvalidated permission keys

`update_permissions` and `invite_staff` both wrote `StaffPermission` rows
straight from request input. `PermissionChecker.has` consults those rows as
per-user overrides, so an unknown or mistyped key became a live override row.

Both now validate every key against `_valid_permission_keys()` - built from the
existing `P` constants plus every permission granted by `ROLE_PERMISSIONS`
(406 keys). Unknown keys raise `VALIDATION_ERROR` and **nothing is persisted**.
No permission was created.

## Preserved semantics (re-asserted by test)

- Tenant scoping: target must belong to the acting tenant.
- Explicit deny precedence: `overrides={p: False}` beats a role grant.
- Cross-tenant isolation: a grant for another tenant does not apply.
- Unknown role fails closed.
- Permission reduction still revokes active sessions and sets the Redis
  revocation flag `get_current_user` actually checks (pre-existing 2F behaviour,
  unchanged).

## Note on the `*` wildcard

`*` (`P.ALL`) is a genuine registry entry, so it passes validation. It cannot
act as a global grant through an override: `PermissionChecker.has` matches an
override only by exact key or `engine:*`, never by a bare `*`. Asserted by
`test_wildcard_override_cannot_act_as_a_global_grant`.
