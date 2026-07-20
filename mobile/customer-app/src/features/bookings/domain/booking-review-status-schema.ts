import { z } from "zod";

/**
 * Mirrors the real response of
 * `GET /v1/customer/bookings/{bookingId}/rating` — used only to decide
 * review-boundary visibility (submission is out of this sprint's scope,
 * §36). A `null` review means either "no review yet" or "booking not
 * found/not owned" — this client only ever calls this after already
 * confirming ownership via the detail fetch, so that ambiguity never
 * produces a false positive (CUSTOMER-L5-12-contract-matrix.md).
 */
const existingReviewSchema = z.object({
  rating: z.number(),
  comment: z.string().nullable(),
  created_at: z.string().nullable(),
});

const bookingReviewStatusResponseSchema = z.object({
  review: existingReviewSchema.nullable(),
});
export type ValidatedExistingReview = z.infer<typeof existingReviewSchema>;

export function parseBookingReviewStatus(payload: unknown): { review: ValidatedExistingReview | null } | null {
  const result = bookingReviewStatusResponseSchema.safeParse(payload);
  return result.success ? result.data : null;
}
