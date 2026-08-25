/**
 * DTO for the Home Service booking draft, confirmed against
 * `HomeServiceBookingDraft.to_dict()` + `_enrich_draft()`
 * (app/engines/home_service_booking/{models,service}.py, read directly
 * this task). Only fields this app's Assistant foundation actually
 * consumes are strictly typed; everything else passes through
 * unvalidated (`.passthrough()`) rather than being silently stripped --
 * a later phase reading a field this one doesn't need yet still gets it.
 */
import { z } from "zod";

export const bookingDraftResponseSchema = z.object({
  id: z.string(),
  customer_id: z.string().nullable(),
  ai_session_id: z.string().nullable(),
  category_id: z.string(),
  offering_id: z.string(),
  job_type_id: z.string().nullable(),
  status: z.string(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  issue_summary: z.string().nullable(),
  // Drafts created before these checks run carry real SQL NULL values.
  // Requiring strings here made a healthy assistant-bootstrap response fail
  // parsing whenever the backend included such a resumable draft, even though
  // the current product decision deliberately starts a new request.
  serviceability_status: z.string().nullable(),
  price_status: z.string().nullable(),
  provider_match_status: z.string().nullable(),
  price_snapshot: z.record(z.string(), z.unknown()).nullable(),
  expires_at: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  // Enriched fields (only present once the offering/category/job-type
  // rows resolve -- see `_enrich_draft`).
  offering_name: z.string().optional(),
  offering_slug: z.string().optional(),
  category_name: z.string().optional(),
  category_slug: z.string().optional(),
  job_type_key: z.string().optional(),
  job_type_label: z.string().optional(),
  photo_urls: z.array(z.string()).optional(),
}).passthrough();
export type BookingDraftResponseDto = z.infer<typeof bookingDraftResponseSchema>;

/** `GET .../by-session/{ai_session_id}` returns the draft dict OR `null`
 * (no draft yet) -- confirmed in source
 * (`HomeServiceChatbotBookingService.get_draft_by_ai_session`). */
export const bookingDraftOrNullSchema = bookingDraftResponseSchema.nullable();
