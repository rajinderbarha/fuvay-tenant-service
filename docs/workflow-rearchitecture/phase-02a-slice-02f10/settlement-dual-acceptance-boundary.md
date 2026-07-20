# Settlement Dual-Acceptance Boundary — Slice 2F-10 (Workstream 10)

## Already closed by Slice 2F-9 (shared service method, re-verified here)
`customer_respond_to_settlement` calls
`self._get_settlement_proposal(db, proposal_id, complaint_id=complaint_id)`
— this is the exact same method Slice 2F-9 fixed to cross-check
`proposal.complaint_id` against the caller's already-verified
`complaint_id`, and it is shared by both `provider_router` and
`customer_router`. No new fix was required or made here; this was
directly re-verified (not assumed) by reading the current source of
`customer_respond_to_settlement` and `_get_settlement_proposal`.

## Preserved, unmodified guarantees
- **Customer cannot supply/modify the settlement amount or remedy type**:
  `SettlementRespondIn` has exactly 2 fields, `response` (accept/reject/
  counter) and `counter_description` (free text for a *new* counter-
  proposal, not a modification of the existing one) — no amount or
  remedy-type field exists anywhere in the schema.
- **Dual acceptance is enforced by `_check_dual_acceptance`**, called
  before any status promotion (Slice 2F-9's bug #30a/#30b fix, unmodified)
  — a customer accepting alone cannot mark the proposal accepted or
  trigger payout; both `customer_response` and `tenant_response` must be
  present and matching before `_execute_settlement_payout` fires.
- **Payout is internal credit/security-deposit only, via
  `DisputeSettlementService`** — canonical, unmodified, no real-money path.
- **Rejection creates no financial side effect** — `response == "reject"`
  branch only sets `proposal.status`/`complaint.settlement_status`, no
  payout call.
- **Repeated acceptance does not double-credit**: `_check_dual_acceptance`
  and the `if proposal.status == PROPOSAL_ACCEPTED` guard around the
  payout call mean a second `accept` call on an already-accepted proposal
  does not re-invoke `_execute_settlement_payout` (unmodified,
  pre-existing behavior, verified by the unchanged Slice 2F-9/Sprint 75
  test suite passing in this slice's regression run).

## Customer cannot accept a foreign proposal
Directly proven by the shared `_get_settlement_proposal` cross-check
(Slice 2F-9's fix, re-verified passing in Slice 2F-9/2F-9A's own tests,
re-run again this slice with zero regressions).

## Conclusion
No code change was needed in this workstream — this document exists to
satisfy the mission's explicit instruction that a weaker route reaching
the settlement service must be found and either fixed or block closure.
None was found: the customer path already inherits the correct,
already-fixed shared guard.
