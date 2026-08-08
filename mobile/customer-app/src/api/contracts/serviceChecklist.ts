import { z } from "zod";

/**
 * GET /v1/customer/home-services/booking-drafts/{draft_id}/service-checklist
 *
 * The REAL authored checklist points the assigned provider's technician must
 * complete -- narrowed to that provider's own selection and filtered to
 * customer-visible items, server-side. Nothing here is marketing copy: every
 * line corresponds to a checklist point that exists on the job the technician
 * receives.
 *
 * `total_points: 0` with empty sections is a legitimate state (nothing authored
 * for that service yet) and the app must render nothing rather than substitute
 * reassurance the provider is not committed to.
 */
export const serviceChecklistPointSchema = z.object({
  id: z.string(),
  label: z.string(),
  help_text: z.string().nullable().optional(),
  requires_photo: z.boolean().default(false),
}).passthrough();

export const serviceChecklistSectionSchema = z.object({
  title: z.string(),
  points: z.array(serviceChecklistPointSchema).default([]),
}).passthrough();

export const serviceChecklistResponseSchema = z.object({
  master_service_id: z.string().nullable().optional(),
  total_points: z.number(),
  photo_points: z.number().default(0),
  sections: z.array(serviceChecklistSectionSchema).default([]),
  /** True when these are the provider's own chosen points rather than the full
   * authored list -- lets the UI word it accurately instead of guessing. */
  provider_selected: z.boolean().default(false),
}).passthrough();
