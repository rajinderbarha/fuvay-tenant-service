# Service and Direct-Database Audit — Workstream 10

## Methods audited
`ServiceInvoiceService.create_invoice`, `.add_item`, `.issue_invoice`;
`ServicePaymentService.record_onsite_payment`.

## Registered callers (re-verified via grep across `app/`)
All 4 methods have **exactly one** caller each: the corresponding
endpoint in `invoice_payment/provider_router.py`. No other router,
service, worker, or background job calls any of these 4 methods.

## Strongest / weakest caller
Since each method has exactly one caller, strongest == weakest == the
now-guarded `provider_router.py` endpoint. There is no second, weaker
entry point into these exact service methods.

## Tenant ID source verification
Confirmed (source read, `provider_router.py`): every call passes
`tenant_id=str(user.tenant_id)` — the caller's own server-derived tenant
context — never a request-body or query-parameter value. A
request-provided tenant ID cannot override the principal's own scope
because no such parameter is ever accepted by these 4 endpoints.

## Object ownership / target membership
Verified at the service layer (pre-existing, re-confirmed unmodified):
`_assert_tenant` (invoice-level) and a direct `job.tenant_id`/`inv.tenant_id`
comparison (job/invoice-level) both raise `ERR_INVOICE_ACCESS_DENIED` on
mismatch.

## Status transition verification
`issue_invoice`: blocks re-issuing (`INV_ISSUED` check) +
`_assert_transition` state-machine call. `add_item`: blocks adding items
to a non-`INV_DRAFT` invoice. `record_onsite_payment`: blocks a duplicate
payment record when an existing `COLLECTED`/`VERIFIED` payment already
exists for the invoice. All pre-existing, unmodified.

## Direct database mutations
`issue_invoice` performs 2 direct SQLAlchemy Core `update()` statements
(on `ServiceInvoice` and `ServiceJob`) in addition to ORM attribute
mutation — re-verified as pre-existing, unmodified, and scoped by
`.where(ServiceInvoice.id == inv.id)` / `.where(ServiceJob.id == inv.job_id)`,
which only ever target the already-tenant-verified row loaded earlier in
the same call.

## Service-layer defense-in-depth
Not added this slice: since every one of these 4 service methods has
exactly one caller (the now-guarded router), and that caller is the only
connected entry point, there is no alternate/weaker path that would
require an independent service-layer permission re-check. Adding one
would be defense-in-depth for a bypass that does not exist — not
introduced, consistent with "do not claim repository-wide service
coverage" and "close directly connected bypasses only."

## Conclusion
Zero connected service bypasses found. No direct-database-mutation risk
beyond what the now-guarded router already controls.
