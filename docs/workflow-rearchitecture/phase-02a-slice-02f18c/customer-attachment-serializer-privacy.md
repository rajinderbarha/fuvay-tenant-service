# Customer Attachment Serializer Privacy

## Verified (unchanged from 2F-18B, re-confirmed)
- `MediaAsset.to_dict()` never exposes `storage_key`/`storage_bucket`
  (confirmed absent from the method by direct read) — internal storage
  location never reaches any client, customer or otherwise.
- `ChatMessage.to_dict(viewer_type)` returns `{}` for any message not
  visible to the requesting `viewer_type` (2F-18/2F-18A) — a customer
  never sees a `provider_only`/`admin_only` message's `media_urls` field
  at all, since the whole message is filtered out.
- `platform_notifications` never calls `MediaAsset.to_dict()` directly —
  `ChatMessage.media_urls` only ever stores the raw `media_id`
  reference(s) the client itself supplied; actual asset metadata is
  fetched separately via `/v1/media/{id}`, which now (this slice) applies
  the SAME retrieval-time thread-authority check for `chat_attachment`
  assets.

## New this slice: retrieval-time enforcement closes the "return unauthorized ID" edge case
Previously, even though `MediaAsset.to_dict()` itself was safe, a customer
COULD receive a `media_id` reference in a message's `media_urls` (e.g. if
a provider mistakenly or maliciously attached an asset the customer
shouldn't see) and then successfully call `/v1/media/{id}` to actually
fetch it, if `MediaAccessService`'s tenant-wide-for-office/generic checks
happened to allow it. Now: since only `chat_attachment`-context assets can
be attached at all (2F-18B), and the thread-claim lock (this slice) ties
every claimed asset to exactly one thread, and retrieval now re-validates
`validate_thread_access` for that thread — a customer attempting to fetch
a `media_id` from a message in a thread they don't own is denied at
RETRIEVAL time even if the ID somehow reached their client (which itself
shouldn't happen given `is_visible_to` filtering, but this is genuine
defense-in-depth, not reliance on a single layer).

## Attachment URLs cannot be reused by a foreign principal
Confirmed: `preview_url`/`public_url` in `MediaAsset.to_dict()` defaults to
the authenticated API path (`/v1/media/{id}/view`), not a raw,
credential-free storage URL, for non-`is_public` assets — a foreign
principal possessing the URL still must pass the SAME retrieval-time
authorization (including, for `chat_attachment` assets, this slice's
thread-authority check) — knowing the URL confers no bypass.

## Nested serializers follow the same policy as direct reads
There is only ONE serialization path for `ChatMessage`/`MediaAsset` in
this module — no divergent "list" vs. "detail" nested-object shortcut
exists that could apply different filtering (confirmed by code read,
unchanged from 2F-18).
