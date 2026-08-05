import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { confirmDraftResponseSchema } from "../contracts/bookingReview";

/**
 * `POST /{draft_id}/confirm` -- confirmed idempotent server-side via
 * `ConfirmationLockService` (returns the SAME booking_number/booking_id on
 * a duplicate call with the same idempotency key, never a second
 * ServiceBooking/ServiceJob). The `Idempotency-Key` header is what the
 * backend keys that lock on; the caller must reuse the same key across
 * retries of the SAME confirm attempt (see idempotency/idempotencyStore.ts).
 */
export async function confirmDraft(draftId: string, idempotencyKey: string) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `/v1/customer/home-services/booking-drafts/${draftId}/confirm`,
    idempotencyKey,
  });
  return parseApiSuccess(res.json, confirmDraftResponseSchema);
}
