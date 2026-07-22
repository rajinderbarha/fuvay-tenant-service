# N01 Domain-Integrity Scope (frozen for Slice 2F-37)

Carried forward unchanged from Slice 2F-31A/2F-32/2F-33 — still open,
still non-canonical, still not reducing N01's protected count (238 of
N01's own routes remain `VERIFIED`; this backlog is orthogonal to
authorization coverage):

1. **`confirm_upload` storage-existence verification** —
   `MediaService.confirm_upload` materializes a `MediaFile` DB row
   without verifying the referenced storage object actually exists.
2. **Expired upload-session cleanup** — no cleanup job exists for
   expired, never-confirmed `MediaUploadSession` rows or any orphaned
   storage they may reference.
3. **Orphaned-storage cleanup** — related to #2; no reconciliation job
   exists between DB state and storage-provider state.
4. **Media quota GET tenant-trust tightening** — `GET /v1/media/
   tenants/{tenant_id}/quota` trusts its path `tenant_id` without
   comparing it to the caller's own tenant (a read-path gap, not a
   canonical mutation).

Slice 2F-37 freezes this list as a visible sub-scope requiring its own
future implementation slice — it does not remediate any of the 4 items,
and none of the 4 may silently disappear from the program.
