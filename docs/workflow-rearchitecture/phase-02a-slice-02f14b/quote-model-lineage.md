# Quote Model Lineage

## Single model, two API surfaces

There is exactly one quote model reached by `field_ops.router`: **`JobQuote`** (table
`job_quotes`). Both the "legacy simple" surface (`create_quote` + `respond_to_quote` +
`list_quotes_by_job`) and the "richer line-item" surface (`create_job_quote` +
`send_job_quote` + `approve_job_quote` + `reject_job_quote` + `get_job_quote` +
`list_job_quotes`) read and write the **same table**. This was not previously documented as a
single lineage — Slice 2F-14/14A's docs discussed them as if potentially separate; this slice
confirms via direct source inspection (`select(JobQuote)` in every one of these methods) that
they are the same model.

## Fields

`id` (PK), `tenant_id`, `job_id`, `customer_id`, `amount`/`total_amount`
(+ `labour_amount`/`parts_amount`/`visit_fee`/`discount_amount`/`tax_amount` on the richer
surface), `quote_number`, `quote_type`, `status` (`draft`/`pending`/`sent`/`approved`/`rejected`/
`expired`), `created_by`/`created_by_staff_id`, `expires_at`, `responded_at`/`sent_at`/
`approved_at`/`rejected_at`, `findings_snapshot`, `recommendation_snapshot`,
`recommended_work`/`recommendation`, `notes`, `parts`, `rejection_reason`.

## Classification

`JobQuote` — **FIELD_OPS_PROVIDER_QUOTE** for the creation/send side (provider-authored,
provider-priced); **FIELD_OPS_CUSTOMER_QUOTE_DECISION** for the response side (`respond_to_quote`/
`approve_job_quote`/`reject_job_quote` only ever change `status`/`responded_at`/`approved_at`/
`rejected_at` — never `amount`/`total_amount`, so a customer decision cannot alter the price).

## Not the same as `quote_checklist`

`quote_checklist` (from Slice 2F-13/2F-14's boundary findings) is a completely distinct model
family belonging to the checklist-template pipeline (`ServiceChecklistTemplate`), unrelated to
`JobQuote`. No merge was made or considered.

## Invoice/payment relationship

`JobQuote` has no direct FK to `InvoiceRecord`/`PaymentRecord`. The connection is indirect: a
customer's quote approval moves `Job.status` to `QUOTE_APPROVED`, which is one of several
preconditions `generate_invoice` checks (`job.status in (SIGNED_OFF, COMPLETED)` — quote approval
alone does not satisfy this; work must still be started and completed first). See
quote-financial-boundary.md.
