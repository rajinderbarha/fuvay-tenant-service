# Bargain Configuration Safety — UX-06 Round 5 (Workstream 3)

## Pre-creation checklist (per the spec's required conditions)

| Condition | Status |
|---|---|
| Environment is dev/test | Yes |
| Rule can be scoped to the isolated demo tenant | **NO — `BargainRule` has no `tenant_id` column at all** |
| Rule can be scoped to the exact service/category/offering | Partially (has `master_service_id`/`category_id`) but this scoping is platform-wide, affecting every tenant offering that service |
| Created through a canonical authorized API or safe seed mechanism | **NO — no create/write endpoint exists anywhere in the mounted routes** (only read/preview) |
| No migration required | Would require either a migration-adjacent script or raw SQL |
| No raw SQL required | Cannot be satisfied without one |
| No existing shared rule overwritten | Unknown/unverifiable without a query tool this round provided |
| Idempotent / reversible | Unverifiable without a real create path to test |
| Another tenant remains unaffected | **Cannot be true by construction — the model is global** |

**5 of 9 required conditions fail outright.** Per the spec: *"When ANY
condition cannot be proven, do NOT create the rule — use status
BARGAIN_CONFIGURATION_POLICY_BLOCKED instead."*

## Decision

**No `BargainRule` was created this round.** This specific workflow segment
(provider price-tier matching for `ac_repair`) is assessed as
`BARGAIN_CONFIGURATION_POLICY_BLOCKED` — a genuine backend/platform
configuration gap that cannot be safely closed from an isolated customer
test session, not a frontend defect and not something Round 5 should route
around with unsafe shared-data mutation.

This assessment applies specifically to the pricing-tier/bargain step of the
booking pipeline — it does not by itself determine the overall Round 5 status
token, which also depends on the screen-design and typecheck workstreams (see
final-status-rationale.md).
