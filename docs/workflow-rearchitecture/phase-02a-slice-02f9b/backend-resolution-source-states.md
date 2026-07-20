# Backend Resolution Source States — Slice 2F-9B (Workstream 1)

## Method
`ComplaintService.provider_offer_resolution` calls
`self._transition(db, complaint, STATUS_RESOLUTION_PROPOSED, ACTOR_PROVIDER, actor_user_id, ...)`.
`_transition` (complaint_service.py ~line 1124) does:
```python
old_status = complaint.status
allowed = ALLOWED_TRANSITIONS_EXT.get(old_status, set())
if new_status not in allowed:
    raise ValueError(f"{ERR_COMPLAINT_INVALID_TRANSITION}: {old_status} → {new_status}")
```
So the legal source states are exactly the keys `k` of
`ALLOWED_TRANSITIONS_EXT` such that `STATUS_RESOLUTION_PROPOSED in
ALLOWED_TRANSITIONS_EXT[k]`.

## Direct extraction from `app/engines/complaints/constants.py`
`ALLOWED_TRANSITIONS_EXT = {**ALLOWED_TRANSITIONS, <overrides>}`. Scanning
every key's target set for `"resolution_proposed"`:

| Backend status constant | Backend string value | Frontend serialized value | Contains resolution_proposed as target? |
|---|---|---|---|
| `STATUS_OPEN` | `open` | `open` | No (base: `{AWAITING_PROVIDER, UNDER_ADMIN_REVIEW, CANCELLED, REFUND_REQUESTED}`; ext override drops REFUND_REQUESTED, adds TENANT_REVIEW_PENDING — neither includes resolution_proposed) |
| `STATUS_AWAITING_PROVIDER` | `awaiting_provider_response` | `awaiting_provider_response` | **YES** — `{UNDER_ADMIN_REVIEW, RESOLUTION_PROPOSED, REFUND_REQUESTED}` |
| `STATUS_AWAITING_CUSTOMER` | `awaiting_customer_response` | `awaiting_customer_response` | No — `{RESOLVED, UNDER_ADMIN_REVIEW}` |
| `STATUS_UNDER_ADMIN_REVIEW` | `under_admin_review` | `under_admin_review` | **YES** — `{RESOLUTION_PROPOSED, REWORK_APPROVED, REFUND_REQUESTED, REJECTED, RESOLVED}` |
| `STATUS_RESOLUTION_PROPOSED` | `resolution_proposed` | `resolution_proposed` | No — `{AWAITING_CUSTOMER, RESOLVED, UNDER_ADMIN_REVIEW, REWORK_APPROVED}` (does not include itself) |
| `STATUS_REWORK_APPROVED` | `rework_approved` | `rework_approved` | No — `{RESOLVED}` |
| `STATUS_REFUND_REQUESTED` | `refund_requested` | `refund_requested` | No — `{REFUND_APPROVED}` |
| `STATUS_REFUND_APPROVED` | `refund_approved` | `refund_approved` | No — `{REFUND_RECORDED}` |
| `STATUS_REFUND_RECORDED` | `refund_recorded` | `refund_recorded` | No — `{RESOLVED}` |
| `STATUS_RESOLVED` | `resolved` | `resolved` | No — `{CLOSED}` |
| `STATUS_CLOSED` | `closed` | `closed` | No key — no outgoing transitions |
| `STATUS_CANCELLED` | `cancelled` | `cancelled` | No key — no outgoing transitions |
| `STATUS_REJECTED` | `rejected` | `rejected` | No key — no outgoing transitions |
| `STATUS_SETTLED` | `settled` | `settled` | No — ext-only key, `{CLOSED}` |

Plus the extended AI-settlement/tenant-review statuses
(`tenant_review_pending`, `tenant_no_response`, `ai_settlement_started`,
`ai_waiting_customer`, `ai_waiting_tenant`, `ai_proposal_sent`,
`ai_settlement_accepted`, `ai_settlement_failed`,
`admin_review_pending`, `settlement_proposed`, `admin_decision_made`) —
none of their transition sets include `resolution_proposed` either
(confirmed by direct read of `ALLOWED_TRANSITIONS_EXT`'s extended block,
lines 234-255).

## Result: exactly 2 legal source states
```
PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES = [
  "awaiting_provider_response",
  "under_admin_review",
]
```

## Status aliases / formatting differences
None found. The backend status strings stored on `CustomerComplaint.status`
are used verbatim (already snake_case) by the frontend — the page's own
`STATUS_COLOR` map and `status.replace(/_/g, " ")` display logic confirm
the frontend already consumes the exact backend string values with no
translation layer. No alias table, no case difference, no legacy status
name exists for either of the 2 legal states or any other status in this
router's domain.

## Existing direct tests (Slice 2F-9A, unmodified, re-run this slice)
- `test_legal_source_state_allowed[awaiting_provider_response]`
- `test_legal_source_state_allowed[under_admin_review]`
- `test_illegal_source_state_rejected_no_mutation[...]` (9 other statuses)
- `test_repeated_offer_while_already_resolution_proposed_rejected`

All still passing — see `backend-regression-report.md`.
