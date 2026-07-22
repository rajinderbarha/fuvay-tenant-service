# StaffPermission Integration

## Integration point chosen: the smallest shared one

Per the brief's instruction ("use the smallest shared integration point that prevents duplicated permission logic"), the fix touches exactly one function: `app/dependencies/auth.py::get_current_user`. Every `require_permission`/`require_any_permission`/`require_tenant_mutation_permission` dependency already calls `get_current_user` first and reads `user.permission_overrides` — so fixing the one shared reconstruction point automatically fixes every consumer, with zero duplicated logic anywhere else.

## Requirements checklist

| Requirement | Status |
|---|---|
| Load only permissions belonging to the authenticated user and active tenant | Yes — `StaffPermission WHERE user_id = :user_id`, and `user_id` is fixed to one tenant by the `User` row itself |
| Validate permission names against the canonical registry | Not validated at load time (any string in `permission_key` loads as-is) — but structurally inert if invalid, since `.has()` only ever compares against a real `P.*` constant. `check_role_integrity.py` now separately flags unknown keys for operator visibility, without blocking anything |
| Apply grant and deny deterministically | Yes — proven by `test_explicit_deny_overrides_a_base_bundle_grant` |
| Expose effective permissions to existing dependencies | Yes — via `UserContext.permission_overrides`, consumed transparently by all existing `require_*` dependencies |
| Preserve existing role checks where genuinely required | Yes — role-only guards (`require_super_admin`, `require_tenant_owner`, etc.) were not touched |
| Preserve `tenant_owner` behavior | Yes — `_build_token_pair`'s `if user.role == "staff"` gate means `tenant_owner` accounts are entirely unaffected by this fix (their overrides, if any existed, still aren't loaded — see `known-limitations.md`) |
| Preserve technician restrictions | Yes, same reasoning — technician overrides aren't loaded either (existing gap, not newly introduced) |
| Preserve platform-admin scoping | Yes — untouched |
| Avoid one query per permission | Yes — one query per login/refresh loads ALL of a user's overrides at once into a dict, not queried per-permission-check |
| Avoid N+1 loading | Yes, same reasoning |
| Cache invalidation behavior | None needed — no cache exists; the JWT itself is the "cache," refreshed at login/token-refresh (see `session-and-token-revocation.md` for the associated exposure-window discussion) |
| Handle missing `StaffPermission` rows safely | Yes — empty dict, no elevated or reduced access beyond the role bundle |
| Handle malformed legacy permission rows safely | Yes — inert by construction, plus now surfaced by the integrity check |
| Audit visibility for permission changes | Yes, pre-existing — `update_permissions`'s service method already calls `self._audit("staff.permissions_updated", ...)` (confirmed by reading its source, not modified this slice) |

## Not a second authorization system
This integration reuses the existing `PermissionChecker`, existing `StaffPermission` model, existing `UserContext` dataclass, and existing `require_*` dependency functions verbatim. No new authorization primitive, table, or dependency type was introduced.

## Known gap (not fixed this slice, documented honestly)
`_build_token_pair`'s `if user.role == "staff":` gate means only `staff`-role accounts ever get their `StaffPermission` overrides loaded into a JWT — `technician` and `tenant_owner` accounts with override rows (if any existed) would not have them take effect. This wasn't part of this slice's scope (the manager/read-only personas both target `staff`-role accounts specifically), but is worth knowing if a future need arises to restrict a `technician` or `tenant_owner` account via overrides. See `known-limitations.md`.
