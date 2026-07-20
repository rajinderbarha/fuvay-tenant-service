# Quote Ownership & State Integrity

## Actual quote statuses (extracted from source, not invented)

`draft` (richer surface only, pre-send), `pending` (legacy surface's initial state),
`sent`, `approved`, `rejected`, `expired`.

## Verified

- Job belongs to tenant: `_get_job_for_quote_management`'s tenant_owner-own-tenant check (fixed
  this slice to also deny customer).
- Quote belongs to Job: `quote.job_id != job.id` checked explicitly in `send_job_quote`
  (`QUOTE_NOT_FOUND` if mismatched); `list_job_quotes`/`get_job_quote` filter by `job_id`.
- Customer belongs to Job/quote: `quote.customer_id != customer_id` in `respond_to_quote`
  (`NotFoundException`); `_get_quote_for_customer`'s equivalent check for
  `approve_job_quote`/`reject_job_quote`.
- Quote ID cannot be substituted across Jobs: verified via the `job_id`/`quote.job_id` match
  checks above.
- Customer ID cannot be substituted: fixed this slice (respond-to-quote-customer-authority.md).
- Quote amount cannot be changed by a customer decision route: `respond_to_quote`/
  `approve_job_quote`/`reject_job_quote` only ever write `status`/`responded_at`/`approved_at`/
  `rejected_at` — none touch `amount`/`total_amount`/`labour_amount`/`parts_amount` fields.
  Verified by direct source inspection of all three methods.
- Customer cannot create or send a provider quote: fixed this slice
  (`_get_job_for_quote_management` customer denial).
- Technician approving a provider quote: no route exists for this (`approve_job_quote`/
  `reject_job_quote` require `require_customer`) — technician is denied at the router.
- Repeated acceptance/rejection: rejected, not idempotent — `quote.status != "pending"` raises
  409 `CONFLICT` on any second call (`test_repeated_response_rejected`).
- Rejected quote creates no invoice/payment: `generate_invoice`/`record_payment` require
  `job.status in (SIGNED_OFF, COMPLETED)`/`job.invoice_id`, neither of which a rejected quote's
  `to_status = JS.QUOTE_REJECTED` transition satisfies or advances toward.
- Sent quote cannot bypass required prior state: `create_job_quote` requires
  `job.status == JS.ASSESSMENT_COMPLETE`; `send_job_quote` requires
  `JS.QUOTE_SENT in _resolve_transitions(job.job_type, job.status)`.
- Invalid state produces no mutation: all the above raise before any `db.add`/field mutation.
- Child records (spawned repair job) are not created before state validation: `respond_to_quote`
  only calls `_spawn_repair_from_consultation` after the `to_status not in allowed` check has
  already passed and `job.status` has already been updated.
