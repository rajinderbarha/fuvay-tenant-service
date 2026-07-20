# CUSTOMER-L5-06 — Contract Matrix

Verified by direct reading of `app/engines/home_service_booking/customer_router.py`,
`service.py`, `models.py`, `constants.py`, and `app/engines/media/new_router.py`,
`asset_service.py`, `models.py`, `validation.py`, `access.py` — cross-checked by
an independent research pass reaching identical conclusions on every point.

## Booking Draft

| Concept | Backend contract | Auth | Client type | API method | Query/mutation | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Create draft | `POST /v1/customer/home-services/booking-drafts` (body: `category_slug`, `offering_slug`, optional `ai_session_id`) | Required | `ValidatedBookingDraft` | `draftApi.createDraft` | `useCreateDraft` | `BookingDraftScreen` | `draft-schema.test.ts` | MATCHED, with a structural caveat (see below) |
| Get draft | `GET /v1/customer/home-services/booking-drafts/{id}` | Required, ownership-enforced (403/404) | same | `draftApi.getDraft` | `useDraft` | `BookingDraftScreen` | same | MATCHED |
| Update draft | `PUT /v1/customer/home-services/booking-drafts/{id}` — accepted fields: `customer_name`, `customer_phone`, `city`, `zipcode`, `issue_summary`, `issue_details`, `preferred_date`, `preferred_time_window`, `offering_type_id`, `brand_id`, `address_id` | Required | same | `draftApi.updateDraft` | `useUpdateDraft` | `BookingDraftScreen` | same | MATCHED (partial — see mismatch below) |
| Cancel draft | `POST /{id}/cancel` (body: optional `reason`) | Required | `{ draft_status, message }` | `draftApi.cancelDraft` | `useCancelDraft` | `BookingDraftScreen` | `draft-schema.test.ts` | MATCHED |
| Add photo (link) | `POST /{id}/photos` (body: `photo_url`, `content_type`) | Required, ownership + terminal-status enforced | `{ photo_urls, draft_status }` | `draftApi.addPhoto` | `useLinkDraftPhoto` | `BookingMediaScreen` | `draft-schema.test.ts` | MATCHED |
| Remove/replace a linked photo | No endpoint exists — `/photos` is append-only, max 5, no delete/replace | — | — | — | — | Not offered in UI once linked (see known-gaps) | — | MISSING_BACKEND |
| Draft version / revision / ETag | No column exists on `HomeServiceBookingDraft` at all | — | — | — | — | No conflict-detection UI built | — | MISSING_BACKEND — not "not implemented," genuinely absent |
| Draft list / multiple drafts | No `GET /booking-drafts` (list) endpoint for customers — only `GET /{id}` | — | — | — | — | Single-active-draft policy assumed by necessity (see draft-architecture.md) | — | MISSING_BACKEND |
| `issue_type_id` sync | Column exists on the model; **not in the `PUT` endpoint's accepted-field list** | — | — | Not called for this field | — | Not synced — documented gap | — | MISMATCHED (real column, no real write path) |
| `service_option_ids_json` sync | Same — column exists, not accepted by `PUT` | — | — | Not called | — | Not synced — documented gap | — | MISMATCHED |
| `offering_type_id` sync | Accepted by `PUT`; mapped from CUSTOMER-L5-05's `service_type` answer (same documented-assumption caveat as L5-05) | — | — | `useUpdateDraft` | — | `BookingDraftScreen`, on draft creation | tested | MATCHED (with L5-05's carried-over naming assumption) |
| `brand_id` sync | Accepted by `PUT`; mapped from CUSTOMER-L5-05's `brand` answer | — | — | `useUpdateDraft` | — | Same | tested | MATCHED |
| `issue_summary` sync | Accepted by `PUT` (free text); mapped from CUSTOMER-L5-05's `issue_description`/`customer_note` answers, joined | — | — | `useUpdateDraft` | — | Same | tested | MATCHED |
| Draft creation against the actual selected service | `offering_slug` must resolve against `MasterService` (admin_catalog); CUSTOMER-L5-04's real `ServiceDetailScreen` is built on `MasterOffering` (customer_flow) — **no confirmed FK/slug bridge between the two tables** | — | — | Attempted with the real `category.slug`/`service.slug` already fetched by L5-04; a 422 `HOME_BOOKING_OFFERING_INVALID` is handled as an honest, non-crashing "this service isn't available for booking yet" error state | — | `BookingDraftScreen` | `draft-entry.test.ts` | MISMATCHED — the sprint's most consequential structural finding |

## Media Upload (Phase 0A Engine)

