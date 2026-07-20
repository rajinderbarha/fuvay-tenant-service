# Slice 2F-10A Implementation Summary

## Scope
Complete the domain-integrity adjudication Slice 2F-10 left open:
`create_complaint`'s eligibility contract, `check_eligible`'s
advisory-vs-authoritative status, `create_refund_request_from_complaint`'s
silent-transition behavior, and `add_customer_message`'s resolved/settled
policy question.

## Findings and dispositions

1. **`check_eligible` is CANONICAL_CREATION_POLICY, not advisory.**
   Evidence: its record-status table (`ELIGIBLE_STATUSES`) carries real,
   deliberate product history (`MODULE-L5-02 bug #23`'s comment in
   `constants.py` explicitly describes a prior fix to this exact table
   to avoid making billed work uncontestable); its window/duplicate rules
   are backed by a real, configurable `ComplaintPolicy` model, not a
   stub; and dedicated (if previously unused) error constants
   (`ERR_COMPLAINT_NOT_ELIGIBLE`, `ERR_COMPLAINT_WINDOW_EXPIRED`,
   `ERR_COMPLAINT_DUPLICATE_OPEN`) already existed specifically for this
   contract. See `complaint-eligibility-contract.md`.

2. **`create_complaint` had a confirmed creation-eligibility bypass** —
   Slice 2F-10 wired in only the ownership half of this contract
   (duplicating `_fetch_record`/`_customer_owns_record` inline); status
   eligibility, filing window, and duplicate-open-complaint were not
   enforced at creation at all, only by the separate, un-consulted
   `check-eligible` GET endpoint. Fixed by having `create_complaint` call
   `check_eligible` directly as the single, shared, authoritative gate —
   the two can now never disagree for the same fixture.

3. **`create_refund_request_from_complaint`'s silent-skip-on-illegal-
   transition is NOT a defect** — existing tests
   (`test_refund_events_log_the_status_actually_applied`,
   `test_refund_path_advances_and_resolves_the_complaint`) prove this is
   deliberate, tested, load-bearing behavior shared by the entire refund
   lifecycle (`create_refund_request_from_complaint`,
   `admin_approve_refund`, `record_refund`). Classified
   REQUEST_ALLOWED_WITHOUT_COMPLAINT_TRANSITION_BY_POLICY. No code change
   was made; this slice adds direct tests proving the behavior across
   every relevant complaint status instead of assuming it, and confirms
   the one real defect in this area (`MODULE-L5-02 bug #31`, the
   audit-log truthfulness fix) was already closed before this slice.

4. **`add_customer_message`'s resolved/settled behavior remains a genuine,
   undecided product question** — no additional repository evidence was
   found this slice beyond what Slice 2F-9A/2F-10 already documented.
   Not changed.

## What changed
1. **`app/engines/complaints/eligibility_service.py`** —
   `check_eligible`'s return dict gained a `reason_code` field for each
   ineligibility case, mapped to the existing (previously unused)
   `ERR_COMPLAINT_NOT_ELIGIBLE`/`ERR_COMPLAINT_ACCESS_DENIED`/
   `ERR_COMPLAINT_WINDOW_EXPIRED`/`ERR_COMPLAINT_DUPLICATE_OPEN`
   constants — additive only, the human-readable `reason` string is
   unchanged.
2. **`app/engines/complaints/complaint_service.py`** — `create_complaint`
   now calls `self._eligibility.check_eligible(...)` and raises
   `ValueError(reason_code)` before constructing any `CustomerComplaint`
   row, replacing the narrower ownership-only check Slice 2F-10 added.
3. **`app/engines/complaints/refund_service.py`** — no functional change;
   reviewed and confirmed correct, with an explanatory comment recording
   the investigation and disposition.
4. **New test file**:
   `tests/test_phase2f10a_complaint_eligibility_and_refund_integrity.py`
   (25 tests) — eligibility contract rules, creation/check_eligible
   consistency, and refund silent-transition-is-intentional proof across
   every relevant complaint status.
5. Two pre-existing tests and one Slice 2F-10 test updated to stub
   `check_eligible` directly instead of the narrower `_fetch_record` stub
   they previously used.

## What did NOT change
`FINAL_STATUSES`, `ALLOWED_TRANSITIONS`/`ALLOWED_TRANSITIONS_EXT`,
`add_customer_message`, the refund lifecycle's transition rules, the
dual-acceptance settlement model, and `complaints.provider_router`/
`complaints.admin_router` were not modified. No frontend file was
modified (customer-app never calls `check-eligible` as a preflight at
all — see `frontend-preflight-alignment.md`). No permission or role was
created. `readonly@demo-ac-services.local` and migration 144 were
untouched.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
see `approval-gate.md`. Customer router coverage remains 8/8; provider
router remains 9/9; tenant mutation coverage remains 106/182.
