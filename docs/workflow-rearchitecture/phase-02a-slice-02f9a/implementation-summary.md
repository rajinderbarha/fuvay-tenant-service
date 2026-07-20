# Slice 2F-9A Implementation Summary

## Scope
Narrow follow-up to Slice 2F-9. Module: `app.engines.complaints.provider_router`.
Determine and verify final-state behavior for exactly 2 mutations —
`respond_to_complaint` (service: `provider_add_response`) and
`offer_resolution` (service: `provider_offer_resolution`) — via direct
source investigation and a full state-matrix test suite, not assumption.

## What was found
Slice 2F-9's own investigation contained two factual errors, both
discovered by re-reading the actual source in this slice:

1. **`offer_resolution` was reported as having "no state precondition at
   all."** False. `provider_offer_resolution` calls `self._transition(...)`,
   which checks `ALLOWED_TRANSITIONS_EXT` and raises
   `COMPLAINT_INVALID_STATUS_TRANSITION` unless the complaint is currently
   `awaiting_provider_response` or `under_admin_review` — the only two
   states whose transition set includes `resolution_proposed`. This
   already fully blocks offering a resolution from any open/resolved/
   closed/cancelled/rejected/settled/awaiting-customer state. No code fix
   was needed — this needed proof, not a fix.

2. **`provider_add_response` was reported as having no audit event.**
   False. It already calls `self._log_event(..., EVT_PROVIDER_RESPONDED, ...)`,
   writing a `ComplaintEvent` row identically to the other 8 mutation
   paths in this router. No audit gap ever existed.

3. **Genuine, confirmed gap**: `provider_add_response` had no final-state
   check at all — unlike its own customer-side sibling method
   (`add_customer_message`, line 179), which already guards this exact
   capability with `if complaint.status in FINAL_STATUSES: raise
   ValueError(ERR_COMPLAINT_ALREADY_CLOSED)`.

4. **New defect found in this slice (not previously flagged)**:
   `provider_offer_resolution` created and flushed the `ComplaintResolution`
   row *before* calling `self._transition(...)` to validate legality. An
   illegal-state offer therefore still wrote a resolution record to the
   database session ahead of the `ValueError`. Confirmed via a failing
   `db.add`-call-count assertion in the new test suite before the fix.

## What changed
1. **`app/engines/complaints/complaint_service.py`**
   - `provider_add_response`: added
     `if complaint.status in FINAL_STATUSES: raise ValueError(ERR_COMPLAINT_ALREADY_CLOSED)`,
     mirroring `add_customer_message`'s exact, pre-existing pattern. No
     new error code, no new status, no `ALLOWED_TRANSITIONS` change.
   - `provider_offer_resolution`: reordered so `self._transition(...)` is
     called *before* the `ComplaintResolution` row is constructed/added/
     flushed. No new status, no new transition, no new error code — purely
     a reordering to make an already-correct legality check also gate
     record creation.
2. **`frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx`**
   — added `isFinalState`/`canReplyOrOffer`; the "Reply to customer" input/
   button and "Offer resolution" button are now hidden once the complaint
   is `closed`/`cancelled`/`rejected`, matching the backend's own final-state
   policy for exactly these two operations. "Propose settlement" and the
   settlement accept/reject controls are untouched (different service
   methods, out of this slice's scope).
3. **New test file**: `tests/test_phase2f9a_complaints_state_machine.py`
   (30 tests) — full state matrix for both routes, repeated-action
   classification, audit-event proof, side-effect-safety proof, and 3
   drift-guard tests confirming the sibling/`_transition`/dual-acceptance
   patterns this slice relies on remain unmodified.
4. **Slice 2F-9 documentation corrected** — see `deferred-items.md`
   §Documentation Corrections below and the edited files themselves
   (`known-limitations.md`, `complaint-state-machine.md`, `approval-gate.md`,
   `deferred-items.md` in `phase-02a-slice-02f9/`).

## What did NOT change
No previously-closed module was touched. `complaints.customer_router`,
`complaints.admin_router`, `execution.real_estate_router` were not begun
or modified. No permission was created. No role was created. No new
status or transition was added to `ALLOWED_TRANSITIONS`/`ALLOWED_TRANSITIONS_EXT`.
No internal-note system, dispute interface, refund/cash-payment behavior,
or model merge was introduced. `readonly@demo-ac-services.local` and
migration 144 were untouched. No visual redesign occurred (2 button
visibility conditions only, same layout).

## Outcome
`SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_CLOSED` — see
`approval-gate.md`. Global tenant-mutation coverage unchanged: **106/182**
(re-verified via runtime inventory; no router-level guard changed).
