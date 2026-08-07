/**
 * DTO for GET /v1/customer/search (app/engines/customer_flow/router.py ->
 * CustomerCategoryFlowService.search).
 *
 * Returns two independent result sets: whole categories whose name matches,
 * and individual services. Both are already filtered server-side to
 * active + customer-visible catalog rows.
 *
 * CONFIRMED GAP: results are NOT filtered by the customer's ZIP -- the
 * endpoint has no zipcode parameter. A match can therefore name something
 * that is not bookable at the customer's location, so the caller is
 * responsible for reconciling against the Home payload's
 * `bookable_categories` before presenting anything as tappable.
 */
import { z } from "zod";

export const searchCategoryDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  icon_url: z.string().nullable().optional(),
});

export const searchOfferingDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  starting_price: z.number().nullable().optional(),
  /** Present on master_services-backed results so the caller can map an
   * offering back to the category it belongs to. */
  category_id: z.string().nullable().optional(),
});

export const customerSearchResponseSchema = z.object({
  query: z.string(),
  categories: z.array(searchCategoryDtoSchema).default([]),
  offerings: z.array(searchOfferingDtoSchema).default([]),
});

export type CustomerSearchResponseDto = z.infer<typeof customerSearchResponseSchema>;
