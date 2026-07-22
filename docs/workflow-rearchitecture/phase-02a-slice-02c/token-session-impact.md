# Token and Session Impact

## Current state (investigated, not acted upon — no remediation was applied)

- `manager@demo-ac-services.local`: **0 sessions** — nothing to revoke.
- `readonly@demo-ac-services.local`: **7 sessions, all with `revoked_at IS NULL`** — currently live/unrevoked, per the `user_sessions` table.

## What the remediation script does today

Deliberately **nothing** to sessions/tokens — this slice's script only changes the `role` column and writes an audit row. This is intentional given no mapping was applied this slice (nothing to revoke sessions *for* yet), but it is also a documented gap for when remediation *does* happen (see below).

## Design for when remediation is eventually applied (documented here for the next slice, not built this slice)

Per the brief: "do not allow a stale token to retain an invalid or previous authorization state." For a `role` change, the relevant existing repository mechanisms are:

- **Sessions**: `user_sessions` table has a `revoked_at` column already (confirmed this slice) — revocation is `UPDATE user_sessions SET revoked_at = now() WHERE user_id = :id AND revoked_at IS NULL`. This uses an existing, already-present column; no new session-revocation mechanism needs to be invented.
- **Access tokens**: confirmed this slice — `app/dependencies/auth.py::get_current_user` reads `role = payload.get("role", "customer")` directly from the **JWT payload**, not a fresh per-request database lookup. This means a token already issued before a role change would keep carrying the *old* role string until it expires or is refreshed via `/v1/auth/token/refresh`. For these 2 specific accounts this is low-severity today (the old role already grants zero permissions, so a stale token is stuck at zero, not elevated), **but it is exactly the mechanism the brief warns about** ("do not allow a stale token to retain an invalid or previous authorization state") and matters a great deal for any *future* role change generally (e.g. if `readonly@` is ever mapped to `staff`, an unrevoked pre-existing session's token would still carry `tenant_readonly` until it expires naturally — the user would not actually receive their new `staff` permissions until they log in again or their token refreshes). **This confirms session revocation is not merely a nice-to-have for a future remediation — it is required** to make a role change take effect promptly, not just eventually.
- **Refresh tokens**: same `user_sessions` table appears to back these (not independently re-verified this slice).
- **Permission caches**: none found in this codebase — `usePermissions()` (frontend) always fetches fresh from `GET /v1/auth/me` (confirmed Slice 2), and no server-side permission cache was found in this or prior slices' investigations.
- **Navigation caches**: none found — frontend nav is computed live from the permission fetch, not cached.

## Recommendation for the future remediation execution
When a mapping is approved and applied:
1. Revoke all of the account's `user_sessions` rows (`revoked_at = now()`) as part of the same transaction as the role update.
2. Do not send an account notification automatically — these are demo accounts with unclear real ownership; a notification implies a real user should be told, which should be a deliberate choice by whoever approves the mapping, not an automatic side effect. If the account owner is known, a manual notification is more appropriate than an automated one for a 2-account, demo-tenant remediation.
3. **Revoking sessions is necessary but not sufficient on its own** — since `role` is embedded in the JWT at issue-time (confirmed above), the user must also either log out/in again or hit `/v1/auth/token/refresh` to receive a token carrying the new role. Revoking the session forces this (the old token's session no longer validates), so revocation is the correct and sufficient mechanism — it doesn't need a separate "force token invalidation" step, revoking the session accomplishes that.

## This slice's actual session/token action taken
**None.** No session was revoked, no token was invalidated, because no role was changed. This section documents the plan for when that does happen, per the brief's request to "define whether to..." even though execution didn't occur.
