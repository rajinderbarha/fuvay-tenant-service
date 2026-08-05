import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { customerReviewReadResponseSchema, customerReviewWriteResponseSchema } from "../contracts/customerReview";

export async function getBookingRating(bookingId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `/v1/customer/bookings/${bookingId}/rating` });
  return parseApiSuccess(res.json, customerReviewReadResponseSchema);
}

export interface SubmitRatingInput {
  rating: number;
  comment?: string;
  tags?: string[];
}

/** Backend eligibility (`REVIEW_NOT_ELIGIBLE` / `REVIEW_ALREADY_SUBMITTED`)
 * is authoritative -- this call never assumes the booking is reviewable. */
export async function submitBookingRating(bookingId: string, input: SubmitRatingInput) {
  const res = await authenticatedRequest({
    method: "POST", path: `/v1/customer/bookings/${bookingId}/rating`,
    body: { rating: input.rating, comment: input.comment, tags: input.tags },
  });
  return parseApiSuccess(res.json, customerReviewWriteResponseSchema);
}
