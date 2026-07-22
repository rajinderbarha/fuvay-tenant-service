# SLA, Priority, and Escalation Behavior — Workstream 12

## Finding: no SLA/priority/escalation mutation route exists in this router
`CustomerComplaint` has `sla_status` and (per the frontend's `priority`
field usage, confirmed in the detail page) a `priority` attribute, but
**no route in `provider_router.py` mutates either field.** Confirmed via
full read of the router file — all 9 mutations touch
`ComplaintMessage`/`ComplaintResolution`/`ServiceReworkRequest`/
`RefundRequest`/`AISettlementSession`/`SettlementProposal`; none writes
to `CustomerComplaint.sla_status` or `.priority` directly.

## Escalation
No escalation-trigger route (manual or automatic) was found in this
router. `STATUS_UNDER_ADMIN_REVIEW` exists in the state machine as a
reachable status (see `complaint-state-machine.md`), but no route in
`provider_router.py` transitions a complaint into or out of it.

## Requirements verification

| Requirement | Status |
|---|---|
| Provider cannot silently lower platform-controlled priority | Vacuously true — no route mutates priority at all |
| Provider cannot reset SLA by repeatedly changing status | Vacuously true — no route in this router changes `sla_status`, and the one indirect complaint-status mutation (`complete_rework`'s conditional resolve) is gated by `ALLOWED_TRANSITIONS`, not repeatable into a reset state |
| Escalation cannot target another tenant | N/A — no escalation route exists |
| Automatic worker routes are distinguished from user routes | N/A — no worker/scheduled-job route was found calling into this router's endpoints (all 9 are HTTP-only, `get_current_user`-based) |
| User access-scope guards are not applied to legitimate workers | N/A — no worker exists to misapply a guard to |

## Conclusion
SLA, priority, and escalation are read-only concerns from this router's
perspective — nothing here mutates them, so no automation was built and
none needed protecting. Per "do not build SLA automation if it does not
exist," nothing was added.
