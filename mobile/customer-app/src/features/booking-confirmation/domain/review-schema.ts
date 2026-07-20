import { z } from "zod";
import { matchedProviderSchema } from "../../provider-matching/domain/provider-match-schema";
import { PRICE_TIERS } from "../../bargain/domain/bargain-schema";

/**
 * Mirrors the real, cumulative shape of
 * app/engines/home_service_booking/service.py#build_booking_summary's
 * response (`POST /{draftId}/summary`) — see
 * CUSTOMER-L5-11-contract-matrix.md. `booking_summary` is a merged JSON
 * blob accumulated across every prior sprint's writes to it
 * (confirm-price-choice, build_booking_summary itself) — every field here
 * is therefore optional/nullable except `ready_for_confirmation`, the one
 * field this endpoint always computes fresh.
 */
export const addressSnapshotSchema = z.object({
  address_line_1: z.string().nullable(),
  address_line_2: z.string().nullable(),
  landmark: z.string().nullable(),
  city: z.string().nullable(),
  state: z.string().nullable(),
  zipcode: z.string().nullable(),
  country: z.string().nullable(),
  name: z.string().nullable(),
  phone: z.string().nullable(),
});
export type ValidatedAddressSnapshot = z.infer<typeof addressSnapshotSchema>;

export const bookingSummarySchema = z.object({
  offering_name: z.string().nullable().optional(),
  offering_slug: z.string().nullable().optional(),
  issue_summary: z.string().nullable().optional(),
  address: addressSnapshotSchema.nullable().optional(),
  city: z.string().nullable().optional(),
  zipcode: z.string().nullable().optional(),
  preferred_date: z.string().nullable().optional(),
  preferred_time_window: z.string().nullable().optional(),
  selected_provider: matchedProviderSchema.nullable().optional(),
  serviceability: z.object({ serviceable: z.boolean(), status: z.string().nullable() }).optional(),
  ready_for_confirmation: z.boolean(),
  selected_price_tier: z.enum(PRICE_TIERS).nullable().optional(),
  customer_offer: z.number().nullable().optional(),
  payment_mode: z.string().nullable().optional(),
});
export type ValidatedBookingSummary = z.infer<typeof bookingSummarySchema>;

export const reviewResultSchema = z.object({
  booking_summary: bookingSummarySchema,
  draft_status: z.string().min(1),
});
export type ValidatedReviewResult = z.infer<typeof reviewResultSchema>;

export function parseReviewResult(payload: unknown): ValidatedReviewResult | null {
  const result = reviewResultSchema.safeParse(payload);
  return result.success ? result.data : null;
}
