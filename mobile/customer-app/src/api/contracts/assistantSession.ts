/**
 * DTO for the canonical assistant surface (`AIConversationSession`/
 * `AIConversationMessage`, app/engines/ai_conversation/{models,
 * customer_router}.py, per the canonical decision record
 * docs/backend/ai-booking-assistant-canonical.md -- Sprint-15
 * `/v1/customer/ai-chat/*`, never the deprecated `/v1/customer/ai/*` or
 * `/v1/ai/chat`).
 */
import { z } from "zod";

export const languageOptionDtoSchema = z.object({
  code: z.string(),
  label: z.string(),
});
export type LanguageOptionDto = z.infer<typeof languageOptionDtoSchema>;

export const assistantSessionResponseSchema = z.object({
  id: z.string(),
  session_key: z.string(),
  customer_id: z.string().nullable(),
  category_id: z.string().nullable(),
  language: z.string(),
  current_intent: z.string(),
  workflow_status: z.string(),
  collected_fields: z.record(z.string(), z.unknown()),
  context_data: z.record(z.string(), z.unknown()),
  turn_count: z.number(),
  last_activity_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  is_active: z.boolean(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  // Booking-Assistant Foundation (2026-08-01) addition -- see
  // app/engines/ai_conversation/regional_language.py.
  language_options: z.array(languageOptionDtoSchema).optional(),
});
export type AssistantSessionResponseDto = z.infer<typeof assistantSessionResponseSchema>;

export const assistantMessageResponseSchema = z.object({
  id: z.string(),
  session_id: z.string(),
  role: z.string(),
  content: z.string(),
  intent_at_time: z.string().nullable().optional(),
  tool_calls_made: z.array(z.string()).optional(),
  created_at: z.string().nullable(),
});
export type AssistantMessageResponseDto = z.infer<typeof assistantMessageResponseSchema>;

export const quickReplyDtoSchema = z.object({
  label: z.string(),
  value: z.string(),
});

/** POST .../messages response: {"reply", "tools_called", "session", "intent"}
 * -- confirmed in AIConversationService.send_message docstring/return.
 * `quick_replies` (added alongside the offering-choice tap-select fix):
 * real backend-sourced tap options for THIS reply, e.g. choosing between
 * "AC Installation" and "AC Service" before a draft exists -- null/absent
 * whenever there's nothing to tap, never fabricated client-side. */
export const sendMessageResponseSchema = z.object({
  reply: z.string(),
  tools_called: z.array(z.string()),
  session: assistantSessionResponseSchema,
  intent: z.string(),
  quick_replies: z.array(quickReplyDtoSchema).nullable().optional(),
});
export type SendMessageResponseDto = z.infer<typeof sendMessageResponseSchema>;

export const messagesListResponseSchema = z.object({
  messages: z.array(assistantMessageResponseSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
});
