# provider-response-state-behavior.md — respond_to_complaint

## Route reconciliation
- **Runtime method/path**: `POST /v1/provider/complaints/{complaint_id}/respond`
  (`provider_router.py`, function `respond_to_complaint`).
- **Auth dependency**: `require_tenant_owner_mutation` (Slice 2F-9, unchanged).
- **Service method**: `ComplaintService.provider_add_response(db, tenant_id, complaint_id, actor_user_id, message_text, request_id)`.
- **Request schema**: `AddResponseIn { message_text: str }`.
- **Record mutation**: creates one `ComplaintMessage` row
  (`sender_type=provider`, `visibility=public`), sets
  `complaint.provider_responded_at = now()`.
- **Complaint status before/after**: unchanged by this operation in all
  cases — `respond_to_complaint` never transitions complaint status; it
  only records a message and a first-response timestamp.
- **Required actor**: tenant_owner (or super_admin) of the owning tenant,
  via router-level `require_tenant_owner_mutation` + service-level
  `provider_get_complaint`'s tenant-ownership check.
- **Existing state validation (as of this slice)**: `if complaint.status
  in FINAL_STATUSES: raise ValueError(ERR_COMPLAINT_ALREADY_CLOSED)` —
  newly added; mirrors `add_customer_message`'s identical, pre-existing
  guard.
- **Audit event**: `EVT_PROVIDER_RESPONDED` via `_log_event` — pre-existing,
  confirmed present before this slice (Slice 2F-9's claim that no audit
  event exists was incorrect).
- **Notification event**: none raised by this method directly.
- **Frontend caller**: `complaints/[complaint_id]/page.tsx`, "Send reply"
  button — now hidden when `status` is `closed`/`cancelled`/`rejected`.
- **Alternate route**: none. Only `provider_router.py`'s
  `respond_to_complaint` calls `provider_add_response` (confirmed via
  `alternate-caller-review.md`).
- **Transaction boundary**: single `await db.commit()` at the end of the
  method; on `ValueError` (final-state or empty-message), no `db.add`/
  `db.flush`/`db.commit` occurs — proven directly in
  `tests/test_phase2f9a_complaints_state_machine.py::TestSideEffectSafety::test_respond_final_state_no_settlement_or_credit_side_effect`.
- **Side effects**: none beyond the message row and audit event — no
  settlement, credit, rework, or refund side effect exists in this method
  at all, so none can be triggered regardless of state.

## Per-state behavior
See `final-state-policy-matrix.csv` and `direct-state-test-matrix.csv`.
Disposition: **FINAL_STATE_MUTATION_PROHIBITED** for `closed`/`cancelled`/
`rejected` (fixed this slice); **ACTIVE** for every other status,
including `resolved` and `settled` (see `product-decisions-required.md`
for the open question of whether `resolved`/`settled` should also block
new provider messages — not changed this slice, since `resolved`/`settled`
are not in the base `FINAL_STATUSES` set and `add_customer_message`'s own
sibling behavior treats them the same way).

## Repeated action
A second, third, etc. `respond_to_complaint` call in the same non-final
state is **ALLOWED_MESSAGE_APPEND** — each call creates a new
`ComplaintMessage` row and a new `EVT_PROVIDER_RESPONDED` audit event; this
is ordinary conversation, not a duplicate to reject. Proven in
`test_repeated_response_is_allowed_message_append`.
