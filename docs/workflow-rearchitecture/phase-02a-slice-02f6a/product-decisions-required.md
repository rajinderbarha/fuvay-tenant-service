# Product Decisions Required — Slice 2F-6A (not resolved this slice)

## 1. Should technician ever be granted access to any of the 3
   staff-or-above capabilities?
Per `technician-persona-decision.md`, no product evidence (mobile
caller, test, documented workflow) currently supports technician access
to `provider_record_payment`/`staff_create_invoice`/`staff_add_invoice_item`.
If a future product decision wants technicians to record payments or
create invoices directly from a mobile app, that would require: (a)
building the mobile caller, and (b) then reconsidering whether
`require_owner_or_office_staff_mutation` should be widened back to
`require_staff_or_above_mutation` for the specific capability being
extended. Not decided here.

## 2. Should `staff` (or technician) ever be granted `FIELD_OPS_INVOICE_GEN`?
Carried over from Slice 2F-6, still unresolved. `provider_issue_invoice`
remains tenant_owner-only.

## 3. Frontend button visibility
The tenant-portal invoice page does not hide the "Issue" button from
non-owner roles, nor the 3 staff-gated buttons from non-owner/non-staff
roles. A scoped follow-up could add a role check to this one page
component. Not made this slice (see `frontend-exposure-audit.md`).

## 4. Overpayment / account-credit policy
This slice rejects any `collected_amount` exceeding the invoice's
`customer_payable_amount`. If the product wants to support overpayment
with the excess applied as a customer credit (a genuinely different
capability, already partially modeled elsewhere via
`customer_credits.CustomerCreditService`), that would be a new
integration decision, not made here — "do not invent account-credit
behavior."

## 5. Empty-invoice issuance
`issue_invoice` does not check whether the invoice has any line items
before issuing. Not conclusively proven to be a defect (a single
flat-charge invoice with zero itemized lines but a nonzero
`total_amount` seeded from booking price is plausible) — flagged, not
acted on.

## 6. Missing audit event for `add_item`
`add_item` does not call an audit-logging function, unlike every other
mutation in this file. A future slice should decide the event-name/
payload convention and add it.

## Recommendation (non-binding)
None of these block security or financial-integrity closure. The
frontend button-visibility item (#3) is the most user-visible and
lowest-risk to address next, if prioritized.
