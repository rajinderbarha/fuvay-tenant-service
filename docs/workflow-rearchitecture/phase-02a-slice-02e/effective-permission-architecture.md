# Effective-Permission Architecture

## The complete, now-verified pipeline

1. **Login** (`AuthService._build_token_pair`, `app/engines/auth/service.py:172-206`): if `user.role == "staff"`, queries `StaffPermission WHERE user_id = :user_id` and builds `{permission_key: is_granted}`. Embeds this dict as `extra_claims["permission_overrides"]`, along with `access_scope`, into the access token via `create_access_token`.
2. **Token refresh** (same file, ~line 765): identical fresh reload of `StaffPermission` rows, so a permission change takes effect the next time the user's token refreshes — not just at next login.
3. **JWT** (`app/engines/auth/utils.py::create_access_token`): merges `extra_claims` into the signed payload. `permission_overrides` and `access_scope` are now real claims in every issued token for a `staff`-role user.
4. **Request-time reconstruction** (`app/dependencies/auth.py::get_current_user`): decodes the token, checks the Redis blacklist/revocation flags, then builds `UserContext` — **this is the step that was broken.** It read `access_scope`, `role`, `tenant_id`, and 10+ other claims from `payload`, but never `permission_overrides`. **Fixed this slice** — one line added: `permission_overrides=payload.get("permission_overrides")`.
5. **Authorization check** (`app/core/permissions.py::PermissionChecker.has()`): given `role`, `permission`, and `overrides`, resolves in this order: `super_admin` → always true; `P.ALL` in role bundle → true; exact override match → returns override value (grant OR deny, whichever is set); engine-wildcard override match → same; role bundle membership → true; else false.

## Canonical effective-permission algorithm (now fully reachable)

```
def effective_permission(role, permission, overrides, tenant_id, requesting_tenant_id):
    if role == "super_admin":
        return True
    if permission in ROLE_PERMISSIONS.get(role, []) and P.ALL is present:
        return True
    if overrides and permission in overrides:
        return overrides[permission]          # exact override: grant or deny, always wins
    if overrides:
        engine_wildcard = permission.split(":")[0] + ":*"
        if engine_wildcard in overrides:
            return overrides[engine_wildcard]  # engine-level override
    return permission in ROLE_PERMISSIONS.get(role, [])
```

(Tenant-boundary check is a separate, prior concern — `overrides` are only ever loaded `WHERE user_id = :user_id`, and a user's `tenant_id` is fixed at the `User` row level, so an override dict can never contain another tenant's grants by construction, not by a check inside this function. See `staffpermission-integration.md`.)

## Answers to Workstream 1's specific questions

| Question | Answer | Verification |
|---|---|---|
| Base permissions derived from canonical role? | Yes — `ROLE_PERMISSIONS[role]` | RUNTIME_VERIFIED |
| Tenant-specific grants? | Yes — `StaffPermission.is_granted=True` rows, now reachable | RUNTIME_VERIFIED (fixed this slice) |
| Tenant-specific denies? | Yes — `is_granted=False` rows, now reachable, confirmed to override role grants | RUNTIME_VERIFIED (new test) |
| Does explicit deny override base role grant? | **Yes** — confirmed by `test_explicit_deny_overrides_a_base_bundle_grant` | RUNTIME_VERIFIED |
| May grants expand `staff` permissions? | **Yes** — confirmed by `test_grant_beyond_base_staff_bundle_takes_effect` | RUNTIME_VERIFIED |
| May technician permissions be overridden? | Same mechanism applies (overrides are role-agnostic in `PermissionChecker.has()`), but `_build_token_pair` only loads `StaffPermission` rows `if user.role == "staff"` — a `technician`-role user's overrides are never loaded into their JWT, even if rows existed. **Not fixed this slice** — see `known-limitations.md`. | SOURCE_VERIFIED (gap found this slice) |
| Can `tenant_owner` be restricted? | No — same `if user.role == "staff"` gate excludes `tenant_owner` from override loading entirely | SOURCE_VERIFIED |
| May platform roles receive tenant `StaffPermission` records? | Structurally yes (nothing prevents inserting one), but they'd never be loaded into a platform role's JWT (same `staff`-only gate) and platform roles bypass permission checks anyway via `role == "super_admin"` or their own `ROLE_PERMISSIONS` bundles | SOURCE_VERIFIED |
| Behavior for missing/malformed records? | `_get_staff_permissions` returns `{}` if no rows exist — safe default, no permissions granted beyond role bundle | RUNTIME_VERIFIED |
| Behavior when permission source unavailable? | If the `StaffPermission` query fails at login, the exception would propagate and fail the login itself (not silently grant/deny) — not independently re-tested this slice, but no fail-open code path was found | SOURCE_INFERRED |
| Tenant-boundary validation? | By construction (`user_id` uniquely maps to one tenant) — confirmed no cross-tenant leak possible via the query shape, plus a dedicated integrity check now exists (`check_role_integrity.py`) | RUNTIME_VERIFIED |
| Cache behavior? | No permission cache exists anywhere (confirmed Slice 2C, re-confirmed this slice); overrides live only in the JWT, refreshed at login/token-refresh | RUNTIME_VERIFIED |

## What this fix does NOT do
It does not extend override-loading to `technician` or `tenant_owner` roles (found as a new, narrower gap this slice — see `known-limitations.md`). It does not touch mutation-route guard coverage (a separate, larger gap — see `tenant-mutation-route-inventory.csv`).
