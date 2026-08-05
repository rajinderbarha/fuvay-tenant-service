import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { bookingDraftResponseSchema, bookingDraftOrNullSchema } from "../contracts/bookingDraft";

const BASE = "/v1/customer/home-services/booking-drafts";

export interface StartBookingDraftInput {
  categorySlug: string;
  offeringSlug: string;
  aiSessionId?: string;
}

/** Idempotent server-side when `aiSessionId` is supplied (confirmed in
 * source: a non-terminal draft already linked to that session is
 * returned instead of a new one being created -- see
 * HomeServiceChatbotBookingService.start_booking_draft). */
export async function startBookingDraft(input: StartBookingDraftInput) {
  const res = await authenticatedRequest({
    method: "POST",
    path: BASE,
    body: { category_slug: input.categorySlug, offering_slug: input.offeringSlug, ai_session_id: input.aiSessionId },
  });
  return parseApiSuccess(res.json, bookingDraftResponseSchema);
}

export async function getBookingDraft(draftId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/${draftId}` });
  return parseApiSuccess(res.json, bookingDraftResponseSchema);
}

/** Resolves the non-terminal draft (if any) already linked to an AI
 * session -- how the app discovers a draft DeepSeek's tool call created
 * mid-conversation, and how it resumes across app restarts. */
export async function getBookingDraftByAiSession(aiSessionId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/by-session/${aiSessionId}` });
  return parseApiSuccess(res.json, bookingDraftOrNullSchema);
}
