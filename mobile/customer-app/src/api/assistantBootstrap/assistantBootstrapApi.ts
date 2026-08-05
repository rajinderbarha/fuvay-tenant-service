import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  assistantBootstrapResponseSchema, interpretOfferingSelectionResponseSchema, selectIssueResponseSchema,
} from "../contracts/assistantBootstrap";

const BASE = "/v1/customer/home-services/assistant-bootstrap";

/** Backend-first Booking Assistant entry point -- returns the real,
 * zipcode-serviceable ISSUES for a category and the customer's own
 * resumable draft, if any. Never calls DeepSeek (see
 * HomeServiceChatbotBookingService.get_assistant_bootstrap). */
export async function getAssistantBootstrap(categorySlug: string, zipcode: string | null) {
  const query = new URLSearchParams({ category_slug: categorySlug, ...(zipcode ? { zipcode } : {}) });
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}?${query.toString()}` });
  return parseApiSuccess(res.json, assistantBootstrapResponseSchema);
}

/** Constrained issue-selection interpretation -- called ONLY for the
 * customer's own free-text message before any draft exists. DeepSeek can
 * only match one of the REAL serviceable issues passed to it server-side;
 * it never creates a draft itself (see
 * OfferingInterpretationService.interpret). */
export async function interpretOfferingSelectionText(
  categorySlug: string, zipcode: string | null, text: string, sessionId?: string | null,
) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `${BASE}/interpret`,
    body: { category_slug: categorySlug, zipcode: zipcode ?? undefined, text, session_id: sessionId ?? undefined },
  });
  return parseApiSuccess(res.json, interpretOfferingSelectionResponseSchema);
}

/** Canonical issue-selection operation -- creates/resolves the real draft
 * and returns its first backend question. Supports selecting more than
 * one real problem at once (`additionalIssueIds`); the backend rejects
 * issues that don't share a workflow rather than silently merging or
 * dropping them (see HomeServiceChatbotBookingService.select_issue). */
/** `language` presents the FIRST question of the flow in the customer's
 * chosen conversation language. Real bug fixed here: without it, choosing
 * Hindi/Punjabi still produced an English first question, because this
 * endpoint returns its own envelope and was never routed through the
 * presentation service. */
export async function selectAssistantBootstrapIssue(
  categorySlug: string, zipcode: string | null, issueId: string,
  aiSessionId?: string | null, additionalIssueIds?: string[], language?: string | null,
) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `${BASE}/select-issue`,
    body: {
      category_slug: categorySlug, zipcode: zipcode ?? undefined, issue_id: issueId,
      ai_session_id: aiSessionId ?? undefined,
      additional_issue_ids: additionalIssueIds && additionalIssueIds.length > 0 ? additionalIssueIds : undefined,
      language: language ?? undefined,
    },
  });
  return parseApiSuccess(res.json, selectIssueResponseSchema);
}