| Concept | Backend contract | Auth | Client type | API method | Query/mutation | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Upload | `POST /v1/media/upload` (multipart: `file`, `media_context="booking_issue_photo"`, `owner_type="booking_draft"`, `owner_id=<draftId>`, `is_public=false`) | Required | `ValidatedMediaAsset` | `mediaApi.upload` | `useUploadMedia` | `BookingMediaScreen` | `media-asset-schema.test.ts` | MATCHED |
| Get asset | `GET /v1/media/{id}` | Required, customer-scoped | same | `mediaApi.getAsset` | (used internally after upload) | — | same | MATCHED |
| List assets for a draft | `GET /v1/media?media_context=booking_issue_photo&owner_type=booking_draft&owner_id=<draftId>` | Required, server-side customer_id-filtered regardless of query params | `ValidatedMediaAsset[]` | `mediaApi.listAssets` | `useDraftMedia` | `BookingMediaScreen` | same | MATCHED |
| View/preview | `GET /v1/media/{id}/view` (access-checked, 302 redirect or local serve) | Required | URL string, used as `<Image source>` | `mediaApi.viewUrl` | — | `MediaPreview` component | — | MATCHED |
| Replace | `POST /v1/media/{id}/replace` (multipart `file`) | Required, ownership-enforced | `{ replaced_id, new_asset }` | `mediaApi.replace` | `useReplaceMedia` | `BookingMediaScreen` | `media-asset-schema.test.ts` | MATCHED — note: this replaces the *media asset*, not the draft's `photo_urls` entry (see gap above: the draft has no update path for an already-linked URL) |
| Delete | `DELETE /v1/media/{id}` (soft delete) | Required, ownership-enforced | `{ id, deleted }` | `mediaApi.delete` | `useDeleteMedia` | `BookingMediaScreen` | same | MATCHED — same draft-linkage caveat |
| Download | `GET /v1/media/{id}/download` | Required | URL string | `mediaApi.downloadUrl` | — | Not used this sprint (no product need for forced download in a booking-photo flow) | — | NOT_APPLICABLE (real, unused) |
| Signed URL / presigned POST | Legacy `router.py` flow exists (`/v1/media/upload/initiate` + `/confirm`) — placeholder S3 URL when no real provider configured, hardcoded `scan_status="clean"` | — | — | Not used | — | — | — | NOT_APPLICABLE — deliberately not used; the real, authoritative Phase 0A multipart flow is used instead |
| Malware scanning / content moderation | Does not exist — `MediaAsset` has no `scan_status` column at all; upload is synchronous, `status="active"` immediately | — | — | — | — | No processing/pending state shown — would be dishonest to show one | — | MISSING_BACKEND (confirmed absent, not deferred) |
| Upload progress | `fetch`-based multipart upload in React Native does not expose granular byte-level progress without a native XHR/`expo-file-system` uploader | — | — | Indeterminate progress state only (see media-architecture.md) | `useUploadMedia` | `BookingMediaScreen` | — | MISMATCHED — real upload, honest coarse-grained progress only |
| Client-side compression/EXIF stripping | No `expo-image-manipulator`/`expo-file-system` installed before this sprint | — | — | Added `expo-image-manipulator` this sprint (see dependency-decisions) | `prepareImageForUpload` | — | `media-preparation.test.ts` | MATCHED (dependency added this sprint) |
| Max photos per draft | `DRAFT_MAX_PHOTOS = 5` (booking-draft side) | — | enforced client-side pre-check + trusted server 422 | — | — | `BookingMediaScreen` | tested | MATCHED |
| Allowed types (draft-linking step) | `{"image/jpeg", "image/png", "image/webp"}` (stricter than the media engine's own `booking_issue_photo` rule, which also allows `image/gif`) | — | Client validates against the **stricter** draft-side set, since that's the binding constraint for what can actually be linked | — | — | — | tested | MATCHED |
| Max size | Media engine: 10 MB for `booking_issue_photo` (enforced server-side on the actual bytes). Draft side: `MAX_PHOTO_SIZE_BYTES` constant exists but is **never enforced** (the `/photos` endpoint never receives file bytes) | — | Client enforces 10 MB pre-upload | — | — | — | tested | MATCHED (client mirrors the binding media-engine limit) |

## Error Model

Both engines raise `ServiceOSException` with real, stable string codes
(`HOME_BOOKING_DRAFT_NOT_FOUND`, `HOME_BOOKING_DRAFT_ACCESS_DENIED`,
`HOME_BOOKING_DRAFT_TERMINAL_STATUS`, `HOME_BOOKING_CATEGORY_INVALID`,
`HOME_BOOKING_OFFERING_INVALID`, `HOME_BOOKING_PHOTO_UPLOAD_FAILED`,
`MEDIA_FILE_REQUIRED`, `MEDIA_CONTEXT_NOT_ALLOWED`, `MEDIA_TYPE_NOT_ALLOWED`,
`MEDIA_FILE_TOO_LARGE`, `MEDIA_ACCESS_DENIED`, `MEDIA_CUSTOMER_SCOPE_VIOLATION`,
`MEDIA_NOT_FOUND`), surfaced via HTTP status + JSON body, mapped by the
app's existing `normalizeApiError` into the stable `ApiErrorCategory` union
(unmodified this sprint) — no new error-handling layer was needed, only new
customer-facing message mappings (see failure-matrix.md).
