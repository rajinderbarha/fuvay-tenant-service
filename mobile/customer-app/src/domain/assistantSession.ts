import { ChatbotLanguageOption } from "./chatbotLanguage";
import { ServerTimestamp } from "./dates";

export interface QuickReply {
  label: string;
  value: string;
}

export interface AssistantMessage {
  id: string;
  role: string;
  content: string;
  createdAt: ServerTimestamp | null;
  /** Real backend-sourced tap options attached to THIS assistant message
   * (e.g. choosing between offerings before a draft exists) -- only ever
   * present on an assistant message, never fabricated client-side. */
  quickReplies?: QuickReply[];
  /** Marks a purely client-side, temporary transcript entry (the inline
   * "assistant is responding" typing indicator, or an optimistic echo of
   * the customer's own tap-answer before the round-trip confirms it) --
   * never sent to or received from the backend, never persisted, always
   * replaced/removed once the real response arrives. */
  isTyping?: boolean;
}

export interface AssistantSession {
  id: string;
  sessionKey: string;
  categoryId: string | null;
  language: string;
  languageOptions: ChatbotLanguageOption[];
  turnCount: number;
  isActive: boolean;
  workflowStatus: string;
}

export interface SendMessageResult {
  reply: string;
  session: AssistantSession;
  intent: string;
  quickReplies: QuickReply[] | null;
}

/** One chatbot-conversation language the BACKEND offers for this ZIP
 * (`build_language_options`). Lives in the domain layer, not in the
 * controller: a component that renders language options must not import
 * from the screen controller, which imports that component back -- a real
 * circular import that resolved to `undefined` at runtime and crashed the
 * Assistant with a render error. */
export interface AssistantLanguageOption {
  code: string;
  label: string;
}
