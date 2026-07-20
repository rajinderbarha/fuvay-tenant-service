# Compensation / Idempotency Evidence (WS7)

## `confirm_upload` idempotency

`MediaService.confirm_upload` checks `sess.status == "confirmed"` and
raises `ServiceOSException("CONFLICT", "Upload already confirmed.")` on a
repeat call — confirming the same session twice is rejected, not silently
re-applied. This is a genuine idempotency guard against double-confirm, but
it is orthogonal to the missing storage-existence check documented in
[database-storage-integrity-report.md](database-storage-integrity-report.md):
the FIRST confirm still succeeds without verifying the object exists.

## `delete_file` idempotency

Soft delete (`is_deleted = True`) is naturally idempotent — deleting an
already-deleted file re-sets the same flag/timestamp with no side effect
beyond updating `deleted_at`. No storage-side compensation is needed
because no storage mutation occurs on this path (see the integrity
report).

## Expired-session cleanup

No cleanup job (cron/background task) exists for expired, never-confirmed
`MediaUploadSession` rows — confirmed by `git grep MediaUploadSession`
finding zero references outside `service.py`/`models.py`. An expired
session simply becomes permanently unconfirmable (the `expires_at` check
in `confirm_upload` blocks it) but is never purged, and any storage object
the client uploaded against its reserved key (if any) is never cleaned up
either. This is a resource-leak gap, not a correctness/security one — it
does not affect the authorization or privacy closure of these routes, and
is recorded here for completeness rather than fixed (out of this slice's
scope).

## No outbox/retry mechanism exists

There is no message queue, outbox table, or retry worker tied to media
uploads in this codebase. The "strategy" in practice is closest to
storage-first-then-DB for `upload_media`/`replace_media` (via
`MediaAssetService`, unmodified) with no compensating cleanup on DB-insert
failure, and DB-only (no storage write at all) for the 3 `router.py`
routes closed this slice. Neither is a formally engineered
compensation/idempotent-retry/outbox strategy — this is accurately reported
as an accepted, unresolved gap rather than claimed as one of the mission's
"proven" strategies.
