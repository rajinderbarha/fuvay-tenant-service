import { z } from "zod";

/**
 * Mirrors the real, tier-only contract of
 * app/engines/home_service_booking/service.py#confirm_price_choice — see
 * CUSTOMER-L5-10-contract-matrix.md. There is no bargain-session, offer,
 * or counteroffer model anywhere in the real backend (exhaustively
 * verified this sprint) — this schema is intentionally small because the
 * real capability is intentionally small: pick a tier, get the resolved
 * amount back.
 */
export const PRICE_TIERS = ["low", "mid", "high"] as const;
export type PriceTier = (typeof PRICE_TIERS)[number];

export const bookingSummarySchema = z.object({
  selected_tenant_id: z.string().nullable(),
  selected_provider_name: z.string().nullable(),
  selected_zipcode: z.string().nullable(),
  selected_price_tier: z.enum(PRICE_TIERS),
  customer_offer: z.number(),
  allowed_offer_min: z.number(),
  allowed_offer_max: z.number(),
  platform_fee_amount: z.number(),
  payment_mode: z.string().min(1),
});
export type ValidatedBookingSummary = z.infer<typeof bookingSummarySchema>;

export const confirmPriceChoiceResultSchema = z.object({
  booking_summary: bookingSummarySchema,
  draft_status: z.string().min(1),
});
export type ValidatedConfirmPriceChoiceResult = z.infer<typeof confirmPriceChoiceResultSchema>;

export function parseConfirmPriceChoiceResult(payload: unknown): ValidatedConfirmPriceChoiceResult | null {
  const result = confirmPriceChoiceResultSchema.safeParse(payload);
  return result.success ? result.data : null;
}
