# Deferred Items (explicitly out of Slice 2F-14, for a future slice)

- `field_ops.router`'s remaining 19 routes: `create_job`, `respond_to_quote`,
  `complete_assessment`, `start_assessment`, `close_job`, `convert_to_repair`,
  `deduct_commission`, `financial_close`, `generate_invoice`, `add_media`, `add_note`,
  `create_quote`, `create_job_quote`, `approve_job_quote`, `reject_job_quote`,
  `send_job_quote`, `record_payment`, `spawn_repair`, `void_job`.
- `JobNote`/`JobMedia` access-control fix (see product-decisions-required.md item 1).
- `checklist_router` (ServiceChecklistTemplate/Item, Slice 2F-13) — untouched, no shared bypass
  found requiring a fix.
- `quote_checklist`, `PartsRequest`, Booking Exception Resolution, Admin/Tenant My Work,
  Next-Action aggregation, customer quote approval UI, inspection functionality, offline sync,
  media infrastructure, customer signature infrastructure, PDF reports, supervisor/inspector/
  manager roles, migration 144, `readonly@demo-ac-services.local` remediation — all per the
  mission's explicit out-of-scope list, none begun.
- Legacy `Job.checklist`/`update_checklist` route deprecation decision (product call, see
  product-decisions-required.md item 2).
- A dedicated DB-level concurrency test for `_provision_job_checklist_items` (known-limitations.md
  item 2).
