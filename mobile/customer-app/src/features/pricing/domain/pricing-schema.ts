import { z } from "zod";
import { matchedProviderSchema } from "../../provider-matching/domain/provider-match-schema";

/**
 * Mirrors the customer-relevant subset of
 * app/engines/home_service_booking/service.py#match_provider_and_price's
 * response — see CUSTOMER-L5-09-contract-matrix.md. Reuses L5-08's
 * `matchedProviderSchema` for `selected_provider` (same endpoint, same real
 * fields). Deliberately has no key for `area_market_comparison` or the
 * admin-only fields — `z.object()`'s default unknown-key-stripping makes
 * it structurally impossible for the parsed type to carry them.
 *
 * `allowed_offer_min`/`allowed_offer_max`/`platform_fee_percent`/
 * `platform_fee_amount` ARE accepted (unlike L5-08's schema, which excluded
 * the whole price-options object) because they arrive as part of the same
 * flat object as the customer-visible `low_price`/`mid_price`/`high_price`
 * — but this sprint's UI never renders them (see contract-matrix.md's
 * INTERNAL_ONLY classification); only the parser accepts them so a real
 * response is not rejected outright.
 */
export const priceOptionsSchema = z.object({
  currency: z.string().min(1),
  low_price: z.number(),
  mid_price: z.number(),
  high_price: z.number(),
  allowed_offer_min: z.number(),
  allowed_offer_max: z.number(),
  platform_fee_percent: z.number(),
  platform_fee_amount: z.number(),
  payment_mode: z.string().min(1),
});
export type ValidatedPriceOptions = z.infer<typeof priceOptionsSchema>;

export const priceEstimateResultSchema = z.object({
  selected_provider: matchedProviderSchema,
  selected_provider_price_options: priceOptionsSchema,
  draft_status: z.string().min(1),
});
export type ValidatedPriceEstimateResult = z.infer<typeof priceEstimateResultSchema>;

export function parsePriceEstimateResult(payload: unknown): ValidatedPriceEstimateResult | null {
  const result = priceEstimateResultSchema.safeParse(payload);
  return result.success ? result.data : null;
}

/**
 * Real, backend-confirmed degenerate case (matching_engine.py's formula can
 * legitimately produce low_price === high_price when
 * BargainRule.customer_min_price === customer_max_price) — not a separate
 * fabricated "FIXED" pricing model, just the real range collapsing to one
 * point. See CUSTOMER-L5-09-pricing-semantics.md.
 */
export function isSinglePointEstimate(options: ValidatedPriceOptions): boolean {
  return options.low_price === options.high_price;
}
