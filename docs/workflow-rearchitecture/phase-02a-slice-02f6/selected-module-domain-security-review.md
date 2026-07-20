# Domain Security Review — Workstream 8 (customer/complaint/operational + finance adaptation)

This module is finance-adjacent (invoice/payment recording) but is
executed by tenant staff against their own tenant's records, so the
review blends the mission's "finance" and "customer/operational record"
domain checklists.

## Customer/operational-record checklist (applied)
- **IDOR / cross-tenant targeting**: `invoice_id` and `job_id` are
  path/body parameters, but every service method loads the target row
  first and then compares its `tenant_id` against the caller's own
  server-derived `tenant_id` (`_assert_tenant` / direct comparison +
  `ERR_INVOICE_ACCESS_DENIED`) — re-verified via source read for all 4
  routes, unmodified this slice. A cross-tenant `invoice_id`/`job_id`
  guess is rejected with 403, not a silent success or a different error
  shape that would leak existence.
- **Tenant isolation**: confirmed — `tenant_id` is never accepted from
  the client in any of the 4 routes; it always comes from
  `str(user.tenant_id)`.
- **Assignment/object ownership**: no per-job-assignment check exists
  (i.e., a `staff` or `technician` account is not restricted to only the
  specific job(s) they were personally assigned) — any staff/technician
  within the correct tenant can create/pay any invoice in that tenant.
  This matches the existing `FIELD_OPS_JOBS_CLOSE` permission's
  documented scope ("close own jobs" is enforced elsewhere in the
  ServiceJob execution pipeline, not in this invoice module) and is
  **not** a new gap introduced or found this slice — the mission's
  in-scope fix was role/permission separation (previously absent
  entirely), not per-job delegation depth, which was not evidenced as
  broken by any test or audit finding.
- **Status transitions**: `issue_invoice` blocks re-issuing an
  already-issued invoice; `add_item` blocks adding items to a non-draft
  invoice; `record_onsite_payment` blocks a duplicate payment record for
  an invoice already in `COLLECTED`/`VERIFIED` status — all pre-existing,
  re-verified via source read, unmodified.
- **Sensitive notes/bulk actions**: not applicable — no notes field, no
  bulk-mutation endpoint in this module.

## Finance-adjacent checklist (applied)
- **Client-supplied amounts**: `collected_amount` (payment) and
  `unit_price`/`quantity` (invoice item) are client-supplied — no
  positivity/range validation was found in `record_onsite_payment` or
  `add_item` for these fields. This is a **pre-existing** gap, not
  introduced this slice, and fixing it would require adding new
  validation logic not evidenced elsewhere in this exact file (unlike
  `package_commerce`'s `update_package`, which already had a proven
  validation pattern to mirror). Logged as a known limitation, not fixed
  — the mission's "close only conclusively proven, safely-fixable"
  criterion counsels against inventing a new validation threshold
  (e.g., "reject negative price") without an existing analogous pattern
  in this exact service.
- **Range/tier minimums, bargain floors**: not applicable — no
  price-tier/bargain-floor concept exists in the invoice-item model.
- **Bulk updates**: none present.
- **Published-price impact**: not applicable — invoices are per-job
  documents, not a shared price catalog.

## Conclusion
The primary, conclusively-provable defect (complete absence of
role/permission enforcement) is fixed. Two lower-severity, pre-existing
items (no per-assignment job restriction; no positive-amount validation
on payment/item amounts) are documented as known limitations, consistent
with the "close only conclusively proven defects" instruction — neither
was introduced this slice, and fixing either would require either a
new validation rule with no existing in-file precedent, or expanding
scope into the ServiceJob-assignment pipeline (a different, already-
closed module's territory).
