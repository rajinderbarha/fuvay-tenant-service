# Customer Message Final-State Policy — Slice 2F-10A (Workstream 10)

## Established policy (unchanged, re-verified)
`add_customer_message` blocks on base `FINAL_STATUSES`
(`closed`/`cancelled`/`rejected`) via `if complaint.status in
FINAL_STATUSES: raise ValueError(ERR_COMPLAINT_ALREADY_CLOSED)` —
unmodified since before Slice 2F-9A, re-confirmed by source read and by
the full regression suite passing unchanged this slice.

## Resolved/settled: still MESSAGE_ALLOWED_BY_EXISTING_POLICY
`resolved` and `settled` are not in base `FINAL_STATUSES` (only in the
broader `FINAL_STATUSES_EXT`), so `add_customer_message` currently
allows messaging in both. No new repository evidence was found this
slice (beyond what Slice 2F-9A/2F-10 already documented) that would
justify reclassifying this. **Remains PRODUCT_DECISION_REQUIRED, not
changed** — per the mission's explicit instruction not to change this
without conclusive evidence.

## Every other status
`open`, `awaiting_provider_response`, `awaiting_customer_response`,
`under_admin_review`, `resolution_proposed`, `rework_approved`,
`refund_requested`, `refund_approved`, `refund_recorded`: all allowed
(not in `FINAL_STATUSES`) — unchanged.

## Repeated messages
Confirmed (unchanged from Slice 2F-9A's equivalent finding for the
provider side): an ordinary repeated customer message in any allowed
state is a legitimate conversation turn, not a duplicate mutation to
reject — `add_customer_message` has no idempotency guard and none was
added; this is correct, established behavior.

## Provider/internal author impersonation
Structurally impossible — `AddMessageIn` has no `sender_type` or
`visibility` field; `add_customer_message` hardcodes
`sender_type = ACTOR_CUSTOMER` and `visibility = VIS_PUBLIC` (unchanged,
re-confirmed by source read).

## Foreign complaint
Rejected via `get_customer_complaint`'s ownership check (unchanged,
Slice 2F-10-verified).
