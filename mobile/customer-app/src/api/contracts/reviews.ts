/** Route confirmed mounted: GET /v1/customer/reviews/eligibility,
 * GET/POST /v1/customer/reviews, GET/PATCH /v1/customer/reviews/{id}. */
import { z } from "zod";

export const reviewEligibilityDtoSchema = z.object({
  eligible: z.boolean(),
  reason: z.string().optional(),
});
export type ReviewEligibilityDto = z.infer<typeof reviewEligibilityDtoSchema>;

export const reviewDtoSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  rating: z.number(),
  comment: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
});
export type ReviewDto = z.infer<typeof reviewDtoSchema>;
