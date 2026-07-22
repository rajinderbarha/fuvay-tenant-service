# Customer Media Privacy

## Verified
- **Customer may attach only assets they own or are already authorized to
  use** — `MediaAccessService.assert_can_view`'s customer branch requires
  `asset.customer_id == actor.user_id` exactly (no tenant-wide fallback
  for the customer role) — proven directly
  (`test_customer_cannot_attach_another_customers_upload`).
- **Customer cannot reference another customer's media** — same mechanism.
- **Customer cannot access provider-internal assets** — `chat_attachment`
  is the only context this slice permits at all, and it IS in
  `CUSTOMER_CONTEXTS`, so a customer's OWN chat-attachment upload is
  reachable by them; a `provider_document`-context asset is rejected by
  the `media_context` check before `MediaAccessService` is even consulted.
- **Customer response serializers expose only safe media fields** —
  `MediaAsset.to_dict()` (unchanged, pre-existing) exposes `id`,
  `owner_type`, `owner_id`, `tenant_id`, `customer_id`,
  `uploaded_by_user_id`, `media_context`, filename/mime/size, `storage_driver`
  (not the key), `is_public`, `access_level`, `status`, dimensions,
  `preview_url`, timestamps — no `storage_key`/`storage_bucket`
  (confirmed absent from `to_dict()`), no delivery-provider credentials.
  This is NOT modified by this slice — `platform_notifications` never
  calls `MediaAsset.to_dict()` at all; `ChatMessage.media_urls` only
  stores the raw `media_id`(s) the client already supplied, and the
  client fetches asset metadata separately via `/v1/media/{id}` (which
  applies the same `to_dict()`/`assert_can_view` pair).
- **Customer identity is principal-derived** — `actor_user_id`/`customer_id`
  in `customer_router.py` are always `uuid.UUID(u.user_id)` (JWT-derived),
  unchanged.
- **Foreign/missing attachment errors are privacy-equivalent** — within
  `platform_notifications`'s own attach-time check, YES (single error code
  for every rejection reason, this slice). At the media engine's OWN
  retrieval routes, NO (pre-existing, out-of-scope gap — see
  `attachment-download-read-authority.md`).

## Note: customer_router.py cannot currently send attachments at all
`customer_router.py`'s `SendMessageIn` schema has no media field (confirmed
in `attachment-route-inventory.csv`) — this slice's fixes apply to the
service-layer code path (`send_message`, reachable if that schema were
ever extended) but are not currently exercisable via any live customer
route. Documented for completeness, not treated as a live customer gap.
