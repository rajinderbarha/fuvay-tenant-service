# Final Status Rationale — Slice 2F-39A3

## Selected token: `AUTHORIZATION_REMEDIATION_BLOCKED`

**Preferred wording (per Slice 2F-39A3 review):** The mounted-route
census is complete: 261/261 previously unresolved route records now have
final classifications. Authorization certification remains blocked
because 21 routes require explicit product/caller-policy decisions and
service-layer verification. Always state this as "261/261 classified;
0 unclassified" — never as "0/261 unclassified" standing alone, which
reads ambiguously.

## The classification-volume blocker is closed; a different kind of blocker replaces it

The original 261-route census is now **100% classified** (0 unresolved
route-method records, down from 149 at this slice's start). This is real
progress — the mission's own success criterion for
`MOUNTED_ROUTE_CENSUS_COMPLETE` includes "UNKNOWN is zero, UNCLASSIFIED
is zero, PENDING is zero," which is now true.

However, `MOUNTED_ROUTE_CENSUS_COMPLETE` also requires "every confirmed
mutation has an evidence-backed authority boundary." **21 routes do not
meet this bar** — they are classified (each has exactly one final
category, satisfying the classification requirement) but explicitly
flagged `PRODUCT_DECISION_REQUIRED` because their authority boundary has
not been verified with the same rigor applied to the confirmed-safe and
confirmed-defective routes. This is not the same blocker as before
(classification volume); it is a **verification-depth** blocker.

## Why these 21 were not force-verified or force-fixed

Two confirmed real defects this program has now found
(`security.router::create_api_key`, `pricing.router::activate_rule`/
`deactivate_rule`) shared an outwardly identical guard signature
(`require_permission` where a sibling correctly used
`require_tenant_mutation_permission`) with two confirmed **safe** routes
(`security.router::rotate_api_key`/`revoke_api_key`, which turned out to
already enforce tenant ownership via `_require_trusted_tenant` inside the
service despite an unrelated-looking router signature). This proves the
guard pattern alone is not sufficient evidence either way — each of the
~8 remaining bare-`require_permission` candidates requires the same
individual service-layer trace that resolved the earlier four. That trace
was not completed for all 21 this slice, given time constraints, and
guessing would risk exactly the false-safety-claim problem this program
has repeatedly guarded against.

## What this slice achieved

- **149/149 remaining routes classified** — the original 261-route
  census is complete.
- **2 more real, confirmed defects found and fixed**
  (`chat.router::delete_message`, `compliance.router::record_consent`/
  `withdraw_consent`), both matching established, already-proven-correct
  sibling patterns in the same files.
- **21 routes honestly flagged as unverified**, not silently passed.
- Read-path privacy items kept in their own separate ledger throughout,
  per instruction — never folded into the mutation arithmetic.
- Phase-2F regression: 2500/2500 passed, twice, identical.

## Path forward

A future slice (2F-39A4 or equivalent) should resolve the 21 flagged
routes with the same rigor as the confirmed defects — prioritizing the
~8 bare-`require_permission` instances first. Only after that should any
`MOUNTED_ROUTE_CENSUS_COMPLETE` claim be made.

This slice stops at its own approval gate. Demo-role migration, Migration
144 execution, and Slice 2F-40 are not started.

## Reviewer-clarified bar for closing a `PRODUCT_DECISION_REQUIRED` row

Per the Slice 2F-39A3 review, `PRODUCT_DECISION_REQUIRED` is a valid
final census classification only when the row already records: fully
qualified route identity, persistent mutation behavior, current
authentication, current permission/scope, tenant/principal derivation,
client-controlled identifiers, service-layer method, known callers, the
exact missing product/caller-model decision, risk if left unchanged, and
safe candidate dispositions. These 21 rows must stay outside any
protected numerator until each is individually resolved to one of:
canonical tenant/provider mutation, customer self-service mutation,
platform-admin mutation, trusted internal operation, signed
callback/webhook, safely deprecated/unmounted route, or proven
non-business/read-only route. They must not be bulk-resolved by path
name or HTTP verb pattern-matching.
