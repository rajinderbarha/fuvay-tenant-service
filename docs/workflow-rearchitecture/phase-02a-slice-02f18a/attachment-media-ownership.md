# Attachment/Media Ownership

## Disposition: ATTACHMENT_MODEL_SUPPORTED

`media_ids` (accepted on `SendMsgIn.media_ids` in `provider_router.py`, and
implicitly via `media_urls` in `chat_service.send_message`'s signature,
reachable from `customer_router.py` too) reference
`app.engines.media.models.MediaAsset` — a real, pre-existing model in this
codebase (`media_assets` table, columns include `tenant_id`, `owner_type`,
`owner_id`, `uploaded_by_user_id`). No new upload infrastructure was built
(per OUT OF SCOPE) — only a reference-validation step against the EXISTING
model.

## Implemented this slice
`ChatMessageService._validate_attachments(db, tenant_id, media_urls)`,
called from `send_message` before any `ChatMessage` is constructed:
1. If no `media_ids` present, no-op (attachment-free messages unaffected).
2. Each `media_id` must parse as a UUID — malformed values rejected
   (`test_malformed_media_id_rejected`).
3. Each `media_id` must resolve to a real `MediaAsset` row —
   `db.get(MediaAsset, asset_id)` — missing asset rejected
   (`test_nonexistent_media_asset_rejected`).
4. If the resolved asset has a `tenant_id` AND the sending thread has a
   `tenant_id`, they must match — cross-tenant asset rejected
   (`test_cross_tenant_media_asset_rejected`).
5. All rejections raise the SAME error code (`CHAT_ATTACHMENT_NOT_FOUND`)
   regardless of which condition failed — privacy equivalence (a caller
   cannot distinguish "doesn't exist" from "belongs to another tenant").

Same-tenant, existing assets are accepted unchanged
(`test_same_tenant_media_asset_accepted`).

## Not implemented (out of proportion for this slice)
- **Message-level attachment binding** (a formal `ChatMessageAttachment`
  join row) — attachments remain referenced via the existing
  `ChatMessage.media_urls` JSONB column (pre-existing schema, no migration
  possible this slice). "Belongs to the exact conversation/message" beyond
  tenant-match is therefore not independently verifiable (a same-tenant
  asset uploaded for an unrelated purpose could technically be referenced)
  — flagged in `known-limitations.md`, not silently claimed closed.
- **Uploader/owner authorization** (is the CALLER the asset's uploader or
  otherwise authorized to attach it) — only tenant-match is checked, not
  `uploaded_by_user_id`/`owner_id`. A same-tenant user could reference
  another same-tenant user's already-uploaded asset. Flagged, not fixed —
  building a full authorization check against the media engine's own
  access-control rules (`app/engines/media/access.py` exists and was NOT
  read/integrated this slice) was judged out of proportion without a
  dedicated pass on that engine's own semantics.
- **Deleted/quarantined attachment handling**: `MediaAsset` may have a
  status/soft-delete concept not consulted here — the current check only
  proves the row exists and matches tenant, not that it is active/approved.
  Flagged in `known-limitations.md`.

These three items keep `DOMAIN_INTEGRITY_CLOSED` from being unconditionally
claimed for attachments — the slice fixes the acute IDOR/cross-tenant risk
(the part directly reachable and provable without a deeper media-engine
integration) and honestly defers the rest.
