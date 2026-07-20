/**
 * BCP-47 language registry for the DeepSeek conversational booking chat ONLY.
 *
 * Per the UX-06 hard language-architecture rule: this registry and its selector
 * UI are scoped exclusively to the AI chat surface. It must never be imported by
 * any ordinary screen (Home, Bookings, Notifications, Account, navigation) —
 * those stay in a single base UI language permanently. See
 * docs/design/ux-06-customer-app/language-architecture-compliance.md.
 *
 * The backend ai_conversation engine has NO language field in its request schema
 * (confirmed by reading app/engines/ai_conversation/{customer_router,service}.py —
 * grepped the whole package for language/lang_code/locale, found nothing). The
 * selection made here is therefore folded into the outgoing message text via
 * withLanguageInstruction() in lib/api.ts, and kept as local, client-only
 * conversation metadata (never sent as a fake structured field).
 */
export interface ChatLanguageOption {
  code: string;         // BCP-47
  englishName: string;
  nativeName: string;
  dir: "ltr" | "rtl";
}

// A real, if non-exhaustive, multi-language registry — not limited to en/hi/pa.
export const CHAT_LANGUAGES: ChatLanguageOption[] = [
  { code:"en", englishName:"English",    nativeName:"English",     dir:"ltr" },
  { code:"hi", englishName:"Hindi",      nativeName:"हिन्दी",       dir:"ltr" },
  { code:"pa", englishName:"Punjabi",    nativeName:"ਪੰਜਾਬੀ",       dir:"ltr" },
  { code:"bn", englishName:"Bengali",    nativeName:"বাংলা",        dir:"ltr" },
  { code:"ta", englishName:"Tamil",      nativeName:"தமிழ்",        dir:"ltr" },
  { code:"te", englishName:"Telugu",     nativeName:"తెలుగు",       dir:"ltr" },
  { code:"mr", englishName:"Marathi",    nativeName:"मराठी",        dir:"ltr" },
  { code:"gu", englishName:"Gujarati",   nativeName:"ગુજરાતી",      dir:"ltr" },
  { code:"kn", englishName:"Kannada",    nativeName:"ಕನ್ನಡ",        dir:"ltr" },
  { code:"ml", englishName:"Malayalam",  nativeName:"മലയാളം",      dir:"ltr" },
  { code:"ur", englishName:"Urdu",       nativeName:"اردو",         dir:"rtl" },
  { code:"ar", englishName:"Arabic",     nativeName:"العربية",      dir:"rtl" },
  { code:"es", englishName:"Spanish",    nativeName:"Español",      dir:"ltr" },
  { code:"fr", englishName:"French",     nativeName:"Français",     dir:"ltr" },
];

export function searchChatLanguages(query: string): ChatLanguageOption[] {
  const q = query.trim().toLowerCase();
  if (!q) return CHAT_LANGUAGES;
  return CHAT_LANGUAGES.filter(l =>
    l.code.toLowerCase().includes(q) ||
    l.englishName.toLowerCase().includes(q) ||
    l.nativeName.toLowerCase().includes(q)
  );
}
