/**
 * Routes confirmed mounted: GET /v1/customer/categories,
 * /v1/customer/categories/{slug}, /v1/customer/categories/{slug}/
 * offerings. These are the real vertical/category discovery surface for
 * the customer app -- there is no separate "enabled verticals" bootstrap
 * endpoint for customers (see capability registry `appConfig.*` =
 * MISSING); category/offering visibility IS the vertical-enablement
 * signal this app must key off of.
 */
import { z } from "zod";

export const categoryDtoSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  vertical: z.string().nullable().optional(),
  is_active: z.boolean().optional(),
});
export type CategoryDto = z.infer<typeof categoryDtoSchema>;

export const offeringDtoSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  category_id: z.string(),
});
export type OfferingDto = z.infer<typeof offeringDtoSchema>;
