import { z } from "zod";
import { matchedProviderSchema } from "../../provider-matching/domain/provider-match-schema";
import { addressSnapshotSchema } from "./review-schema";

/**
 * Mirrors the real response of
 * app/engines/home_service_booking/customer_router.py's
 * `POST /{draftId}/confirm` (delegating to
 * `HomeServiceFinalCreationService.finalize()`) — see
 * CUSTOMER-L5-11-contract-matrix.md. On an idempotent retry the backend
 * returns a smaller object (only `idempotent/booking_number/booking_id/
 * confirmation_id`) — every field beyond those three is therefore
 * optional here, not because the data is untrustworthy but because the
 * real contract genuinely omits it on that path.
 */
export const confirmBookingResultSchema = z.object({
  idempotent: z.boolean(),
  booking_number: z.string().min(1),
  booking_id: z.string().min(1),
  confirmation_id: z.string().min(1),
  job_number: z.string().optional(),
  job_id: z.string().optional(),
  status: z.string().optional(),
  booking_status: z.string().optional(),
  selected_provider_tenant_id: z.string().nullable().optional(),
  selected_price_option: z.string().nullable().optional(),
  selected_price_amount: z.number().nullable().optional(),
  payment_mode: z.string().optional(),
});
export type ValidatedConfirmBookingResult = z.infer<typeof confirmBookingResultSchema>;

export function parseConfirmBookingResult(payload: unknown): ValidatedConfirmBookingResult | null {
  const result = confirmBookingResultSchema.safeParse(payload);
  return result.success ? result.data : null;
}

/**
 * Mirrors ServiceBooking.to_dict() (app/engines/final_records/models.py)
 * from `GET /v1/customer/my-activity/bookings/{bookingId}` — the real
 * canonical booking record, fetched after confirmation rather than
 * trusting the mutation response alone (CUSTOMER-L5-11 §45).
 *
 * `provider_snapshot` reuses `matchedProviderSchema` deliberately: the
 * real backend field is confirmed to be the RAW, unstripped
 * `draft.selected_provider_snapshot` (including `internal_score`/
 * `matching_score_snapshot`) — unlike `booking_summary.selected_provider`,
 * which `build_booking_summary` strips server-side. Reusing the same
 * 5-field schema here means `z.object()`'s default unknown-key-stripping
 * removes those two internal-only keys structurally, on the client, since
 * the backend does not do it for this specific field. See
 * CUSTOMER-L5-11-security-review.md.
 */
export const bookingPriceSnapshotSchema = z.object({
  currency: z.string().optional(),
  selected_price_option: z.string().nullable().optional(),
  selected_price_amount: z.number().nullable().optional(),
  payment_mode: z.string().optional(),
});

export const bookingJobSchema = z.object({
  id: z.string().min(1),
  job_number: z.string().min(1),
  status: z.string().min(1),
});

export const bookingDetailSchema = z.object({
  id: z.string().min(1),
  booking_number: z.string().min(1),
  draft_id: z.string().min(1),
  customer_name: z.string().nullable(),
  customer_phone: z.string().nullable(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  address_snapshot: addressSnapshotSchema.nullable(),
  preferred_date: z.string().nullable(),
  preferred_time_window: z.string().nullable(),
  price_snapshot: bookingPriceSnapshotSchema.nullable(),
  provider_snapshot: matchedProviderSchema.nullable(),
  issue_summary: z.string().nullable(),
  status: z.string().min(1),
  failure_reason: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  job: bookingJobSchema.nullable().optional(),
});
export type ValidatedBookingDetail = z.infer<typeof bookingDetailSchema>;

/**
 * `GET /bookings/{id}` returns HTTP 200 with `{"error": "..."}` for
 * not-found/access-denied — never a 404/403 status (a real, disclosed API
 * quirk, see contract-matrix.md). This union lets the parser distinguish
 * the two real shapes without relying on HTTP status for this endpoint.
 */
const bookingDetailErrorSchema = z.object({ error: z.string().min(1) });
const bookingDetailResponseSchema = z.union([bookingDetailSchema, bookingDetailErrorSchema]);

export type BookingDetailParseResult = { kind: "found"; booking: ValidatedBookingDetail } | { kind: "error"; code: string } | { kind: "invalid" };

export function parseBookingDetailResponse(payload: unknown): BookingDetailParseResult {
  const result = bookingDetailResponseSchema.safeParse(payload);
  if (!result.success) return { kind: "invalid" };
  if ("error" in result.data) return { kind: "error", code: result.data.error };
  return { kind: "found", booking: result.data };
}
