import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { assistantSessionResponseSchema, sendMessageResponseSchema, messagesListResponseSchema } from "../contracts/assistantSession";

/**
 * Canonical assistant surface only (docs/backend/ai-booking-assistant-
 * canonical.md, Sprint-15 `AIConversationService` via
 * `/v1/customer/ai-chat/*`). Deliberately does NOT call the deprecated
 * `/v1/customer/ai/*` (Sprint-29 compatibility layer) or `/v1/ai/chat`
 * (`ai_chat`, deprecated for customer booking use) -- both carry
 * `deprecated=True` in source per the decision record.
 */
export interface CreateAssistantSessionInput {
  categoryId?: string;
  zipcode?: string;
}

export async function createAssistantSession(input: CreateAssistantSessionInput) {
  const res = await authenticatedRequest({
    method: "POST",
    path: "/v1/customer/ai-chat/sessions",
    body: {
      category_id: input.categoryId,
      context: input.zipcode ? { zipcode: input.zipcode } : {},
    },
  });
  return parseApiSuccess(res.json, assistantSessionResponseSchema);
}

export async function getAssistantSession(sessionId: string) {
  const res = await authenticatedRequest({ method: "GET", path: `/v1/customer/ai-chat/sessions/${sessionId}` });
  return parseApiSuccess(res.json, assistantSessionResponseSchema);
}

export async function setAssistantSessionLanguage(sessionId: string, language: string) {
  const res = await authenticatedRequest({
    method: "PUT", path: `/v1/customer/ai-chat/sessions/${sessionId}/language`, body: { language },
  });
  return parseApiSuccess(res.json, assistantSessionResponseSchema);
}

export async function sendAssistantMessage(sessionId: string, message: string, signal?: AbortSignal) {
  const res = await authenticatedRequest({
    method: "POST", path: `/v1/customer/ai-chat/sessions/${sessionId}/messages`, body: { message }, signal,
  });
  return parseApiSuccess(res.json, sendMessageResponseSchema);
}

export async function getAssistantMessages(sessionId: string, page: number = 1) {
  const res = await authenticatedRequest({
    method: "GET", path: `/v1/customer/ai-chat/sessions/${sessionId}/messages?page=${page}`,
  });
  return parseApiSuccess(res.json, messagesListResponseSchema);
}
