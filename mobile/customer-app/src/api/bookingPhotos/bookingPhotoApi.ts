import { z } from "zod";
import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";

/**
 * Photo attachments for a booking draft.
 *
 * This closes a gap where the whole feature existed server-side but was
 * unreachable from the app: the backend has always accepted
 * `POST /v1/media/upload` followed by
 * `POST /v1/customer/home-services/booking-drafts/{id}/photos`, and the
 * Booking Review adapter already read `photo_urls`, but nothing in the app
 * ever uploaded one. A customer describing "the AC is leaking from here"
 * had no way to show it.
 *
 * It is deliberately a TWO-step flow, mirroring the backend: the media
 * engine owns the bytes (scanning, quota, access control) and the booking
 * draft only ever stores a URL. Uploading does not attach; attaching is
 * what makes the photo part of the booking.
 */

/** Backend: `ALLOWED_PHOTO_TYPES` on the draft photo route. */
export const ALLOWED_PHOTO_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;

/** Backend: `DRAFT_MAX_PHOTOS`. Enforced here too so the picker can stop
 * the customer before a round-trip that would only 422. */
export const MAX_DRAFT_PHOTOS = 5;

/** Customers may only upload into a small set of contexts; this is the one
 * the media engine's access policy allows for booking imagery. */
const BOOKING_PHOTO_CONTEXT = "booking_issue_photo";

const mediaAssetSchema = z
  .object({
    id: z.string(),
    preview_url: z.string(),
    mime_type: z.string().optional(),
    file_size_bytes: z.number().optional(),
  })
  .passthrough();

const draftPhotosSchema = z
  .object({
    photo_urls: z.array(z.string()),
    draft_status: z.string(),
  })
  .passthrough();

export interface PickedPhoto {
  uri: string;
  mimeType: string;
  fileName: string;
}

/**
 * Step 1 — upload the bytes to the media engine.
 *
 * React Native's FormData takes `{ uri, name, type }` rather than a Blob;
 * the cast is required because the DOM lib types `append` as accepting only
 * `string | Blob`, which is not what this runtime implements.
 */
export async function uploadBookingPhoto(photo: PickedPhoto) {
  const form = new FormData();
  form.append(
    "file",
    { uri: photo.uri, name: photo.fileName, type: photo.mimeType } as unknown as Blob,
  );
  form.append("media_context", BOOKING_PHOTO_CONTEXT);
  form.append("owner_type", "customer");

  const res = await authenticatedRequest({
    method: "POST",
    path: "/v1/media/upload",
    body: form,
  });
  return parseApiSuccess(res.json, mediaAssetSchema);
}

/** Step 2 — attach an uploaded photo's URL to the draft. */
export async function attachPhotoToDraft(draftId: string, photoUrl: string) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/home-services/booking-drafts/${draftId}/photos`,
    body: { photo_url: photoUrl },
  });
  return parseApiSuccess(res.json, draftPhotosSchema);
}

/** Convenience: upload then attach, returning the draft's new photo list. */
export async function addPhotoToBookingDraft(draftId: string, photo: PickedPhoto) {
  const uploaded = await uploadBookingPhoto(photo);
  return attachPhotoToDraft(draftId, uploaded.data.preview_url);
}

/** Detach a photo from the draft. The media asset itself is left to the
 * media engine's retention rules -- the draft only ever held a reference. */
export async function removePhotoFromBookingDraft(draftId: string, photoUrl: string) {
  const res = await authenticatedRequest({
    method: "DELETE",
    path: `/v1/customer/home-services/booking-drafts/${draftId}/photos`,
    body: { photo_url: photoUrl },
  });
  return parseApiSuccess(res.json, draftPhotosSchema);
}
