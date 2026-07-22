# Quote Parent Pipeline Boundary

## Determined lineage
`quote_checklist`'s `job_id` resolves against `app.engines.final_records.models.ServiceJob` — confirmed by direct import and query in `quote_service.py::_get_job` (pre-existing) and `checklist_service.py::create_checklist` (added this slice, mirroring the same pattern).

## Explicitly NOT the following
- **field_ops.Job** — a completely separate model (`app/engines/field_ops/models.py`), with its own `JobQuote` capability (see `field-ops-quote-alternate-audit.md`). No FK, no shared table, no ID compatibility between `field_ops.Job.id` and `ServiceJob.id`.
- **Booking** — `booking_id` is denormalized (copied at creation from `job.booking_id`) onto every quote_checklist row for query convenience, but no quote_checklist model has an ORM relationship or FK constraint to `Booking`. All authorization and lifecycle logic reads through `ServiceJob`, never `Booking` directly.
- **ServiceBooking** — no reference anywhere in this module.

## No merges performed
This slice did not merge `field_ops.Job` with `ServiceJob`, did not merge `Booking` with `ServiceBooking`, did not adapt IDs between pipelines, and did not move `PartsRequest` into this module. `ServiceJobQuote`/`ServiceJobQuoteItem`/`ServiceJobChecklist`/`ServiceJobChecklistItem` remain their own distinct tables, unmodified in schema.

## Why this matters for authorization
Because the parent is `ServiceJob` (not `field_ops.Job`), the tenant-ownership check for every quote/checklist mutation must resolve through `ServiceJob.tenant_id`, not `field_ops.Job.tenant_id` — confirmed correct in `create_quote` (pre-existing) and now `create_checklist` (fixed this slice). Any future slice touching this module must continue to resolve ownership through `ServiceJob`, not attempt to reuse `field_ops.Job`'s own ownership helpers (which operate on an unrelated table).
