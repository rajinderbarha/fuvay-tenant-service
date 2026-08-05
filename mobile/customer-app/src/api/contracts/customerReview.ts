/**
 * DTO for `POST|GET /v1/customer/bookings/{bookingId}/rating` (confirmed
 * via direct read of `app/engines/home_service_assignment/customer_router.py`
 * -- both now return the identical allow-listed shape, never
 * `CustomerReview.to_dict()` verbatim).
 */
import { z } from "zod";

export const customerReviewDtoSchema = z.object({
  rating: z.number(),
  comment: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
  created_at: z.string().nullable(),
});
export type CustomerReviewDto = z.infer<typeof customerReviewDtoSchema>;

export const customerReviewReadResponseSchema = z.object({
  review: customerReviewDtoSchema.nullable(),
});

export const customerReviewWriteResponseSchema = z.object({
  review: customerReviewDtoSchema,
});
