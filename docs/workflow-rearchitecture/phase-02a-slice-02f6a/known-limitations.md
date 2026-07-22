# Known Limitations — Slice 2F-6A

1. **Frontend "Issue"/staff-action buttons not hidden from denied
   roles.** The backend now correctly rejects staff-issue and
   technician-any-action attempts, but the tenant-portal UI still
   renders the buttons for those roles. Not a security gap (backend
   authoritative, no mutation occurs) but a UX polish item. See
   `frontend-exposure-audit.md`.

2. **No positive-amount validation on `add_item`'s tax bucket.** Tax
   line items are summed as-is with no explicit sign validation (unlike
   quantity/unit_price, which are now validated). Not evidenced as
   exploitable — no test or product documentation suggests negative tax
   is a real vector — but noted for completeness.

3. **No per-item audit event for `add_item`.** Every other mutation in
   this file logs a `FinancialEvent`; `add_item` does not. Pre-existing,
   not introduced this slice, not fixed (design-choice, not mechanical).

4. **Empty-invoice issuance not blocked.** `issue_invoice` does not
   verify the invoice has at least one line item. Not conclusively
   proven to be a defect (see `invoice-state-machine.md`).

5. **No row-level locking anywhere in this module.** Concurrent
   duplicate-issue or duplicate-payment races are theoretically possible
   (see `duplicate-concurrency-review.md`) — a platform-wide,
   pre-existing gap, not redesigned here.

6. **Overpayment is rejected outright; no account-credit path exists**
   for excess payment. If this is ever desired, it is a distinct
   product/integration decision (see `product-decisions-required.md`).

7. **Technician access could be revisited** if a mobile/staff-app client
   is ever built for this capability — the current
   `TENANT_OWNER_OR_CANONICAL_STAFF` decision (corrected in Slice 2F-6B
   from an earlier, ambiguous "STAFF_ONLY" label) is evidence-based on
   the *current* absence of any such client, not a permanent
   architectural constraint.

8. **Product-policy questions left open by design**: whether
   staff/technician should ever get `FIELD_OPS_INVOICE_GEN`, and whether
   technician should ever be widened into
   `require_owner_or_office_staff_mutation`'s equivalent — both
   deliberate, policy-driven non-closures, not oversights.
