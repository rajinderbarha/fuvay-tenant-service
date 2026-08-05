import {
  AssistantSessionResponseDto, AssistantMessageResponseDto, SendMessageResponseDto,
  assistantSessionResponseSchema, sendMessageResponseSchema, messagesListResponseSchema,
} from "../contracts/assistantSession";
import { AssistantSession, AssistantMessage, SendMessageResult } from "../../domain/assistantSession";
import { parseServerTimestamp } from "../../domain/dates";
import { ContractValidationError } from "../../domain/errors";

export function parseAssistantSessionDto(raw: unknown): AssistantSessionResponseDto {
  const result = assistantSessionResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("AssistantSessionResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptAssistantSession(dto: AssistantSessionResponseDto): AssistantSession {
  return {
    id: dto.id,
    sessionKey: dto.session_key,
    categoryId: dto.category_id,
    language: dto.language,
    languageOptions: dto.language_options ?? [],
    turnCount: dto.turn_count,
    isActive: dto.is_active,
    workflowStatus: dto.workflow_status,
  };
}

export function adaptAssistantMessage(dto: AssistantMessageResponseDto): AssistantMessage {
  return {
    id: dto.id,
    role: dto.role,
    content: dto.content,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
  };
}

export function parseSendMessageResponse(raw: unknown): SendMessageResponseDto {
  const result = sendMessageResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("SendMessageResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptSendMessageResult(dto: SendMessageResponseDto): SendMessageResult {
  return {
    reply: dto.reply,
    session: adaptAssistantSession(dto.session),
    intent: dto.intent,
    quickReplies: dto.quick_replies ?? null,
  };
}

export function parseMessagesListResponse(raw: unknown) {
  const result = messagesListResponseSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("MessagesListResponseDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}
