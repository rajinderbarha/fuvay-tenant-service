# Duplicate and Concurrency Behavior — Workstream 7

| Operation | Classification | Evidence |
|---|---|---|
| Duplicate invoice creation for the same ServiceJob | **DUPLICATE_REJECTED** | `create_invoice` queries for an existing non-cancelled invoice for the same `job_id` and raises `ERR_INVOICE_ALREADY_EXISTS` (pre-existing, unmodified) |
| Duplicate issue requests | **DUPLICATE_REJECTED** | `issue_invoice` explicitly checks `status == INV_ISSUED` before the general transition check (pre-existing, unmodified; directly tested this slice) |
| Duplicate payment recording | **DUPLICATE_REJECTED** | Pre-existing check against an existing `COLLECTED`/`VERIFIED` `ServicePaymentRecord`, now reinforced by this slice's new invoice-status precondition (defense-in-depth: once `payment_collected`, the status check alone also blocks a second call) |
| Duplicate item addition | **DUPLICATE_ALLOWED_BY_POLICY** | No de-duplication exists for adding the "same" item twice (e.g., two identical `item_name`/`unit_price` rows) — and none is evidenced as required; a legitimate invoice can contain two distinct line items with identical names/prices (e.g., two identical parts). Not classified as a defect. |
| Concurrent payment requests | **CONCURRENCY_RISK_DOCUMENTED** | No row-level lock is taken on the `ServiceInvoice` row before the duplicate-payment-record check; two simultaneous `record_onsite_payment` calls could theoretically both pass the "no existing COLLECTED record" check before either commits. This is the same platform-wide lockless pattern already documented for `finance_hub` (Slice 2F-5B) and `package_commerce` (Slice 2F-5C) — not unique to this module, not redesigned here. |
| Concurrent issue requests | **CONCURRENCY_RISK_DOCUMENTED** | Same lockless pattern; two simultaneous `issue_invoice` calls could theoretically both pass the `status != INV_ISSUED` check before either commits. |
| Transaction boundaries | Each mutation (`create_invoice`, `add_item`, `issue_invoice`, `record_onsite_payment`) commits within its own single request — no cross-request transaction spanning exists. |
| Row locking | **Not present** anywhere in this module (unlike `usage_credits.UsageCreditService._post`'s `with_for_update()`, noted as the stronger pattern in Slice 2F-5C). Documented, not added — adding row-locking here would be a persistence-architecture change, explicitly out of scope ("do not redesign transaction infrastructure"). |
| Unique constraints | Not verified at the database-schema level this slice (would require inspecting migrations, not done — the application-level duplicate checks are the actual, evidenced enforcement mechanism). |
| Idempotency keys | None exist on any of the 4 routes in this module (unlike `finance_hub`'s topup/deduction primitives, which do use idempotency keys via `UsageCreditService`). The application-level state/duplicate checks are the substitute mechanism. |
| Re-read-before-commit | Each mutation loads its target row once per request and acts on that same in-memory object through to commit — no re-read occurs mid-request. |

## Conclusion
No conclusively-provable, uniquely-`invoice_payment` concurrency defect
was found beyond the platform-wide, pre-existing lack of row locking
(already documented as a known limitation in two prior slices). Closing
it here would require a persistence-architecture change, out of this
slice's scope. All final-action duplicate scenarios (issue, payment,
invoice-per-job) are `DUPLICATE_REJECTED`, meeting the mission's
requirement that "duplicate final actions are prevented."
