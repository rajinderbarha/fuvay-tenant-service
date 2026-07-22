# Parts / Quote Boundary

Confirmed unchanged this slice:

- `PartsRequest` links only to `ServiceJob` (not `field_ops.Job`). Technician may request/view
  ServiceJob parts; provider may approve/reject/install ServiceJob parts; technician may NOT
  install parts. No FK, adapter, or lookup was added connecting `PartsRequest` to `field_ops.Job`.
- `quote_checklist` remains distinct from `JobChecklistItem`. `field_ops.Job`'s own `JobQuote`
  model (assessment-driven price quote for repair/consultation jobs) is a separate, unrelated
  quote flow, exposed only via `field_ops.router`'s quote routes (`create_job_quote`,
  `approve_job_quote`, `reject_job_quote`, `send_job_quote`, `respond_to_quote`) — all among the
  19 routes explicitly out of scope this slice (distinct capability: billing/quotes).

No cross-pipeline adapter was created. See job-pipeline-boundary.md.
