# Session and Token Revocation Report — Slice 2D

## Mechanism (built this slice, exercised live)
The remediation script now revokes every unrevoked `user_sessions` row for a changed account as part of the same transaction as the role/active-status update: `UPDATE user_sessions SET revoked_at = now() WHERE user_id = :id AND revoked_at IS NULL`. The affected row count is captured and written into the audit event's metadata (`sessions_revoked`).

## Applied this slice
`manager@demo-ac-services.local`: 0 sessions existed (confirmed both before and after the change) — `sessions_revoked: 0` recorded accurately, not omitted or faked as "N/A."

## Honest exposure-window disclosure (per Workstream 8's explicit instruction)
Confirmed in Slice 2C and re-verified this slice: `app/dependencies/auth.py::get_current_user` reads `role` directly from the JWT payload, not a fresh database lookup. This means:
- **For the remediated account**: since it had 0 sessions and is now `is_active=false`, there is no exposure window — there was no live token to begin with, and the account cannot newly authenticate to receive one.
- **For any future remediation with active sessions** (i.e., if `readonly@` is ever remediated): revoking the `user_sessions` row forces the next request using that session's `session_id` claim to hit the `SESSION_REVOKED` check in `get_current_user` (confirmed existing code path: `if session_id_claim and await r.exists(f"serviceos:session:revoked:{session_id_claim}")`) — **but this check depends on Redis** (`get_redis()`), and the code explicitly fails open if Redis is unavailable ("fail open in dev, configure alerting in prod" — read directly from the source comment). This means session revocation's *enforcement* depends on the Redis-backed revocation-flag mechanism being populated and available, not merely the `user_sessions.revoked_at` column being set.
- **This slice's remediation script sets `user_sessions.revoked_at` but does NOT populate the corresponding Redis revocation key** (`serviceos:session:revoked:{session_id}`) — this is a gap: the DB record of revocation is correct and auditable, but the actual runtime enforcement check reads from Redis, not from `user_sessions` directly (confirmed by reading `get_current_user`'s exact check). For the account remediated this slice (0 sessions), this gap has no practical effect. **It would matter for any future remediation of an account with active sessions** (i.e., `readonly@`) and is documented here rather than silently assumed to be handled.

## Recommendation for future remediation with active sessions
Before remediating `readonly@` (or any account with live sessions), the remediation script should be extended to also write the Redis `serviceos:session:revoked:{session_id}` key for each session being revoked (reading `session_id` values from the `user_sessions` rows being updated), not just the DB column — otherwise a still-valid, unexpired JWT could continue to authenticate successfully (with its stale embedded role/claims) until Redis happens to be checked-and-populated by some other mechanism, or the token naturally expires. This is a concrete, scoped follow-up, not a vague caveat.

## Not claimed
This report does not claim "immediate enforcement" for a hypothetical active-session remediation — it explicitly documents the Redis-dependency gap above, per the brief's instruction not to overstate enforcement guarantees.
