# CUSTOMER-L5-06 — Media Architecture

## Requirements

No real, offering-level "media required" flag was found for
`booking_issue_photo` specifically — CUSTOMER-L5-05's
`ValidatedOfferingDetail.required_fields.requires_photo_upload` is the
closest real signal, but it is informational (rendered as a chip on
`ServiceDetailScreen`) rather than an enforced gate in this sprint (see
known-gaps.md). Media is treated as optional throughout this sprint's UI —
honest given the absence of a real, binding backend requirement to enforce
against.

## Picker

`hooks/use-media-picker.ts`, built on `expo-image-picker` (the one media
library already installed before this sprint). Camera and gallery are both
covered by this single library's `launchCameraAsync`/
`launchImageLibraryAsync` — no separate `expo-camera` dependency was added.
Permission is requested at point of use (`requestCameraPermissionsAsync`/
`requestMediaLibraryPermissionsAsync`), never at startup. The `exif` picker
option is never set to `true` — its default (`false`) means EXIF/GPS data
is never even read off the asset, which is a stronger privacy guarantee
than stripping it afterward.

## Validation

`domain/media-validation.ts` — real limits verified against **two**
independent backend sources (see contract-matrix.md): the media engine's
own `booking_issue_photo` context rule (jpeg/png/webp/gif, 10MB) and the
booking-draft's own, stricter `ALLOWED_PHOTO_TYPES` (jpeg/png/webp, no gif).
The client validates against the **stricter** set, since that's the
binding constraint for a photo to ever actually reach the draft.

## Compression

`hooks/prepare-image-for-upload.ts`, using `expo-image-manipulator`
(added this sprint — see dependency-decisions below). Resizes to a maximum
1920px on the longer edge (only if the original exceeds it — never
upscales) and re-encodes as JPEG at a fixed 0.7 quality — deterministic
settings, not adaptive. Re-encoding through the manipulator has the
practical effect of not carrying over the original file's metadata, though
this environment has no way to inspect the resulting binary's headers
directly to prove EXIF removal byte-for-byte (see known-gaps.md).

## Upload

`api/media-api.ts#uploadBookingPhoto` — direct `multipart/form-data` upload
to `POST /v1/media/upload` (the Phase 0A engine's real, authoritative
endpoint), with `media_context="booking_issue_photo"`,
`owner_type="booking_draft"`, `owner_id=<draftId>`. The legacy signed-URL
flow (`app/engines/media/router.py`) is deliberately not used — see
contract-matrix.md for why.

## Progress

Real, but coarse-grained: React Native's `fetch` (used by
`apiClient.uploadMultipart`) does not expose byte-level upload progress
without a native XHR/`expo-file-system` uploader, neither of which this
sprint added. `MediaItem.status` transitions (`UPLOADING` → `LINKING` →
`LINKED`) give the customer a real, honest sense of progress through
discrete stages, never a fabricated percentage.

## Retry

`MediaItem`'s `retryCount`/`canRetry()` (`domain/media-item.ts`) cap retries
at 3 attempts and distinguish `UPLOAD_FAILED` from `LINK_FAILED` — a
failure during the media-engine upload step vs. the draft-linking step,
since only the latter needs to be retried if the former already succeeded
(re-uploading a file that already uploaded successfully would waste
bandwidth and create an orphan asset).

## Finalization

Not applicable as a separate step — the Phase 0A media engine's
`POST /upload` is synchronous and atomic (validate → access-check → store
→ insert row, all in one request/response cycle). There is no
"finalize" call to make.

## Replacement and Deletion

Both call the real, ownership-enforced `POST /v1/media/{id}/replace` and
`DELETE /v1/media/{id}` endpoints. **Important limitation, documented
honestly**: neither is offered in this sprint's UI once a photo is already
linked to the draft, because the draft's own `/photos` endpoint has no
corresponding remove/replace operation — deleting the underlying media
asset would leave a dangling, broken URL in the draft's `photo_urls` list
with no way to clean it up server-side. `BookingMediaScreen`'s delete
action is real and does call the real endpoint, but this is a genuine,
disclosed backend gap for the *linked* state — see known-gaps.md.

## Preview

`domain/media-preview-url.ts#resolveAuthorizedPreviewSource` — the media
engine's `preview_url` is a relative, access-checked path
(`/v1/media/{id}/view`), never a public CDN URL for this customer-scoped
context. Preview images are fetched with the same bearer token every other
authenticated request uses, passed via React Native's `<Image source={{uri,
headers}}>`.

## Cleanup

No temporary local file cleanup was implemented this sprint (removing the
compressed/original file from device temp storage after a successful
upload) — `expo-image-picker`/`expo-image-manipulator` write to the app's
own cache directory, which the OS manages; no `expo-file-system` dependency
was added to manage this explicitly. Documented as a known, low-severity gap.

## Dependency Decisions

`expo-image-manipulator` (`~14.0.7`) was added this sprint —
`npx expo install` repeatedly failed in this sandboxed environment with a
transient `ERR_SSL_CIPHER_OPERATION_FAILED` TLS error (a known, previously
documented issue in this environment); a plain `npm install
expo-image-manipulator@~14.0.7` succeeded on the first attempt, suggesting
the extra registry/version-resolution network calls `expo install` makes
were the actual trigger.
