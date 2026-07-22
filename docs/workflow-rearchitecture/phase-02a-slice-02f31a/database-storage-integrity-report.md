# Database/Storage Domain Integrity Report (WS7)

This is the decision point for the final status. It resolves Slice 2F-31's
open integrity blocker by actually tracing the real mutation ordering — it
does not assume or restate the prior slice's deferral.

## Real ordering, per route

### `POST /v1/media/upload/initiate`
1. Quota check (DB read).
2. `storage_key` computed server-side (no storage write yet — this route
   only *reserves* a key and returns an upload URL/params to the client).
3. `MediaUploadSession` row inserted (DB write, flushed).
4. Response returned with `upload_url`.

The actual file bytes are uploaded **directly from the client to the
storage provider** (Cloudinary or the S3-placeholder scheme) in a step this
service never observes. There is no storage mutation performed by this
service call at all — only a DB row reserving a key. No cross-system
ordering risk here: if the client never uploads, the session simply expires
unconfirmed (see "Known gap" below).

### `POST /v1/media/upload/{session_id}/confirm`
1. Session loaded (DB read), existence/ownership/expiry checked.
2. `MediaFile` row inserted, `MediaUploadSession.status = "confirmed"`
   (DB writes, single flush — both in the same transaction/session).
3. `_signed_url` computed (no I/O — pure string construction from the
   already-known `storage_key`).

**This is the actual integrity gap.** `confirm_upload` never verifies that
the file object named by `storage_key` actually exists in the storage
provider. A confirming call materializes a `MediaFile` DB row — with
`scan_status` hardcoded to `"clean"` — purely on the caller's say-so that
the upload succeeded. There is no HEAD/existence check against Cloudinary
or the storage backend before the row is created.

**Consequence, honestly stated:** a confirmed `MediaFile` row can reference
a storage object that was never actually uploaded (client abandoned the
upload but still called confirm), producing a "phantom" media record whose
signed URL 404s when accessed. This is a **data-integrity** defect
(DB/storage can diverge), not a **destructive** one — no existing file is
ever lost or overwritten as a result, because nothing is deleted or
replaced by this path.

### `DELETE /v1/media/tenants/{tenant_id}/files/{file_id}`
1. Tenant authority check (DB-free, WS4 fix).
2. `MediaFile` row loaded (DB read).
3. `f.is_deleted = True; f.deleted_at = utcnow()` — a **soft delete**. No
   storage-provider delete call is made anywhere in this method.

This is the important finding for the destructive-inconsistency question:
**this route never deletes the underlying storage object.** The DB row is
marked deleted; the storage object is simply orphaned (leaked, not lost).
There is therefore no scenario on this route where a DB commit can succeed
while storage data is destroyed, or vice versa — because storage is never
mutated here at all.

## Strategy classification

None of the 5 residual routes perform a genuine two-system write that both
must succeed or both must roll back:

- `initiate_upload`/`confirm_upload`/`delete_file` (router.py, DB-only
  mutations from this service's point of view) never call a storage
  provider API themselves.
- `upload_media`/`replace_media` (new_router.py, via `MediaAssetService` /
  `MediaStorageService`) DO perform a real storage write
  (`_store_local`/`_store_cloudinary`/etc.) followed by a DB insert — this
  is storage-first-then-DB. `MediaStorageService` and `MediaAssetService`
  were not modified this slice (no evidence required it — WS5), so their
  existing ordering is unchanged, and no compensating cleanup exists there
  either if the DB insert fails after a successful storage write (an
  orphaned storage object, not a destructive loss).

No route in this slice's scope destructively deletes a storage object
without independently confirming DB state, and no route destructively
deletes a DB row's underlying data without independently confirming storage
state. The only genuine defect is the missing existence check in
`confirm_upload`, which produces **leaked/phantom** records, not
**destroyed** ones.

## Decision

Cross-system atomicity is **not proven** for `confirm_upload` (no storage
existence verification), and no compensating-cleanup or outbox/retry
mechanism exists for it. This is a real, currently-unaddressed gap.
Fixing it (adding a storage HEAD-check before the DB insert, or an async
reconciliation job) is a data-integrity feature, not an authorization/
privacy fix, and was not authorized by this slice's scope — WS7 explicitly
permits stopping here rather than fabricating a fix or a false atomicity
claim.

However, no **credible destructive** inconsistency was found (nothing is
ever deleted from storage by these routes; `delete_file` is soft-delete
only). Per the mission's explicit allowance, this justifies
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` as the final status — the 5
routes are otherwise fully closed on authorization/privacy, but domain
integrity (specifically, `confirm_upload`'s missing storage-existence
verification) remains blocked and is reported here rather than claimed
resolved.

See [compensation-idempotency-evidence.md](compensation-idempotency-evidence.md)
for the idempotency angle and [known-limitations.md](known-limitations.md)
for the forward-looking gap statement.
