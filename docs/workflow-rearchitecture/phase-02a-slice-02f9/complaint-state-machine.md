# Complaint State Machine — Workstream 8

## Actual statuses (re-verified via `constants.py`, not assumed)
`open`, `awaiting_provider_response`, `awaiting_customer_response`,
`under_admin_review`, `resolution_proposed`, `rework_approved`,
`refund_requested`, `refund_approved`, `refund_recorded`, `rejected`,
`resolved`, `closed`, `cancelled`. **Final statuses**:
`{closed, cancelled, rejected}` (`FINAL_STATUSES`, explicit constant).

Additional AI-settlement-specific sub-statuses exist
(`ai_settlement_started`, `ai_waiting_customer`, `ai_waiting_tenant`,
`ai_proposal_sent`, `ai_settlement_accepted`, `ai_settlement_failed`) —
tracked on `AISettlementSession`, not the parent complaint's own status
field in all cases (not exhaustively cross-referenced this slice).

## Transitions reachable from `provider_router.py`

| Route | Precondition | Result | Notes |
|---|---|---|---|
| `respond_to_complaint` | none found | no status change | Pure message append; does not itself transition complaint status |
| `offer_resolution` | none found | no status change on the complaint directly (creates a `ComplaintResolution` row) | Status likely transitions via a separate path not reached by this router |
| `complete_rework` | none on the rework itself | conditionally sets complaint `status = STATUS_RESOLVED` **only if** `STATUS_RESOLVED` is in `ALLOWED_TRANSITIONS[complaint.status]` | Pre-existing, unmodified — correctly guards against resolving from an illegal prior state |
| `respond_to_settlement` (accept, dual-accepted) | none on entry | sets `complaint.status = STATUS_SETTLED` (per a MODULE-L5-02 comment fixing a prior bug where this transition was missing) | Pre-existing, unmodified |

## Verified requirements

| Requirement | Status |
|---|---|
| Final complaints cannot be silently modified | **Not independently verified for `respond_to_complaint`/`offer_resolution`** — neither method checks `complaint.status` against `FINAL_STATUSES` before allowing a new message/resolution. This is a genuine, plausible gap, but not conclusively proven as exploitable within this slice's evidence (no test demonstrates a real-world consequence of replying to a closed complaint), and fixing it would require deciding the correct error code/response shape — logged in `known-limitations.md`, not fixed |
| Closed complaints cannot be resolved again | `complete_rework`'s `ALLOWED_TRANSITIONS` check does prevent this specific path (resolving via rework completion), since `STATUS_CLOSED`/`STATUS_CANCELLED`/`STATUS_REJECTED` have no outgoing transitions in `ALLOWED_TRANSITIONS` |
| Rejected resolutions cannot be marked accepted by the provider | N/A within this router — `ComplaintResolution`'s own accept/reject lifecycle was not found reachable from `provider_router.py` at all (only `offer_resolution`/creation and `list_resolutions`/read exist here) |
| Provider cannot accept a resolution on behalf of the customer | Confirmed — `respond_to_settlement` calls `tenant_respond_to_settlement`, entirely separate from `customer_respond_to_settlement` |
| Escalated complaints cannot be de-escalated without policy | N/A — no escalation/de-escalation route exists in this router |
| Reopening requires an explicit permitted route/persona | N/A — no reopen route exists in this router |
| Repeated transitions are rejected or intentionally idempotent | `complete_rework`'s complaint-resolve side-effect is naturally idempotent (repeating it when the complaint is already resolved simply finds `STATUS_RESOLVED` not in `ALLOWED_TRANSITIONS[STATUS_RESOLVED]` — a no-op, not an error) |
| Denied/invalid transitions perform no mutation | Confirmed via direct tests — a 403 (authorization) or `ValueError` (business/ownership) response occurs before any `db.commit()` |

## Conclusion
**[CORRECTED IN SLICE 2F-9A]** This section previously treated
`respond_to_complaint`/`offer_resolution` as a single, undifferentiated
gap. Direct re-reading of the source in Slice 2F-9A found that was
inaccurate for `offer_resolution`: `provider_offer_resolution` calls
`self._transition(...)`, which enforces `ALLOWED_TRANSITIONS_EXT` and
already rejects the operation from any state other than
`awaiting_provider_response`/`under_admin_review`, raising
`ERR_COMPLAINT_INVALID_TRANSITION`. This was proven directly (not
assumed) via a full state matrix in Slice 2F-9A. `respond_to_complaint`
(`provider_add_response`) genuinely had no final-state check and was
fixed there with a `FINAL_STATUSES` guard mirroring its own customer-side
sibling method. See `phase-02a-slice-02f9a/` for full detail.
