import { z } from "zod";

const httpsOrRelativeImageUrl = z
  .string()
  .refine((value) => value.startsWith("https://") || value.startsWith("/"), { message: "Image URLs must be https:// or a relative path." })
  .nullable();

/** Runtime validation of GET /v1/customer/categories items — a backend field rename or malformed row must not crash the Home screen, only drop that one item. */
export const categorySummarySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1).max(200),
  slug: z.string().min(1).max(200),
  description: z.string().max(2000).nullable(),
  category_type: z.string().min(1).nullable(),
  icon_url: httpsOrRelativeImageUrl,
  banner_url: httpsOrRelativeImageUrl,
  customer_flow_type: z.string().min(1),
  frontend_component_key: z.string().nullable(),
  primary_engine_key: z.string().nullable(),
  available_offering_count: z.number().int().nonnegative(),
  display_order: z.number().int(),
});

export type ValidatedCategorySummary = z.infer<typeof categorySummarySchema>;

export const offeringSummarySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1).max(200),
  slug: z.string().min(1).max(200),
  description: z.string().max(2000).nullable(),
  offering_class: z.string().min(1),
  customer_flow_type: z.string().min(1),
  primary_engine_key: z.string().nullable(),
  pricing_model: z.string().min(1),
  starting_price: z.number().nonnegative(),
  visit_fee: z.number().nonnegative(),
  appointment_fee: z.number().nonnegative(),
  requires_type: z.boolean(),
  requires_brand: z.boolean(),
});

export type ValidatedOfferingSummary = z.infer<typeof offeringSummarySchema>;

/** Drops invalid items rather than failing the whole list — one malformed category must not blank the entire Home screen. */
export function parseCategoryList(items: unknown[]): { valid: ValidatedCategorySummary[]; droppedCount: number } {
  const valid: ValidatedCategorySummary[] = [];
  let droppedCount = 0;
  for (const item of items) {
    const result = categorySummarySchema.safeParse(item);
    if (result.success) valid.push(result.data);
    else droppedCount += 1;
  }
  return { valid, droppedCount };
}
