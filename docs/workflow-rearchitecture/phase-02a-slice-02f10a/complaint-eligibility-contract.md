# Complaint Eligibility Contract — Slice 2F-10A (Workstream 2)

## Rules evaluated by `check_eligible` (in order)
1. **Record type validity** — `record_type in VALID_RECORD_TYPES`, else
   raises `ERR_COMPLAINT_INVALID_RECORD_TYPE`.
2. **Record existence** — `_fetch_record`, else raises
   `ERR_COMPLAINT_RECORD_NOT_FOUND`.
3. **Record status eligibility** — `record.status in
   ELIGIBLE_STATUSES[record_type]`. Per-record-type sets, e.g.
   `service_job: {completed, work_done, cancelled, invoice_issued, paid}`.
   Not eligible → `{"eligible": false, "reason_code":
   ERR_COMPLAINT_NOT_ELIGIBLE}` (this slice added the `reason_code`
   field; the human-readable `reason` string is unchanged).
4. **Customer ownership** — `_customer_owns_record` (direct
   `record.customer_id` match, or a booking lookup for `service_job`
   records that only carry `booking_id`). Not owned → `reason_code:
   ERR_COMPLAINT_ACCESS_DENIED`.
5. **Filing window** — `age = now - record.created_at`; default 168h
   (7 days) unless a `ComplaintPolicy` row overrides
   `complaint_window_hours` (category-scoped, else a `policy_key="default"`
   row). Expired → `reason_code: ERR_COMPLAINT_WINDOW_EXPIRED`.
6. **Duplicate open complaint** — only checked when `complaint_type` is
   supplied and the resolved policy's `allow_duplicate_open_complaints`
   is falsy (default). Checks for an existing `CustomerComplaint` with
   the same `customer_id`/`record_type`/`record_id`/`complaint_type` in
   `OPEN_STATUSES` (`open`, `awaiting_provider_response`,
   `awaiting_customer_response`, `under_admin_review`,
   `resolution_proposed`). Found → `reason_code: ERR_COMPLAINT_DUPLICATE_OPEN`.

## Rules NOT present (confirmed absent, not assumed)
- No completion-prerequisite check distinct from status eligibility (the
  `ELIGIBLE_STATUSES` set itself encodes which "done" states qualify).
- No cancellation-specific restriction beyond `cancelled` being
  explicitly *included* in `service_booking`'s eligible-status set (a
  cancelled booking CAN be complained about — e.g. "you cancelled without
  notice").
- No previous-resolved-complaint check — a resolved complaint does not
  block a new one (only *open*-status duplicates are checked).
- No warranty/rework-specific window extension.
- No administrative override path in `check_eligible` itself (an admin
  filing on a customer's behalf, if it exists, is out of scope —
  `complaints.admin_router` untouched).
- No explicit timezone-naive handling bug — naive `created_at` values are
  defensively coerced to UTC (`if created_at.tzinfo is None:
  created_at.replace(tzinfo=timezone.utc)`).

## Callers of `check_eligible`
Exactly one: `customer_router.py`'s `GET /v1/customer/complaints/check-eligible`
(advisory preflight endpoint) — confirmed via full-repo grep.
`create_complaint` did **not** call it before this slice.

## Final disposition: CANONICAL_CREATION_POLICY
Not merely advisory. Reasoning (per the mission's explicit instruction
not to infer advisory status merely because `create_complaint` didn't
call it):
- `ELIGIBLE_STATUSES` has a real, documented product-history bug fix
  (`MODULE-L5-02 bug #23`) proving the record-status gate is treated as
  meaningful business policy, not a placeholder.
- `ComplaintPolicy` is a full, persisted, category/tenant-configurable
  model (`complaint_window_hours`, `allow_duplicate_open_complaints`) —
  production-grade policy infrastructure, not a stub.
- Dedicated error constants (`ERR_COMPLAINT_NOT_ELIGIBLE`,
  `ERR_COMPLAINT_WINDOW_EXPIRED`, `ERR_COMPLAINT_DUPLICATE_OPEN`) existed
  in `constants.py` specifically for these exact rules before this slice,
  evidencing original intent to enforce them as real, typed failures —
  they were simply never wired into a raise path.
- The name "eligibility" describes a gating concept ("am I allowed"),
  not a courtesy/informational one.

## Fix applied
`create_complaint` now calls `check_eligible` directly as its sole
eligibility gate (see `eligibility-creation-consistency.md`), closing the
bypass. `check_eligible`'s own dict-return contract (rather than raising
typed exceptions itself) is preserved unchanged — `create_complaint`
translates the dict's `reason_code` into a raised `ValueError`.
