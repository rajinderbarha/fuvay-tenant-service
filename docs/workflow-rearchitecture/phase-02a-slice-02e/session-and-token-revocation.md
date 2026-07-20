# Session and Token Revocation — Slice 2E

## No remediation was applied this slice, so no session revocation was executed

`readonly@demo-ac-services.local`'s 7 sessions remain exactly as they were (unrevoked) — since no role/permission change was applied to this account (see `readonly-account-remediation.md`), there is nothing to revoke sessions *for*.

## What this slice's core fix changes about token/session behavior generally
The effective-permission wiring fix means a `staff` user's JWT now actually carries live-consulted `permission_overrides`. This has one important, previously-undocumented implication confirmed this slice:

**A permission grant/deny made via `update_permissions` does NOT take effect for an already-issued, still-valid access token** — the override is baked into the JWT at issue time (login) and refresh time, not read fresh from the database on every request. This mirrors exactly the same "stale JWT" characteristic Slice 2C found for `role` itself (`get_current_user` reads from JWT claims, not a fresh DB lookup) — now confirmed to apply equally to `permission_overrides`.

**Concretely:** if an admin uses `update_permissions` to deny a staff member a permission they previously had, that staff member's *current* access token continues to grant the old (now-revoked) permission until either the token naturally expires (`ACCESS_TOKEN_EXPIRE_MINUTES`, not independently re-checked this slice) or their session is explicitly revoked (forcing a re-login) or their refresh-token flow runs (which reloads permissions fresh, per the code in `app/engines/auth/service.py`'s refresh path).

## Honest exposure-window disclosure
This is the same category of finding as Slice 2C/2D's role-change exposure window, now extended to cover permission changes specifically: **immediate revocation is NOT automatic for a permission change** — an administrator using `update_permissions` today gets no automatic session revocation, and must separately revoke the target user's sessions (using the same `user_sessions.revoked_at` mechanism the remediation script uses) if they want the change to take effect immediately rather than at next natural token refresh/expiry.

## Recommendation (not implemented this slice)
`update_permissions` (or its router endpoint) should be extended to also revoke the target user's active sessions when a *deny* change is made (grants are lower-risk to leave until natural refresh; denies reducing access are the security-sensitive direction per the brief's "prefer immediate revocation for security-sensitive role or permission reductions" instruction). This was not implemented this slice because it touches the `auth` engine's core service method for a capability (staff permission editing) that, while now functional, was not otherwise modified this slice beyond the read-back fix — scoping the session-revocation addition to `update_permissions` itself is a reasonable, bounded follow-up, not folded in here to keep this slice's diff centered on the one proven fix.
