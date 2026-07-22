# Customer Approval Integrity

Direct tests performed (`tests/test_phase2f16_quote_checklist_authorization.py::TestCustomerDecisionOwnershipPreserved`, plus pre-existing `tests/test_sprint22_quote_checklist.py` coverage re-verified this slice):

| Test | Result |
|---|---|
| Correct customer approves own sent quote | Succeeds |
| Correct customer rejects own sent quote | Succeeds (pre-existing test, re-verified) |
| Foreign customer denied | `QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED`, zero persistence (`db.add.assert_not_called()`) |
| Provider actor denied from customer decision route | `require_customer` denies at the router before the handler runs (this slice's fix) |
| Technician denied from customer approval | `require_customer` denies (same mechanism) |
| Quote/Job/customer mismatch denied | Covered by `_assert_transition` (wrong state) and the `customer_id` ownership check (wrong customer) — both pre-existing, re-verified |
| Draft quote approval denied | `_assert_transition(q, QS_CUSTOMER_APPROVED)` — `QUOTE_TRANSITIONS[QS_DRAFT]` does not include `QS_CUSTOMER_APPROVED` (pre-existing, re-verified via full regression) |
| Expired quote approval denied | `QUOTE_TRANSITIONS[QS_EXPIRED] == set()` — no transition possible from a terminal state (pre-existing; also moot since no writer ever reaches `QS_EXPIRED` — see `known-limitations.md`) |
| Already-approved quote, repeated decision (same idempotency key) | Idempotent — returns the existing approved quote unchanged (pre-existing `customer_approve` logic, re-verified) |
| Already-approved quote, repeated decision (different idempotency key) | `QUOTE_IDEMPOTENCY_CONFLICT` (pre-existing, re-verified) |
| Already-rejected quote, repeated decision | `_assert_transition` — `QUOTE_TRANSITIONS[QS_CUSTOMER_REJECTED] == set()`, rejected before any mutation |
| Approval payload attempting amount modification | Not possible — the payload accepts no amount field at all (see `quote-amount-integrity.md`) |
| Rejection without required reason | `ERR_QUOTE_REJECTION_REASON_REQUIRED` if `reason` is blank/missing (pre-existing, re-verified) |
| No mutation on denied/invalid action | `db.add.assert_not_called()` proven for the foreign-customer case this slice; state-transition rejections raise before any `db.execute(update(...))` call (source-position unchanged) |

## Downstream Job effects occur only after approval validation succeeds
`_sync_job_status(db, q.job_id, JOB_STATUS_QUOTE_APPROVED)` is called AFTER `_assert_transition` and the ownership check both pass, and after the quote's own `status` update statement — confirmed by source position in `customer_approve` (unchanged this slice, only the `get_quote`/router-level fixes were made to this file's read paths, not to `customer_approve`'s own mutation logic).
