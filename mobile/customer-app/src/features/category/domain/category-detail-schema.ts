import { z } from "zod";

const httpsOrRelativeImageUrl = z
  .string()
  .refine((value) => value.startsWith("https://") || value.startsWith("/"), { message: "Image URLs must be https:// or a relative path." })
  .nullable();

/**
 * Mirrors app/engines/customer_flow/service.py#get_customer_category_detail
 * (GET /v1/customer/categories/{category_slug}) — see
 * CUSTOMER-L5-04-contract-matrix.md. There is no `parent_category_id` or
 * `subcategories` field anywhere in the backend model (ServiceCategory) —
 * this catalogue is genuinely flat, not a frontend omission.
 */
export const categoryDetailSchema = z.object({
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
  required_steps: z.array(z.string()),
  optional_steps: z.array(z.string()),
});

export type ValidatedCategoryDetail = z.infer<typeof categoryDetailSchema>;

export function parseCategoryDetail(payload: unknown): ValidatedCategoryDetail | null {
  const result = categoryDetailSchema.safeParse(payload);
  return result.success ? result.data : null;
}
