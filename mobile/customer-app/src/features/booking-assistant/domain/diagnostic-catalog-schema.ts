import { z } from "zod";

/**
 * Mirrors app/engines/admin_catalog/service_option_service.py#get_customer_issue_types
 * (GET /v1/customer/catalog/issue-types) — see CUSTOMER-L5-05-contract-matrix.md.
 * `requires_photo`/`requires_description` are the only two genuine
 * backend-driven conditional-branching signals in this entire sprint.
 */
export const issueTypeSchema = z.object({
  issue_type_id: z.string().min(1),
  name: z.string().min(1).max(200),
  code: z.string().min(1),
  severity: z.string().min(1),
  is_common: z.boolean(),
  requires_photo: z.boolean(),
  requires_description: z.boolean(),
  display_order: z.number().int(),
});
export type ValidatedIssueType = z.infer<typeof issueTypeSchema>;

/** Mirrors #get_customer_options (GET /v1/customer/catalog/service-options). */
export const serviceOptionSchema = z.object({
  service_option_id: z.string().min(1),
  name: z.string().min(1).max(200),
  display_name: z.string().min(1).max(200),
  code: z.string().min(1),
  option_group_id: z.string().nullable(),
  is_required: z.boolean(),
  is_default: z.boolean(),
  display_order: z.number().int(),
});
export type ValidatedServiceOption = z.infer<typeof serviceOptionSchema>;

/** Mirrors AdminCatalogService._brand_dict (GET /v1/catalog/master/brands). */
export const brandSchema = z.object({
  brand_id: z.string().min(1),
  category_id: z.string().nullable(),
  name: z.string().min(1).max(200),
  slug: z.string().min(1),
  logo_url: z
    .string()
    .refine((value) => value.startsWith("https://") || value.startsWith("/"), { message: "Logo URLs must be https:// or a relative path." })
    .nullable(),
  description: z.string().nullable(),
  is_active: z.boolean(),
});
export type ValidatedBrand = z.infer<typeof brandSchema>;

/** Mirrors AdminCatalogService._type_dict (GET /v1/catalog/master/service-types). */
export const serviceTypeSchema = z.object({
  type_id: z.string().min(1),
  category_id: z.string().nullable(),
  name: z.string().min(1).max(200),
  slug: z.string().min(1),
  description: z.string().nullable(),
  icon_url: z.string().nullable(),
  is_active: z.boolean(),
});
export type ValidatedServiceType = z.infer<typeof serviceTypeSchema>;

function parseListDroppingInvalid<T>(schema: z.ZodType<T>, payload: unknown, unwrapKey?: string): { items: T[]; droppedCount: number } | null {
  let rawItems: unknown;
  if (Array.isArray(payload)) {
    rawItems = payload;
  } else if (unwrapKey && payload && typeof payload === "object" && Array.isArray((payload as Record<string, unknown>)[unwrapKey])) {
    rawItems = (payload as Record<string, unknown>)[unwrapKey];
  } else {
    return null;
  }

  const items: T[] = [];
  let droppedCount = 0;
  for (const raw of rawItems as unknown[]) {
    const result = schema.safeParse(raw);
    if (result.success) items.push(result.data);
    else droppedCount += 1;
  }
  return { items, droppedCount };
}

export function parseIssueTypeList(payload: unknown) {
  return parseListDroppingInvalid(issueTypeSchema, payload);
}
export function parseServiceOptionList(payload: unknown) {
  return parseListDroppingInvalid(serviceOptionSchema, payload);
}
export function parseBrandList(payload: unknown) {
  return parseListDroppingInvalid(brandSchema, payload, "brands");
}
export function parseServiceTypeList(payload: unknown) {
  return parseListDroppingInvalid(serviceTypeSchema, payload, "types");
}
