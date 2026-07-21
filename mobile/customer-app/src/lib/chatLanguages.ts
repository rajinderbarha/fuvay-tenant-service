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
 *
 * UX-07 NARROWING: per this phase's explicit requirement, the SmartBot chat
 * language selector supports EXACTLY English/हिन्दी/ਪੰਜਾਬੀ — no more. UX-06 had
 * built a broader 14-language BCP-47 registry; that exceeded this phase's
 * explicit bar (verified against docs/design/ux-06-customer-app's own
 * language-architecture-compliance.md, which documented the broader registry
 * as UX-06's own choice, not a hard requirement). Narrowed here; no other
 * screen imports this file (grep-confirmed), so this is a scoped, safe change.
 */
export interface ChatLanguageOption {
  code: string;         // BCP-47
  englishName: string;
  nativeName: string;
  dir: "ltr" | "rtl";
}

// Exactly the 3 languages required by UX-07: English/हिन्दी/ਪੰਜਾਬੀ.
export const CHAT_LANGUAGES: ChatLanguageOption[] = [
  { code:"en", englishName:"English",    nativeName:"English",     dir:"ltr" },
  { code:"hi", englishName:"Hindi",      nativeName:"हिन्दी",       dir:"ltr" },
  { code:"pa", englishName:"Punjabi",    nativeName:"ਪੰਜਾਬੀ",       dir:"ltr" },
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
