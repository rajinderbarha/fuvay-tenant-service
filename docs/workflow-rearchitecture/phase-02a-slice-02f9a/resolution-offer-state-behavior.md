# resolution-offer-state-behavior.md — offer_resolution

## Route reconciliation
- **Runtime method/path**: `POST /v1/provider/complaints/{complaint_id}/resolutions`
  (`provider_router.py`, function `offer_resolution`).
- **Auth dependency**: `require_tenant_owner_mutation` (Slice 2F-9, unchanged).
- **Service method**: `ComplaintService.provider_offer_resolution(db, tenant_id, complaint_id, actor_user_id, resolution_type, description, customer_visible_notes, request_id)`.
- **Request schema**: `OfferResolutionIn { resolution_type: str, description: str, customer_visible_notes: str | None }`.
- **Record mutation**: creates one `ComplaintResolution` row
  (`status=proposed`, `proposed_by_type=provider`).
- **Complaint status before/after**: transitions complaint status to
  `resolution_proposed`, via `self._transition(...)`.
- **Required actor**: tenant_owner (or super_admin) of the owning tenant.
- **Existing state validation**: `self._transition(db, complaint,
  STATUS_RESOLUTION_PROPOSED, ...)` — checks
  `ALLOWED_TRANSITIONS_EXT.get(old_status, set())` and raises
  `COMPLAINT_INVALID_STATUS_TRANSITION` unless `old_status` is
  `awaiting_provider_response` or `under_admin_review` (the only two keys
  whose transition set contains `resolution_proposed`). **Pre-existing,
  unmodified — this slice only reordered when it runs relative to record
  creation (see Fix below), it did not change what it checks.**
- **Audit event**: `EVT_RESOLUTION_PROPOSED` via `_log_event` — pre-existing,
  fires only after a successful transition.
- **Notification event**: `complaint.resolution_offered` to the customer,
  via `notify_customer_complaint` (bug #42, Sprint-era fix, unmodified) —
  wrapped in `try/except Exception: pass`, so a notification failure
  cannot roll back or block the resolution offer itself.
- **Frontend caller**: `complaints/[complaint_id]/page.tsx`, "Offer
  resolution" button — now hidden when `status` is
  `closed`/`cancelled`/`rejected` (this slice).
- **Alternate route**: none. Only `provider_router.py`'s
  `offer_resolution` calls `provider_offer_resolution`.
- **Transaction boundary**: single `await db.commit()` at the end.

## Fix applied this slice (ordering defect)
Before this slice, the method order was: create `ComplaintResolution` →
`db.add` → `db.flush` → `self._transition(...)` (legality check) →
`_log_event` → notify → `commit`. This meant an illegal-state offer
**still wrote a `ComplaintResolution` row to the session** before the
`ValueError` fired. Whether that row ever reached the database depended
entirely on the caller's session/transaction rollback behavior on
exception (not verified as guaranteed within this router's own code).
Fixed by reordering: `self._transition(...)` now runs first; the
`ComplaintResolution` row is only constructed/added/flushed after the
transition succeeds. No new status, transition, or error code was
introduced — purely a reordering of already-existing operations.
Confirmed via `test_offer_resolution_final_state_no_mutation` and
`test_illegal_source_state_rejected_no_mutation` (`db.add.assert_not_called()`
for every illegal source state).

## Per-state behavior
See `final-state-policy-matrix.csv`. Disposition:
**FINAL_STATE_MUTATION_PROHIBITED** for every state except
`awaiting_provider_response` and `under_admin_review` — this is stricter
than a simple "not final" check; it is the full, correct
`ALLOWED_TRANSITIONS_EXT` legality check, already in place before this
slice and unmodified in its logic.

## Repeated action
A second `offer_resolution` call while the complaint is already
`resolution_proposed` (i.e., a resolution is already pending) is
**STATE_TRANSITION_REJECTED** — `resolution_proposed` is not itself a
legal source for another `resolution_proposed` transition, so the second
call raises `COMPLAINT_INVALID_STATUS_TRANSITION` and creates no second
resolution record. Proven in
`test_repeated_offer_while_already_resolution_proposed_rejected`.
