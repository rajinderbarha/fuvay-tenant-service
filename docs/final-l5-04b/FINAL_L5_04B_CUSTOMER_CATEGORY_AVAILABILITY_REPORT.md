# FINAL-L5-04B — Customer Category Availability Report

## Not implemented this sprint — honest scope statement
Customer-facing category discovery (`app/engines/*` customer-flow routers) was not wired to `tenant_category_entitlements`. No code change was made in this area.

## Real, current behavior (unchanged by this sprint)
Customer category discovery today combines global category status (`service_categories.is_active`, `is_customer_visible`) and coverage/geography signals from earlier sprints — none of which are aware of tenant-level entitlement. A category could remain visible to customers and route to a tenant whose entitlement for that category has since been disabled, because nothing in the customer discovery path queries `tenant_category_entitlements`.

## Required checks — status
| # | Check | Result |
|---|---|---|
| 1 | Category with no entitled provider follows visibility policy | Not implemented — no entitlement-aware provider count exists in customer discovery |
| 2 | Disabled tenant entitlement removes that tenant from matching | Depends on the Matching Entitlement gap (also not implemented, see that report) — customer discovery inherits the same gap |
| 3 | Global category disable removes category from discovery | Unaffected, pre-existing, unrelated to this sprint — global `is_active` already gates this |
| 4 | Existing `service_booking` history remains accessible | **True by default** — this sprint made no destructive change anywhere; historical bookings were never touched |
| 5 | Deep links to unavailable categories handled safely | Unaffected, pre-existing behavior, not re-tested this sprint |

## Why deferred
Same rationale as the Matching Entitlement gap: customer discovery is downstream of the matching engine (a category is only meaningfully "available" to a customer if a matching, entitled provider exists) — fixing this correctly requires the matching-engine entitlement work to land first. Attempting a customer-layer fix without the underlying matching fix would only mask, not close, the real gap.

## Result
Not implemented. Honestly documented as dependent on the (also not-yet-implemented) Matching Entitlement fix — see Remaining Blockers for the recommended sequencing.
