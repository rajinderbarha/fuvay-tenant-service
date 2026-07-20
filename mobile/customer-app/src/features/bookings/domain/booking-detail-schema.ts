import { z } from "zod";

/**
 * Mirrors the real response of
 * `GET /v1/customer/bookings/{bookingId}`
 * (`app/engines/home_service_assignment/customer_router.py`) — see
 * CUSTOMER-L5-12-contract-matrix.md. Note this endpoint's real error
 * shape is `{"success": false, "error": {"code", "message"}}` — a
 * distinct convention from CUSTOMER-L5-11's `final_records` endpoint
 * (`{"error": "<string>"}`). This union captures the real shape this
 * specific endpoint actually returns, not the other one.
 */
const detailAddressSnapshotSchema = z
  .object({
    address_line_1: z.string().nullable(),
    address_line_2: z.string().nullable(),
    landmark: z.string().nullable(),
    city: z.string().nullable(),
    state: z.string().nullable(),
    zipcode: z.string().nullable(),
    country: z.string().nullable(),
    name: z.string().nullable(),
    phone: z.string().nullable(),
  })
  .nullable();

const detailProviderSchema = z
  .object({
    provider_name: z.string().nullable(),
    rating: z.number().nullable(),
    public_badges: z.array(z.string()),
  })
  .nullable();

export const bookingDetailSchema = z.object({
  booking_id: z.string().min(1),
  booking_number: z.string().min(1),
  status: z.string().min(1),
  assignment_status: z.string().min(1),
  assignment_message: z.string(),
  preferred_date: z.string().nullable(),
  preferred_time_window: z.string().nullable(),
  city: z.string().nullable(),
  address: detailAddressSnapshotSchema,
  issue_summary: z.string().nullable(),
  selected_provider: detailProviderSchema,
  selected_price_option: z.string().nullable().optional(),
  selected_price_amount: z.number().nullable().optional(),
  payment_mode: z.string(),
  job_status: z.string().optional(),
  scheduled_date: z.string().nullable().optional(),
  scheduled_time_window: z.string().nullable().optional(),
});
export type ValidatedBookingDetail = z.infer<typeof bookingDetailSchema>;

const bookingDetailErrorSchema = z.object({
  success: z.literal(false),
  error: z.object({ code: z.string().min(1), message: z.string() }),
});

const bookingDetailResponseSchema = z.union([bookingDetailSchema, bookingDetailErrorSchema]);

export type BookingDetailParseResult = { kind: "found"; booking: ValidatedBookingDetail } | { kind: "error"; code: string } | { kind: "invalid" };

export function parseBookingDetail(payload: unknown): BookingDetailParseResult {
  const result = bookingDetailResponseSchema.safeParse(payload);
  if (!result.success) return { kind: "invalid" };
  if ("success" in result.data && result.data.success === false) return { kind: "error", code: result.data.error.code };
  return { kind: "found", booking: result.data as ValidatedBookingDetail };
}
