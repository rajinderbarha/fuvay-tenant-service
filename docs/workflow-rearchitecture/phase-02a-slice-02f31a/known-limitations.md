# Known Limitations

- **`confirm_upload` does not verify the storage object exists** before
  creating a `MediaFile` row. This is the reason the final status carries
  `_DOMAIN_INTEGRITY_BLOCKED` rather than a fully-closed status. See
  [database-storage-integrity-report.md](database-storage-integrity-report.md).
- **No cleanup job for expired upload sessions or their orphaned storage
  reservations.** Resource leak, not a security defect.
- **`GET /v1/media/tenants/{tenant_id}/quota` trusts its path `tenant_id`
  without comparing it to the caller's own tenant.** Out of this slice's
  mutation-only scope (read route); flagged for a future slice.
- **This closure is scoped to N01_media_assets only.** 24 canonical routes
  remain unprotected application-wide; this slice makes no claim about any
  of them.
