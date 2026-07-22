# Legacy/Unlinked Media Policy

## Required default: applied

Per the mission's required default ("Do not authorize attachment merely
because tenant_id matches. Reject use when current data cannot prove the
principal and target audience are authorized."), this slice's
`_validate_attachments` never authorizes on tenant match alone — tenant
match is one of five independent checks (context, lifecycle, tenant,
customer, `MediaAccessService`), ALL of which must pass.

## Rows lacking sufficient lineage

| Missing field | Behavior |
|---|---|
| No `customer_id` on the asset | The customer-lineage check (step 8e) is skipped (nothing to compare), but `MediaAccessService.assert_can_view`'s tenant-scoped branch and lifecycle/context checks still apply — a customer-less, tenant-less asset falls to the `uploaded_by_user_id` check, which still requires the ACTING principal to be the uploader. Not blanket-authorized. |
| No `tenant_id` on the asset | Same — `MediaAccessService` falls through to `uploaded_by_user_id` matching. A tenant-less asset is NOT automatically usable by anyone in any tenant. |
| No `uploaded_by_user_id` | Not possible — this column is `nullable=False` on `MediaAsset`, always populated. |
| Unknown/missing `media_context` | Rejected outright by this slice's context check (`!= "chat_attachment"` covers `None`/empty/any other value identically). |
| Legacy `MediaFile`/`MediaUploadSession` rows (the OLDER, pre-migration-049 tables) | **Not reachable at all** — `_validate_attachments` queries `MediaAsset` exclusively (`db.get(MediaAsset, asset_id)`); a `media_id` belonging only to the legacy `media_files`/`media_upload_sessions` tables (different primary-key space, different table) will simply not resolve — `db.get(MediaAsset, ...)` returns `None` → rejected as missing. No legacy row can ever be "accidentally" authorized through this path. |

## No narrow trusted exception is introduced
This slice does not create any bypass for "trusted" legacy media — every
row, old or new, linked or unlinked, goes through the SAME five checks.
The only bypass that exists is `MediaAccessService`'s own pre-existing
`is_public`/`super_admin` short-circuits, which are established platform
policy, not something this slice added.
