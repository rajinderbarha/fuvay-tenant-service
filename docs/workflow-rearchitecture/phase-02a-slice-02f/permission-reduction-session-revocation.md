# Permission-Reduction Session Revocation

## Implemented and tested this slice

`app/engines/auth/service.py::update_permissions` now revokes sessions immediately whenever a permission reduction occurs (grant→deny transition, or a new explicit deny on a permission not previously recorded).

## Mechanism (both halves, closing the gap Slice 2D found)
1. **Database**: `UPDATE user_sessions SET revoked_at = now() WHERE user_id = :id AND revoked_at IS NULL` — same pattern already used by the pre-existing `deactivate_staff` method.
2. **Redis** (the part that was missing, and the part `get_current_user` actually checks at request time): `SETEX serviceos:session:revoked:{session_id} <access_token_ttl_seconds> 1` for every session being revoked. TTL matches `ACCESS_TOKEN_EXPIRE_MINUTES * 60` so the flag doesn't outlive any possible still-valid token referencing that session.

## Requirements checklist

| Requirement | Status |
|---|---|
| Use existing session-revocation mechanisms | Yes — reused `UserSession.revoked_at` (pattern from `deactivate_staff`) and the Redis key format from `get_current_user`'s existing check (not invented) |
| Revoke refresh-token capability | Not separately implemented — revoking the session should be sufficient, since refresh-token validation in this codebase checks `RefreshTokenFamily`/`UserSession` state (per Slice 2D's reading of the refresh path: `if not session or session.revoked_at: raise UNAUTHORIZED`) — a revoked session's refresh attempt already fails via the DB check; the Redis flag additionally blocks the still-valid access token itself before it would even reach a refresh attempt |
| Document access-token residual validity window | See below |
| Create an audit event | Yes — extended the existing `staff.permissions_updated` event's metadata with `reduced_permission_keys` and `sessions_revoked` |
| Avoid unnecessary revocation for harmless metadata changes | Yes — pure grants (no reduction) skip all revocation logic entirely, confirmed by `test_pure_grant_does_not_revoke_sessions` |
| Permission expansion behavior documented | Expansions (grants) take effect at next token refresh/login, same as before this slice — no change needed, since granting more access is not the security-sensitive direction |
| Navigation/permission caches refresh | No cache exists to refresh (confirmed Slice 2C/2E) — the JWT itself is regenerated at next login/refresh, and the session revocation forces that to happen sooner than "whenever it naturally would" |
| Failure to revoke surfaced, not silently ignored | Partial — the Redis `setex` call is wrapped in `try/except` that logs a warning (`auth.session_revocation_redis_failed`) rather than raising, so a Redis outage during a permission-reduction call would silently leave the DB-side revocation as the only protection (which is real but incomplete without the Redis flag) — this mirrors the existing codebase-wide pattern of "fail open on Redis unavailability, log a warning" (seen in `get_current_user`'s own blacklist check) rather than blocking the whole permission-update on a Redis hiccup. See `known-limitations.md` for the honest tradeoff this represents. |

## Honest exposure-window disclosure
If Redis is unavailable at the moment a permission reduction is applied, the `setex` call fails (logged, not raised), and the affected session's access token would remain valid **until it naturally expires** (`ACCESS_TOKEN_EXPIRE_MINUTES`) — the DB-side `revoked_at` alone does not stop `get_current_user` from authenticating an already-issued token, since that function checks Redis, not the `user_sessions` table, for revocation. This is the same category of honest disclosure Slice 2D made for role changes, now applying identically to permission changes.

## Not extended to `deactivate_staff`
That method has the identical gap (DB-only revocation, no Redis flag) but was not fixed this slice — Workstream 9's explicit list names permission/access-scope/role changes, and `deactivate_staff` (full account deactivation) is a related-but-distinct action not explicitly named. Flagged in `known-limitations.md` as a clear, cheap follow-up (the exact same 5-line pattern could be added there).
