import { z } from "zod";

/**
 * Mirrors the customer-facing subset of
 * app/engines/home_service_booking/service.py#match_provider_and_price's
 * response — see CUSTOMER-L5-08-contract-matrix.md. Deliberately has no key
 * for `selected_provider_price_options`/`area_market_comparison` (pricing
 * scope, CUSTOMER-L5-09); `z.object()`'s default unknown-key-stripping
 * makes it structurally impossible for the parsed type to carry those
 * fields, not merely a UI choice to hide them.
 */
export const matchedProviderSchema = z.object({
  tenant_id: z.string().min(1),
  provider_name: z.string().min(1),
  public_badges: z.array(z.string()),
  rating: z.number().nullable(),
  customer_visible_reason: z.string(),
});
export type ValidatedMatchedProvider = z.infer<typeof matchedProviderSchema>;

export const providerMatchResultSchema = z.object({
  selected_provider: matchedProviderSchema,
  draft_status: z.string().min(1),
});
export type ValidatedProviderMatchResult = z.infer<typeof providerMatchResultSchema>;

export function parseProviderMatchResult(payload: unknown): ValidatedProviderMatchResult | null {
  const result = providerMatchResultSchema.safeParse(payload);
  return result.success ? result.data : null;
}
