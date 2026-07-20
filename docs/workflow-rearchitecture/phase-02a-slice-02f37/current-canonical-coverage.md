# Current Canonical Coverage (post Slice 2F-37)

- Canonical denominator: **313**
- Protected: **313**
- Unprotected: **0**
- Pending held candidates: **0**
- Canonical CSV hash: `2d6ebeee18c152c0`
- Mutation-enforcement matrix hash: `4389e57d9db6de83`

This matches exactly the mission's stated expected position for full
Set A/B closure: "Canonical unprotected: 0, Pending held: 0."

This coverage figure applies to the tenant-mutation canonical CSV only
(Design A: tenant-provider-persona mutations). It does NOT represent
application-wide authorization certification — that determination
belongs only to Slice 2F-38. Platform-admin, customer-self-service, and
platform-internal mutations remain tracked separately by design.

One canonically-included route (`POST /v1/payments/tenants/{tenant_id}/payout`)
is protected on its authorization/tenant-trust dimension but carries an
open, honestly-documented financial-integrity gap (client-supplied
`amount` with no authoritative balance validation) — see
`known-limitations.md`.

N01's domain-integrity backlog (4 items) remains open and unremediated
this slice per the frozen 2F-34 contract — see `n01-final-status.md`.
This backlog is explicitly orthogonal to canonical-coverage arithmetic
and does not affect the 313/313/0 figures above.
