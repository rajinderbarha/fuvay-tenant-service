/**
 * Real limits verified against two backend sources — see
 * CUSTOMER-L5-06-contract-matrix.md:
 *  - app/engines/media/validation.py CONTEXT_RULES["booking_issue_photo"]:
 *    {jpeg, png, webp, gif}, max 10MB — enforced on the actual bytes at
 *    upload time.
 *  - app/engines/home_service_booking/constants.py ALLOWED_PHOTO_TYPES:
 *    {jpeg, png, webp} (no gif) — enforced on the client-declared
 *    content_type when linking an already-uploaded photo to the draft.
 * The client validates against the *stricter* set (no gif) since that is
 * the binding constraint for a photo to ever actually reach the draft —
 * uploading a GIF would succeed at the media engine but then be rejected
 * when linking it, which would be a confusing, avoidable dead end.
 */
export const ALLOWED_BOOKING_PHOTO_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
export type AllowedBookingPhotoMimeType = (typeof ALLOWED_BOOKING_PHOTO_MIME_TYPES)[number];

export const MAX_BOOKING_PHOTO_SIZE_BYTES = 10 * 1024 * 1024;
export const MAX_BOOKING_PHOTOS_PER_DRAFT = 5;

export type MediaValidationFailure = "UNSUPPORTED_TYPE" | "TOO_LARGE" | "MISSING_URI" | "COUNT_LIMIT_REACHED";

export interface MediaCandidate {
  uri: string;
  mimeType: string | null;
  fileSizeBytes: number | null;
}

export function validateMediaCandidate(candidate: MediaCandidate, currentCount: number): MediaValidationFailure | null {
  if (!candidate.uri) return "MISSING_URI";
  if (currentCount >= MAX_BOOKING_PHOTOS_PER_DRAFT) return "COUNT_LIMIT_REACHED";
  if (!candidate.mimeType || !(ALLOWED_BOOKING_PHOTO_MIME_TYPES as readonly string[]).includes(candidate.mimeType)) return "UNSUPPORTED_TYPE";
  if (candidate.fileSizeBytes != null && candidate.fileSizeBytes > MAX_BOOKING_PHOTO_SIZE_BYTES) return "TOO_LARGE";
  return null;
}
