/**
 * DTO for `GET /v1/customer/my-activity/bookings/{booking_id}` (confirmed
 * via direct read of `app/engines/final_records/customer_router.py` +
 * `ServiceBooking.to_dict()`). SECURITY (2026-08-01): not-found and
 * cross-customer access both now return an IDENTICAL real HTTP 404
 * (`error_code: "BOOKING_NOT_FOUND"`) -- the prior HTTP-200-with-an-
 * `{"error": ...}` -payload contract (and its two distinct error codes)
 * was a booking-existence oracle and has been removed. A 2xx response
 * from this endpoint is always a real, owned booking.
 */
import { z } from "zod";

/** Customer-safe technician projection (ACTIVE-BOOKING-DETAILS phase) --
 * resolved server-side from `ProviderTeamMember`, never the raw
 * `assigned_staff_id`/user id. Absent fields are `null`, never fabricated. */
export const jobTechnicianDtoSchema = z.object({
  display_name: z.string(),
  designation: z.string().nullable(),
  photo_url: z.string().nullable(),
});

/** `job` on the booking-detail DTO (ACTIVE-BOOKING-DETAILS phase, confirmed
 * via `_customer_safe_job` in `customer_router.py`) -- an allow-listed
 * projection, never `ServiceJob.to_dict()`. `stage`/`stage_label` come from
 * the same canonical `map_job_status` the tenant Bookings & Jobs workspace
 * uses, so the customer app never re-derives its own status→stage mapping. */
export const serviceJobDtoSchema = z.object({
  id: z.string(),
  status: z.string(),
  assignment_status: z.string(),
  stage: z.string(),
  stage_label: z.string(),
  is_terminal: z.boolean(),
  scheduled_date: z.string().nullable(),
  scheduled_time_window: z.string().nullable(),
  technician: jobTechnicianDtoSchema.nullable(),
  updated_at: z.string().nullable(),
  completion: z.object({
    work_summary: z.string().nullable(),
    collected_amount: z.number().nullable(),
    completed_at: z.string().nullable(),
  }).nullable(),
}).passthrough();
export type ServiceJobDto = z.infer<typeof serviceJobDtoSchema>;

/** Versioned, immutable answer snapshot (migration 222,
 * `QuestionFlowService.build_answer_snapshot`) -- resolved ONCE at
 * finalize() time from the live catalog, so a later question/option
 * relabel can never change what a historical booking shows. Deliberately
 * NOT stored in `issue_details` (see that field's comment below). */
export const answerSnapshotEntryDtoSchema = z.object({
  question_id: z.string(),
  question_key: z.string(),
  question_label: z.string(),
  question_type: z.string(),
  answer_code: z.unknown(),
  answer_label: z.string(),
  sequence: z.number(),
});

export const answerSnapshotDtoSchema = z.object({
  schema_version: z.number(),
  answers: z.array(answerSnapshotEntryDtoSchema),
});
export type AnswerSnapshotDto = z.infer<typeof answerSnapshotDtoSchema>;

export const serviceBookingDtoSchema = z.object({
  id: z.string(),
  booking_number: z.string(),
  draft_id: z.string(),
  customer_id: z.string().nullable(),
  tenant_id: z.string().nullable(),
  category_id: z.string(),
  offering_id: z.string(),
  job_type_id: z.string().nullable(),
  customer_name: z.string().nullable(),
  customer_phone: z.string().nullable(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  address_snapshot: z.record(z.string(), z.unknown()).nullable(),
  preferred_date: z.string().nullable(),
  preferred_time_window: z.string().nullable(),
  /**
   * The COMMITTED slot and how urgent it is, both computed server-side.
   *
   * `urgency` is the server's own answer -- "late" | "today" | "upcoming" |
   * "unscheduled", or null for finished work. The app does not re-derive it: the
   * customer's list and the provider's dashboard must agree about which jobs are late,
   * and two sides each reading a date string is exactly how they stop agreeing.
   *
   * Optional so an older backend simply yields no grouping rather than failing to parse.
   */
  scheduled_date: z.string().nullable().optional(),
  scheduled_time_window: z.string().nullable().optional(),
  urgency: z.enum(["late", "today", "upcoming", "unscheduled"]).nullable().optional(),
  minutes_late: z.number().nullable().optional(),
  /** Pre-worded by the server ("2 days late") so the phrasing is identical everywhere. */
  lateness_label: z.string().nullable().optional(),
  price_snapshot: z.record(z.string(), z.unknown()).nullable(),
  // Deliberately NOT typed/consumed beyond existence -- the staff-
  // dependent safety boundary (spec section 5) means provider_snapshot's
  // contents must never reach this receipt's UI even if present.
  provider_snapshot: z.record(z.string(), z.unknown()).nullable().optional(),
  issue_summary: z.string().nullable(),
  // Deliberately NOT the answers source -- `execution/
  // mobile_inspection_service.py` reads this column expecting an
  // unrelated inspection-report shape (`{"answers": [...], "notes": ...}`
  // from a technician's on-site inspection, NOT the customer's booking
  // question-flow answers). Kept typed/passed-through only for schema
  // completeness; never read for the Service Overview card.
  issue_details: z.record(z.string(), z.unknown()).nullable(),
  answer_snapshot: answerSnapshotDtoSchema.nullable().optional(),
  status: z.string(),
  assignment_status: z.string(),
  failure_reason: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  job: serviceJobDtoSchema.nullable().optional(),
  // Enriched server-side by get_my_booking (BOOKING-CONFIRMATION-RECEIPT,
  // 2026-08-01) -- absent only if the underlying catalog row was deleted.
  offering_name: z.string().optional(),
  category_name: z.string().optional(),
  job_type_label: z.string().optional(),
}).passthrough();

export type ServiceBookingDto = z.infer<typeof serviceBookingDtoSchema>;

/**
 * `GET /v1/customer/my-activity/bookings?bucket=active|completed|all` --
 * offset pagination, deterministic `(created_at DESC, id DESC)` ordering,
 * server-side bucket filtering (CLOSURE 2026-08-01: `bucket` now filters
 * at the query level -- `active` excludes `completed`/`cancelled`,
 * `completed` matches only the real `completed` status). `counts` is
 * ALWAYS the authoritative total for all three buckets regardless of
 * which bucket was requested -- the client must never compute a tab
 * count from a partial/paginated fetch. Still no cursor, no server-side
 * text search (confirmed via direct source read) -- search/advanced
 * filters remain absent from the UI rather than faked.
 */
export const bookingListCountsDtoSchema = z.object({
  active: z.number(),
  completed: z.number(),
  all: z.number(),
});
export type BookingListCountsDto = z.infer<typeof bookingListCountsDtoSchema>;

export const bookingListResponseSchema = z.object({
  items: z.array(serviceBookingDtoSchema),
  total: z.number(),
  counts: bookingListCountsDtoSchema,
  limit: z.number(),
  offset: z.number(),
});
export type BookingListResponseDto = z.infer<typeof bookingListResponseSchema>;
