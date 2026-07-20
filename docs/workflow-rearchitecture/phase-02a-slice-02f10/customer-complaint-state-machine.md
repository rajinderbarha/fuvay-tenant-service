# Customer Complaint State Machine — Slice 2F-10 (Workstream 12)

Re-extracted directly from `app/engines/complaints/constants.py` (same
authoritative source as Slice 2F-9A) — the actual repository status set
does **not** match the mission's illustrative list verbatim (there is no
distinct "escalated" or "investigating" status; "awaiting provider
response"/"under admin review" are the closest real equivalents, and
"settlement proposed"/"settled" exist as an extended-status pair, not
separate from "resolved"). Reported as observed, not assumed.

## Customer mutations and their legal source/result states

| Customer mutation | Legal source states | Result state | Final-state behavior |
|---|---|---|---|
| `add_customer_message` | any status not in `FINAL_STATUSES` (`closed`/`cancelled`/`rejected`) | unchanged | blocked in `closed`/`cancelled`/`rejected` |
| `cancel_customer_complaint` | any status with `cancelled` in `ALLOWED_TRANSITIONS_EXT[status]` (`open`, `awaiting_provider_response`... — see 2F-9A's extraction) | `cancelled` | `_transition` raises on illegal source (existing, unmodified) |
| `customer_accept_resolution` (non-rework) | `awaiting_provider_response`, `under_admin_review` (only sources whose transition set includes `resolved`, plus resolution-specific pre-check added this slice) | `resolved` | pre-validated before mutation (fixed this slice) |
| `customer_accept_resolution` (rework) | same 2 sources, target `rework_approved` | `rework_approved` | pre-validated before mutation + rework creation (fixed this slice) |
| `customer_reject_resolution` | any status with `under_admin_review` in `ALLOWED_TRANSITIONS_EXT[status]` | `under_admin_review` | pre-validated before mutation (fixed this slice) |
| `customer_respond_to_settlement` (accept) | proposal must be `proposed`/`countered`; dual acceptance promotes complaint to `settled` | `settled` (only on dual acceptance) | `_check_dual_acceptance` unchanged |
| `customer_respond_to_settlement` (reject) | same | `settlement_status = rejected`, complaint status unchanged | no side effect beyond status field |
| `create_refund_request_from_complaint` | soft ALLOWED_TRANSITIONS check — silently no-ops (does not raise) if `refund_requested` isn't legal from current status | `refund_requested` (if legal) else unchanged | pre-existing silent-no-op behavior, not changed this slice (see `product-decisions-required.md`) |

## Verified directly (not assumed) via the new test suite
- `closed`/`cancelled`/`rejected` complaints cannot have a resolution
  accepted or rejected — proven via
  `test_accept_resolution_illegal_state_creates_no_mutation`/
  `test_reject_resolution_illegal_state_creates_no_mutation`.
- Customer cannot move a complaint into a provider-only state — no
  customer mutation targets `resolution_proposed`, `refund_approved`,
  `refund_recorded`, or any AI-settlement-internal status; every customer
  mutation's target status is one of `resolved`/`rework_approved`/
  `under_admin_review`/`cancelled`/`settled`/`refund_requested` only.
- No explicit "reopen" route exists — a customer cannot reopen a closed
  complaint through any route in this router (confirmed absent).
- Invalid-state requests cause no persistence side effect — proven via
  the ordering-defect fix tests (`db.flush`/`db.commit` never called,
  `ServiceReworkService` never instantiated).
