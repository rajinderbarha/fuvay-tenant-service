# MediaAsset Model Lineage

`app.engines.media.models.MediaAsset` (table `media_assets`, migration 049)
— the authoritative media table. Full field classification:

| Field | Classification | Notes |
|---|---|---|
| `id` | AUTHORIZATION_EVIDENCE | primary key, the referenced `media_id` |
| `owner_type` | STORAGE_ONLY (not a reliable authorization signal) | free-form, caller-supplied at upload time (`"user"`, `"tenant"`, etc.) — NOT guaranteed to reference a chat thread/message/Job even for `media_context="chat_attachment"` uploads |
| `owner_id` | STORAGE_ONLY (same caveat as `owner_type`) | same |
| `tenant_id` | AUTHORIZATION_EVIDENCE | nullable; used by this slice for tenant-match (kept from 2F-18A) and by `MediaAccessService` |
| `customer_id` | AUTHORIZATION_EVIDENCE | nullable; used by this slice (NEW) for same-customer lineage, and by `MediaAccessService`'s customer-context branch |
| `uploaded_by_user_id` | AUTHORIZATION_EVIDENCE | used by `MediaAccessService.assert_can_view`'s fallback ("own media") branch |
| `media_context` | AUTHORIZATION_EVIDENCE (this slice) | used by this slice (NEW) to reject non-`chat_attachment` references; also drives `MediaAccessService`'s `CUSTOMER_CONTEXTS`/`PARTICIPANT_CONTEXTS` branching |
| `file_name_original`, `mime_type`, `file_extension`, `file_size_bytes` | STORAGE_ONLY | no authorization relevance |
| `storage_bucket`, `storage_key` | STORAGE_ONLY / NEVER_CLIENT_VISIBLE | internal storage location — `to_dict()` does NOT expose `storage_key`/`storage_bucket` at all, confirmed by direct read of `MediaAsset.to_dict()` — already correctly excluded from client-facing serialization |
| `storage_driver` | STORAGE_ONLY | `to_dict()` DOES expose this one field (e.g. `"local"`/`"s3"`) — a driver NAME, not a credential or key; no secret value is disclosed |
| `public_url` | VISIBILITY_EVIDENCE | only meaningful when `is_public=True` |
| `is_public` | VISIBILITY_EVIDENCE | consulted first in `MediaAccessService.assert_can_view` — public assets bypass all further checks |
| `access_level` | VISIBILITY_EVIDENCE (declared, not consulted) | column exists (`"tenant"` default) but `MediaAccessService.assert_can_view` does NOT branch on it anywhere in the current implementation — it is set but not read by the access-control logic; flagged, not fixed (would be a change to `access.py`, out of scope) |
| `status` | LIFECYCLE_EVIDENCE | used by this slice (NEW) — only `"active"` accepted |
| `deleted_at` | LIFECYCLE_EVIDENCE | used by this slice (NEW) — must be `NULL` |
| `checksum`, `width`, `height` | STORAGE_ONLY | no authorization relevance |
| `metadata_json` | NOT_PRESENT for authorization purposes | free-form JSONB, no authorization-relevant keys found in `access.py`'s usage |
| `created_at`, `updated_at` | LIFECYCLE_EVIDENCE (informational only) | not consulted for expiry/staleness anywhere in `access.py` |

## Fields explicitly NOT present (confirmed by full model read, not assumed)
- No `job_id` / `service_job_id` column.
- No `booking_id` / `service_booking_id` column.
- No `thread_id` / `conversation_id` column.
- No `message_id` column.
- No `quarantine_status` distinct from `status` (quarantine, if used, is
  expected to be expressed as a `status` value, e.g. `"quarantined"` —
  this slice's `status != "active"` check already covers any such value
  generically without needing to enumerate them).
- No explicit "expiry" column.

This confirms the mission's own premise: same-Job/same-thread/same-message
lineage genuinely CANNOT be proven from existing `MediaAsset` columns —
not a gap in this slice's investigation, a genuine schema limitation.
