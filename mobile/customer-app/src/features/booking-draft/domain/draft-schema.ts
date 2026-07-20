import { z } from "zod";

/**
 * Mirrors app/engines/home_service_booking/models.py#HomeServiceBookingDraft.to_dict()
 * plus the enrichment fields added by service.py#_enrich_draft/start_booking_draft —
 * see CUSTOMER-L5-06-contract-matrix.md. There is no `version`/`revision`
 * field anywhere in this response — confirmed absent from the model, not
 * merely unparsed.
 */
export const DRAFT_STATUSES = [
  "draft",
  "collecting_details",
  "serviceability_checked",
  "price_estimated",
  "provider_matched",
  "ready_for_confirmation",
  "confirmed",
  "expired",
  "cancelled",
  "failed",
] as const;
export type DraftStatus = (typeof DRAFT_STATUSES)[number];

export const TERMINAL_DRAFT_STATUSES: readonly DraftStatus[] = ["confirmed", "expired", "cancelled", "failed"];

export function isTerminalDraftStatus(status: string): boolean {
  return (TERMINAL_DRAFT_STATUSES as readonly string[]).includes(status);
}

export const bookingDraftSchema = z.object({
  id: z.string().min(1),
  customer_id: z.string().nullable(),
  guest_session_id: z.string().nullable(),
  ai_session_id: z.string().nullable(),
  category_id: z.string().min(1),
  offering_id: z.string().min(1),
  selected_tenant_id: z.string().nullable(),
  status: z.string().min(1),
  customer_name: z.string().nullable(),
  customer_phone: z.string().nullable(),
  address_id: z.string().nullable(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  issue_summary: z.string().nullable(),
  offering_type_id: z.string().nullable(),
  brand_id: z.string().nullable(),
  photo_urls: z.array(z.string()),
  preferred_date: z.string().nullable(),
  preferred_time_window: z.string().nullable(),
  serviceability_status: z.string().nullable(),
  price_status: z.string().nullable(),
  provider_match_status: z.string().nullable(),
  failure_code: z.string().nullable(),
  failure_message: z.string().nullable(),
  expires_at: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  // Enrichment fields (present on create/get/update, not on cancel's short response)
  offering_name: z.string().optional(),
  offering_slug: z.string().optional(),
  category_name: z.string().optional(),
  category_slug: z.string().optional(),
  required_fields: z.array(z.string()).optional(),
});

export type ValidatedBookingDraft = z.infer<typeof bookingDraftSchema>;

export function parseBookingDraft(payload: unknown): ValidatedBookingDraft | null {
  const result = bookingDraftSchema.safeParse(payload);
  return result.success ? result.data : null;
}

export const cancelDraftResponseSchema = z.object({
  draft_status: z.string().min(1),
  message: z.string(),
});
export type ValidatedCancelResponse = z.infer<typeof cancelDraftResponseSchema>;

export function parseCancelResponse(payload: unknown): ValidatedCancelResponse | null {
  const result = cancelDraftResponseSchema.safeParse(payload);
  return result.success ? result.data : null;
}

export const linkPhotoResponseSchema = z.object({
  photo_urls: z.array(z.string()),
  draft_status: z.string().min(1),
});
export type ValidatedLinkPhotoResponse = z.infer<typeof linkPhotoResponseSchema>;

export function parseLinkPhotoResponse(payload: unknown): ValidatedLinkPhotoResponse | null {
  const result = linkPhotoResponseSchema.safeParse(payload);
  return result.success ? result.data : null;
}

/**
 * Server expiry (`expires_at`) is authoritative but only actually flips
 * `status` to `"expired"` when an async scheduler job runs
 * (`expire_old_drafts`, home_service_booking/service.py) — there is a real
 * window where `now > expires_at` but `status` is still non-terminal. This
 * client-side check lets the UI react defensively without waiting for that
 * job, while any mutation attempt still trusts the server's actual response
 * as ground truth (CUSTOMER-L5-06 §16).
 */
export function isPastExpiry(draft: ValidatedBookingDraft, nowMs: number = Date.now()): boolean {
  if (!draft.expires_at) return false;
  const expiresAtMs = new Date(draft.expires_at).getTime();
  return Number.isFinite(expiresAtMs) && nowMs >= expiresAtMs;
}
