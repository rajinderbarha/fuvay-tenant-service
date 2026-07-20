# Approval Gate — Slice 2F-10A

## Status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Reasoning

### SECURITY_CLOSED: YES
All Slice 2F-10 role, ownership, resolution-cross-check, and settlement-
cross-check fixes remain intact and re-verified passing (164 targeted
tests). No new customer IDOR was found or introduced. No weaker
alternate caller exists (unchanged from Slice 2F-10's own audit, not
re-litigated).

### COMPLAINT_CREATION_INTEGRITY_CLOSED: YES
- **`check_eligible` classified**: CANONICAL_CREATION_POLICY, with direct
  evidence (not inference from "create_complaint didn't call it") — see
  `complaint-eligibility-contract.md`.
- **Linked-record status rules enforced**: yes, via the fix — proven for
  every relevant status combination in
  `complaint-creation-policy-matrix.csv`.
- **Filing-window behavior enforced**: yes, same fix — proven directly
  (`test_window_expired_returns_reason_code`,
  `test_within_window_is_eligible`).
- **Duplicate behavior explicit**: yes — `duplicate-complaint-behavior.md`,
  classified per-scenario, no invented constraint.
- **Existing-open-complaint behavior explicit**: yes — scoped to
  `OPEN_STATUSES`, proven not to block a new complaint once a prior one
  resolves/closes/cancels/rejects.
- **`check_eligible`/`create_complaint` consistency**: proven structurally
  (single shared call, not parallel logic) and directly via tests — see
  `eligibility-creation-consistency.md`.
- **Invalid creation causes no persistence**: proven for all 4
  reason-code families (`test_create_complaint_never_persists_when_ineligible`).

### REFUND_REQUEST_INTEGRITY_CLOSED: YES
- **Legal source states explicit**: `open`, `awaiting_provider_response`,
  `under_admin_review` — the only 3 `ALLOWED_TRANSITIONS` keys whose
  target set includes `refund_requested` (`refund-request-state-machine.md`).
- **Illegal states directly tested**: all 10 other relevant statuses,
  proven per-status (`test_refund_request_created_regardless_of_state`).
- **Silent transition failure cannot produce a successful inconsistent
  state**: investigated directly, found to be intentional and correctly
  audited (bug #31's own fix, re-verified) — not a defect requiring
  correction; the "successful create + silently skipped transition"
  outcome IS the proven, explicit policy here
  (REQUEST_ALLOWED_WITHOUT_COMPLAINT_TRANSITION_BY_POLICY), not an
  unacceptable inconsistency, because a `RefundRequest` is a review ask
  independent of the complaint's own bookkeeping status.
- **Repeated behavior explicit**: re-requesting while already
  `refund_requested` creates a second `RefundRequest` row (no dedup
  guard exists) but does not double-transition the complaint (already
  not a legal source for itself) — documented, not a financial defect
  since no financial effect exists in this method at all.
- **No financial/persistence side effects on invalid requests**: this
  method has no invalid-request rejection path at all by design (the
  request itself is never state-gated) — the only real invalid-request
  path is foreign-complaint ownership, which is rejected with zero
  persistence (re-verified, `test_foreign_complaint_still_rejected`).

### PRIVACY_CLOSED: YES
Unchanged from Slice 2F-10 — not re-investigated (no new privacy-related
finding this slice), reaffirmed via the unmodified, still-passing
regression suite.

### PRODUCT_POLICY_CLOSED: BLOCKED
One genuine, still-open question remains:
`add_customer_message`'s resolved/settled behavior (see
`product-decisions-required.md` item 1) — not decided, not changed,
conclusive evidence still absent.

## Final combined status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

This is now a fully supported claim: every domain-integrity question
Slice 2F-10 left open (`create_complaint`'s eligibility bypass,
`check_eligible`'s advisory/authoritative ambiguity,
`create_refund_request_from_complaint`'s unproven silent-transition
behavior) has been directly adjudicated with evidence and, where a real
defect existed, fixed and tested.

## Quality gates (40) — summary
All 40 satisfied and verified directly. Evidence distributed across the
other 17 files in this directory.

## Global coverage
Unchanged: customer router 8/8, provider router 9/9, tenant mutation
106/182.

## Stop condition honored
Only `app/engines/complaints/eligibility_service.py` and
`app/engines/complaints/complaint_service.py` were modified for
behavior; `refund_service.py` received an explanatory comment only, no
functional change. `complaints.provider_router` and
`complaints.admin_router` were not modified. No permission, role, or
financial workflow was created. No booking-pipeline merge occurred. No
frontend file was modified. `readonly@demo-ac-services.local` and
migration 144 were untouched. No visual redesign occurred. **Stopping
here per instruction — not beginning another router module.**
