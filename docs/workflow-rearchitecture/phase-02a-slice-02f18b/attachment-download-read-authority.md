# Attachment Download/Read Authority

## Finding: already correct, pre-existing, unmodified by this or any prior platform_notifications slice

Retrieval happens entirely through `app.engines.media.new_router`'s own
routes (`GET /v1/media/{id}`, `GET /v1/media/{id}/view`,
`GET /v1/media/{id}/download`), NOT through any `platform_notifications`
route — `ChatMessage.media_urls` stores only the `media_id` reference; a
client fetches the actual file via the media engine's own routes.

Traced (`asset_service.py`):
- `get_asset(media_id)` → `_load(media_id)` (existence check) →
  `MediaAssetRecord.from_orm(asset)` →
  `self._access.assert_can_view(self.actor, rec)` — re-authorized on
  EVERY call, not cached from attach-time.
- `get_local_file_for_serve(media_id)` — same pattern, used by both
  `/view` and `/download`.

Consequences (all pre-existing, confirmed correct, not requiring a fix):
- **Access IS re-authorized at retrieval time.** A user who could attach
  an asset at time T does not get a permanent grant — every subsequent
  `/view`/`/download` call re-runs `assert_can_view`.
- **A URL does not grant access merely because it's known** — `preview_url`/
  `public_url` in `to_dict()` is only a real, browser-fetchable URL for
  genuinely `is_public=True` assets (CDN-backed) or a same-origin API path
  (`/v1/media/{id}/view`) that itself re-checks authorization — knowing the
  path is not sufficient, the request must still pass `assert_can_view`.
- **No permanent public URL for private assets** — confirmed: `is_public`
  gates whether `public_url` is even meaningful; a private asset's
  `preview_url` defaults to the authenticated API path, not a raw storage
  URL.
- **Customer cannot download provider-internal media** — `assert_can_view`'s
  customer branch requires exact `customer_id` match; a provider-internal
  (non-customer-context) asset falls to the tenant-scoped branch, which
  denies non-tenant-role actors (including customers) outright.
- **Foreign and missing assets are NOT privacy-equivalent at this layer**
  — `_load` (existence) raises a distinct `NotFoundException`
  (`error_code="NOT_FOUND"`, generic) from `assert_can_view`'s
  `MEDIA_ACCESS_DENIED`/`MEDIA_TENANT_SCOPE_VIOLATION`/
  `MEDIA_CUSTOMER_SCOPE_VIOLATION` (all distinct codes, likely distinct
  HTTP statuses via `_domain_code_status`'s generic mapping — `NOT_FOUND`
  → 404, the others → 403 via the `ACCESS_DENIED`/`DENIED` substring
  match... `MEDIA_TENANT_SCOPE_VIOLATION`/`MEDIA_CUSTOMER_SCOPE_VIOLATION`
  contain neither `NOT_FOUND` nor `ACCESS_DENIED`/`DENIED`/`FORBIDDEN`, so
  they fall to the generic 422 default). **This is a genuine, PRE-EXISTING
  gap in the general media engine's retrieval-path privacy** — distinct
  status codes/error codes for missing vs. foreign vs. wrong-tenant vs.
  wrong-customer.

## Disposition
This gap is in `app/engines/media/`, NOT `app/engines/platform_notifications/`.
Per this slice's OUT OF SCOPE ("Changes outside platform_notifications are
allowed only for an existing media authorization or retrieval bypass
DIRECTLY USED by these attachment records") — the retrieval-path privacy
gap is real but is a property of the GENERAL media engine (affects every
media context, not something introduced by or specific to chat
attachments), and fixing it would change error/status behavior for every
other engine that uses media (profile photos, complaints, reviews,
invoices, etc.), which is a app-wide blast radius far beyond this slice's
`platform_notifications`-only mandate. **Documented, not fixed** — see
`known-limitations.md` and `product-decisions-required.md`.
