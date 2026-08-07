/**
 * DTOs for the Service Match/Review/Confirmation surface -- all routes
 * confirmed by direct read of
 * `app/engines/home_service_booking/{customer_router,service}.py` and
 * `app/engines/final_records/creation_service.py` this task.
 */
import { z } from "zod";

export const serviceabilityCheckResponseSchema = z.object({
  serviceable: z.boolean(),
  reason_code: z.string().nullable().optional(),
  message: z.string(),
  draft_status: z.string(),
}).passthrough();

/** `price_snapshot` accumulates keys from TWO backend calls that both
 * spread onto the same JSONB column (`resolve_price_estimate` then
 * `match_provider_and_price`) -- passthrough is deliberate; only the
 * fields this phase actually renders are named. */
export const priceSnapshotDtoSchema = z.object({
  requires_inspection_estimate: z.boolean().optional(),
  visit_fee: z.number().nullable().optional(),
  customer_message: z.string().nullable().optional(),
  pricing_model: z.string().nullable().optional(),
  bargain_available: z.boolean().optional(),
  standard_price: z.number().nullable().optional(),
}).passthrough();

/** Real bug fixed here: `POST /price-estimate` returns an ENVELOPE
 * `{ price_snapshot, draft_status }` -- not the snapshot itself. The API
 * client parsed the response directly as `priceSnapshotDtoSchema`, which
 * (being `.passthrough()`) silently succeeded while leaving every real
 * price field (`visit_fee`, `requires_inspection_estimate`, ...)
 * undefined, so the customer app could never show a resolved price. */
export const priceEstimateResponseSchema = z.object({
  price_snapshot: priceSnapshotDtoSchema.nullable(),
  draft_status: z.string().optional(),
}).passthrough();

export const reviewProviderDtoSchema = z.object({
  tenant_id: z.string(),
  provider_name: z.string(),
  // Real bug fixed here: the backend sends trust badges as OBJECTS
  // ({icon, name, color} -- see matching_engine.build_customer_safe_provider),
  // but this declared `z.array(z.string())`. Parsing the booking summary
  // therefore THREW on every real provider, so Booking Review could never
  // load and fell back to a blocked/error screen.
  public_badges: z.array(z.object({
    name: z.string(),
    icon: z.string().nullable().optional(),
    color: z.string().nullable().optional(),
  }).passthrough()).default([]),
  rating: z.number().nullable().optional(),
  customer_visible_reason: z.string().optional(),
}).passthrough();

export const matchAndPriceResponseSchema = z.object({
  selected_provider: reviewProviderDtoSchema,
  bargain_available: z.boolean(),
  selected_provider_price_options: z.record(z.string(), z.unknown()).nullable(),
  standard_price: z.number().nullable(),
  area_market_comparison: z.unknown().optional(),
  draft_status: z.string().optional(),
}).passthrough();

export const confirmPriceChoiceResponseSchema = z.object({
  booking_summary: z.record(z.string(), z.unknown()),
  draft_status: z.string(),
}).passthrough();

/** The real, capacity-checked slot the provider can honour, resolved
 * BEFORE the customer confirms so they decide on a promise rather than
 * confirming blind. Null when the provider has no capacity in the search
 * horizon -- the customer is told that, never given a fabricated date. */
export const promisedSlotDtoSchema = z.object({
  date: z.string(),
  time_window: z.string(),
  starts_at: z.string(),
  ends_at: z.string(),
  slot_minutes: z.number(),
  capacity: z.number(),
  already_booked: z.number(),
  days_ahead: z.number(),
}).passthrough();

export const bookingSummaryDtoSchema = z.object({
  promised_slot: promisedSlotDtoSchema.nullable().optional(),
  service_sla_minutes: z.number().nullable().optional(),
  service_due_at: z.string().nullable().optional(),
  offering_name: z.string(),
  offering_slug: z.string().optional(),
  issue_summary: z.string().nullable(),
  address: z.record(z.string(), z.unknown()).nullable(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  preferred_date: z.string().nullable(),
  preferred_time_window: z.string().nullable().optional(),
  price_estimate: priceSnapshotDtoSchema.nullable(),
  selected_provider: reviewProviderDtoSchema.nullable(),
  serviceability: z.object({ serviceable: z.boolean(), status: z.string().nullable() }),
  ready_for_confirmation: z.boolean(),
  missing: z.array(z.string()).default([]),
  errors: z.array(z.unknown()).default([]),
  selected_price_tier: z.string().nullable().optional(),
}).passthrough();

export const buildBookingSummaryResponseSchema = z.object({
  booking_summary: bookingSummaryDtoSchema,
  draft_status: z.string(),
}).passthrough();

/** GET /{draft_id}/available-slots. `capacity`/`already_booked` are
 * omitted here (unlike `promisedSlotDtoSchema`) because
 * `select_promised_slot` doesn't recompute them when overwriting the
 * summary -- they were only ever informational, never read by the UI. */
export const availableSlotsResponseSchema = z.object({
  slots: z.array(z.object({
    date: z.string(),
    time_window: z.string(),
    starts_at: z.string().nullable().optional(),
    ends_at: z.string().nullable().optional(),
    slot_minutes: z.number().nullable().optional(),
    days_ahead: z.number(),
  })),
}).passthrough();

export const selectSlotResponseSchema = z.object({
  booking_summary: bookingSummaryDtoSchema,
  draft_status: z.string(),
}).passthrough();

export const markReadyResponseSchema = z.object({
  draft_status: z.string(),
  ready_for_confirmation: z.boolean(),
}).passthrough();

export const confirmDraftResponseSchema = z.object({
  booking_number: z.string(),
  booking_id: z.string(),
  idempotent: z.boolean().optional().default(false),
}).passthrough();
export type ConfirmDraftResponseDto = z.infer<typeof confirmDraftResponseSchema>;
