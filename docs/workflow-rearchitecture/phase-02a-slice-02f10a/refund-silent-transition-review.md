# Refund Silent-Transition Review — Slice 2F-10A (Workstream 8/9)

## Question
Can the complaint-status transition helper silently refuse while the
refund request is still reported as created successfully? **Yes — and
this is deliberate, tested, and shared across the whole refund
lifecycle, not a defect.**

## Evidence
1. `test_module_l5_02_complaints_flow.py::test_refund_events_log_the_status_actually_applied`'s
   own docstring states: *"the refund service's complaint transitions
   are a silent no-op when disallowed (deliberately — the skip is
   load-bearing for idempotent cases)"* — for all three of
   `create_refund_request_from_complaint`, `admin_approve_refund`, and
   `record_refund`.
2. `test_refund_path_advances_and_resolves_the_complaint` proves the
   *happy path* sequence (`open → refund_requested → refund_approved →
   refund_recorded → resolved`) works correctly when each step is called
   in its legal order — the silent-skip only matters for out-of-order or
   repeated calls, where it acts as an idempotent no-op rather than an
   error.
3. `MODULE-L5-02 bug #31`'s own fix (already applied, pre-existing) shows
   the team was already aware of and had already addressed the *one* real
   problem here: the audit event used to claim the transition happened
   (hardcoded `new_status`) even when it was skipped. That fix is intact
   and re-verified in this slice (`test_audit_event_logs_true_applied_status_not_claimed_one`).

## Direct test results (this slice)
`TestRefundRequestSilentTransitionIsIntentional` in
`test_phase2f10a_complaint_eligibility_and_refund_integrity.py` — ran
`create_refund_request_from_complaint` from all 13 relevant complaint
statuses:
- `open`, `awaiting_provider_response`, `under_admin_review` → `RefundRequest`
  created AND complaint transitions to `refund_requested`.
- All 10 other statuses (`resolution_proposed`, `rework_approved`,
  `resolved`, `settled`, `closed`, `cancelled`, `rejected`,
  `refund_requested`, `refund_approved`, `refund_recorded`) →
  `RefundRequest` still created (`db.add`/`db.commit` called), but
  `complaint.status` is left unchanged — proven directly per-status, not
  assumed.
- In every case, exactly one `RefundRequest` row and one audit event are
  created — no duplicate persistence, no double financial effect (there
  is no financial effect in this method at all — it only ever creates a
  `requested`-status record; no ledger/credit/deposit service is called
  here).

## Final disposition
**REQUEST_ALLOWED_WITHOUT_COMPLAINT_TRANSITION_BY_POLICY.** The refund
*request* (a customer asking for review) is intentionally decoupled from
whether the complaint's own status field can currently reflect that ask —
this matches the real-world semantics of "I'd like a refund reviewed,"
which should be recordable regardless of exactly which complaint state
the case happens to be in, while the complaint's own status only
advances when doing so is part of the normal linear flow.

## No fix applied
No code was changed. The one genuine defect in this area
(`MODULE-L5-02 bug #31`'s audit-truthfulness bug) was already fixed
before this slice began. This slice's contribution is proof, not
modification.
