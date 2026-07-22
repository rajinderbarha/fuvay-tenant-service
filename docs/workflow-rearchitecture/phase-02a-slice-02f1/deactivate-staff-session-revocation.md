# `deactivate_staff` Session Revocation Fix (Workstream 11)

## The gap
`AuthService.deactivate_staff` (`app/engines/auth/service.py`) previously
only set `user_sessions.revoked_at` in the database. `get_current_user`
(`app/dependencies/auth.py`) reconstructs `UserContext` purely from JWT claims
in the happy path and checks session revocation via a **Redis** key
(`serviceos:session:revoked:{session_id}`), not the DB column. This is the
identical gap Slice 2F found and fixed for `AuthService.update_permissions`
(permission reductions) — `deactivate_staff` had never received the same fix.

Practical impact before this fix: deactivating a staff member did not stop
their already-issued access token from continuing to authenticate until it
naturally expired (up to `ACCESS_TOKEN_EXPIRE_MINUTES`).

## The fix
Mirrors `update_permissions`'s proven pattern exactly:
1. Query active sessions (`revoked_at IS NULL`) for the user before revoking.
2. Update `user_sessions.revoked_at` (now also sets `revocation_reason=
   "staff_deactivated"` for auditability, matching the reason string style
   already used for `"permission_reduction"`).
3. For every active session found, `SETEX serviceos:session:revoked:{id}`
   with a TTL of `ACCESS_TOKEN_EXPIRE_MINUTES * 60` seconds — the exact flag
   `get_current_user` checks at request time.
4. Redis failures are caught and logged as a warning, not raised — fail-open,
   matching the existing convention in `update_permissions` and documented in
   Slice 2F's `known-limitations.md` (a Redis outage at the exact moment of
   deactivation leaves only DB-side revocation until natural token expiry).
5. `sessions_revoked` count added to both the return value and the
   `staff.deactivated` audit event's metadata.

## Cross-tenant / ownership
Unchanged — `deactivate_staff` still requires `user.tenant_id == tenant_id`
(raises `NotFoundException` otherwise), the same check as before this slice.

## Tests
`tests/test_phase2f1_tenant_engine_mutation_enforcement.py::TestDeactivateStaffSessionRevocation`:
- `test_deactivate_staff_sets_redis_revocation_flag_for_all_active_sessions` —
  2 active sessions, both DB-revoked and both get a Redis `setex` call with
  the exact key `get_current_user` checks.
- `test_deactivate_staff_no_active_sessions_no_redis_calls` — no active
  sessions means no unnecessary Redis calls (mirrors `update_permissions`'s
  "pure grant does not revoke" guard against unnecessary churn).

## Refresh-token path
Not separately re-verified this slice (same limitation Slice 2F documented
for `update_permissions`) — relies on the existing refresh-path's own
`session.revoked_at` check, reasoned sufficient but not independently
exercised against a live server.
