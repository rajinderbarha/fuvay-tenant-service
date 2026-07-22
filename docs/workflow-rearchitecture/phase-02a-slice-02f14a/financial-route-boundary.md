# Financial-Looking Route Boundary

## Routes inspected

`deduct_commission`, `financial_close`, `generate_invoice`, `record_payment` (plus `close_job`,
inspected alongside since it shares the same billing service and guard pattern).

## Findings

All five mutate real financial state (`CommissionRecord`, `InvoiceRecord`, `PaymentRecord`, and
`Job.commission_deducted`/`invoice_id`/`payment_id`/`status`) — not display-only records. All five
already routed through `BillingService._get_job_for_billing`, which enforces:
- `tenant_owner`: must own the job's tenant (404 otherwise).
- `staff`/`technician`: must be the assigned technician (403 otherwise).
- `super_admin`: platform-wide, unrestricted (existing, unchanged).

This ownership check was already correct and is unmodified this slice.

## Defect found and fixed

All five routes were gated with plain `require_permission(P.FIELD_OPS_JOBS_CLOSE)` —
**permission-only, not access-scope-aware** — the same defect class already fixed for
`assign_job`/`update_status` in Slice 2F-14 and for `checklist_router` in Slice 2F-13. A
tenant-side actor with a read-only access scope (`customer_support_limited`) could still perform
a real financial mutation. Fixed by upgrading all five to `require_tenant_mutation_permission`
(same permission constant, now access-scope-aware).

## Idempotency

- `record_payment`: guarded by `job.payment_id is not None` (409 `PAYMENT_ALREADY_RECORDED`).
- `deduct_commission`: guarded by `job.commission_deducted` (returns the existing commission
  record with `"idempotent": True` rather than double-deducting).
- `generate_invoice`: guarded by `job.invoice_id is not None` (409 `INVOICE_ALREADY_EXISTS`).
- `financial_close`: composed of the three above, inheriting their idempotency guards.
- `close_job` (`close_job_financial`): guarded by `job.status == JS.CLOSED` (409
  `JOB_ALREADY_CLOSED`) and requires `commission_deducted` first.

## Conclusion

No invented financial workflow was added. The authorization gap (permission-only, not
scope-aware) was real, live, and directly analogous to an already-established fix pattern — fixed
rather than deferred as a product question, per the mission's explicit instruction not to treat a
security gap as a product decision.
