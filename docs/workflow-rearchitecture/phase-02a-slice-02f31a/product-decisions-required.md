# Product Decisions Required

1. **Should `confirm_upload` verify storage-object existence before
   materializing a `MediaFile` row?** (see
   [database-storage-integrity-report.md](database-storage-integrity-report.md))
   This requires either a synchronous HEAD-check against the storage
   provider (adds latency/a new failure mode to confirm) or an async
   reconciliation job (adds infrastructure). Both are legitimate product
   choices with different cost/latency tradeoffs; this slice's scope did
   not authorize picking one.
2. **Should expired, never-confirmed `MediaUploadSession` rows and any
   orphaned storage objects they reference be cleaned up?** No cleanup job
   exists today. Not a security defect, but a resource-leak decision for
   product/infra to prioritize.
3. **Should `GET /v1/media/tenants/{tenant_id}/quota` gain the same
   `_require_trusted_tenant` check as its mutation siblings?** It is a read
   route, out of this slice's mutation-only scope, but shares the same
   "client-supplied tenant_id, no comparison to principal" shape. Flagged
   in [connected-read-privacy-audit.csv](connected-read-privacy-audit.csv)
   for a future slice's authorization.
