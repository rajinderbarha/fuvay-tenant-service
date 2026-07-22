# Quote Financial Boundary

## Findings

Quote acceptance (`respond_to_quote`/`approve_job_quote`) transitions `Job.status` toward
`QUOTE_APPROVED` and, for consultations, triggers `_spawn_repair_from_consultation` — neither of
which creates an `InvoiceRecord`, `PaymentRecord`, or `CommissionRecord`. No quote route calls
`BillingService` directly (confirmed via source: `generate_invoice`/`record_payment`/
`deduct_commission`/`financial_close` are only reachable via `field_ops.router`'s dedicated
financial routes, gated separately and fixed for access-scope in Slice 2F-14A).

## Verified

- Quote acceptance alone does not fabricate a real payment: confirmed, no billing-service call
  in the quote-response path.
- Customer cannot modify provider amount fields: confirmed (quote-ownership-state-machine.md).
- Provider cannot record an arbitrary payment through a quote decision route: quote routes never
  call `record_payment`.
- Invoice/payment routes retain the Slice 2F-14A access-scope fixes: unchanged this slice,
  re-verified via regression (`test_financial_routes_use_tenant_mutation_permission` from
  Slice 2F-14A's test suite still passes).
- No duplicate invoice/payment from repeated quote response: `respond_to_quote` itself rejects a
  second call (409 `CONFLICT`) before any downstream effect could occur twice.
- Any real financial effect uses the canonical existing `BillingService`: confirmed, no new
  finance behavior was built.
- Denied quote actions (wrong persona, foreign quote, repeated call) trigger no financial side
  effect: all raise before any state mutation.
