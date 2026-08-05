/**
 * Chatbot-only language selection (never app-wide). Options ALWAYS come
 * from the backend (`language_options` on the session response, see
 * app/engines/ai_conversation/regional_language.py) -- this module never
 * hardcodes a ZIP-to-language mapping; it only carries the backend's own
 * answer through to the UI.
 */
export interface ChatbotLanguageOption {
  code: string;
  label: string;
}

export const DEFAULT_CHATBOT_LANGUAGE = "en";
