# Deferred Items

- Storage-existence verification for `confirm_upload` (WS7 gap; see
  [database-storage-integrity-report.md](database-storage-integrity-report.md)
  and [product-decisions-required.md](product-decisions-required.md)).
- Expired-session/orphaned-storage cleanup job.
- `GET /v1/media/tenants/{tenant_id}/quota` tenant-trust tightening.
- Selection of the next module/slice — explicitly out of scope per the
  mission ("do not select the next module").
