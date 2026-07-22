# Final Status Rationale — Slice 2F-39A2

## Selected token: `AUTHORIZATION_REMEDIATION_BLOCKED`

## Why this is a more substantive blocked state than 2F-39A's

2F-39A's blocker was purely volumetric: real classification work, no
defects found, 229 routes still unclassified. This slice's blocker is
qualitatively different and more serious: **real, live authorization
defects were found** — one fixed (`create_api_key`'s cross-tenant IDOR +
read-only-scope bypass), six more precisely identified and left
deliberately unfixed pending a product/security decision. Per the
mission's own definition, "any confirmed mutation lacks a complete
authorization boundary" or "any newly discovered authorization issue
remains unresolved" independently triggers `AUTHORIZATION_REMEDIATION_BLOCKED`
— both conditions are true here, on top of the still-incomplete census
(149 routes remain unclassified).

## Why the 6 unfixed findings were not force-fixed

`record_activity`, `write_audit`, `create_session`, `revoke_session`
(security.router) all share bare `get_current_user` auth with fully
client-controlled tenant/entity/user identifiers, and grep confirmed zero
internal callers anywhere in this codebase. Two plausible, materially
different fixes exist depending on intended design:
- If internal-service-only: needs an internal-authority guard (not
  `require_super_admin`, which would be wrong for a service-to-service
  caller with no human session).
- If genuinely end-user-facing: needs tenant/actor ownership checks tied
  to the caller's own identity.

Guessing wrong risks either leaving a real gap (if I assume internal and
add the wrong guard) or breaking an undiscovered legitimate caller (if I
assume end-user and add an ownership check that a real internal caller
can't satisfy). The mission's own instruction — "identify the canonical
authority contract... apply the smallest correct fail-closed fix" —
presupposes the contract is identifiable; here it genuinely was not, with
the evidence available this slice. Recording this honestly (not
concealing it, not force-fixing it) is the responsible choice.

`activate_rule`/`deactivate_rule` in `pricing.router` were left unfixed
for a narrower reason: the fix pattern (swap to
`require_tenant_mutation_permission`) is well-established and low-risk,
but this slice ran out of time to confirm it isn't a deliberate exception
(unlike `create_api_key`, where the client-tenant-id-trust issue alone was
independently damning regardless of the guard question).

## What this slice actually achieved

- **80/80 routes in the 4 target modules classified** with real,
  source-level evidence (not heuristic guessing).
- **1 real, serious defect found and fixed**: cross-tenant IDOR + a
  read-only-access-scope bypass in `security.router::create_api_key`, with
  4 new tests proving the fix, plus a downstream classifier-corpus
  exemption correctly applied (and independently corroborated — the
  frozen 2F-26F historical corpus had already manually flagged this exact
  route `UNPROTECTED_CROSS_TENANT` / HIGH severity, years before this
  slice, confirming the finding wasn't a false positive).
- **6 more real defects found and precisely documented**, not hidden.
- **2 read-path privacy observations** recorded, consistent with this
  program's already-documented pricing-read-path limitation.
- Phase-2F regression: 2481/2481 passed twice, identical.
- Cumulative unresolved-route count: 261 → 229 (2F-39A) → **149** (this
  slice).

## Path forward

The next tranche should prioritize:
1. Resolving the 6 flagged findings (a product/security decision on
   caller intent for the 4 security.router endpoints, then confirmation
   + fix for the 2 pricing.router endpoints).
2. Continuing route classification into the remaining ~28 smaller
   modules.

This slice stops at its own approval gate. Slice 2F-39B/2F-40, demo-role
migration, and Migration 144 execution are not started.
