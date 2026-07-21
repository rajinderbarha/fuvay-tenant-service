# Frontend File Change Report

Exactly one frontend source file changed this round:

- `mobile/customer-app/src/lib/chatLanguages.ts` — narrowed `CHAT_LANGUAGES`
  from a 14-entry BCP-47 registry to exactly 3 entries
  (en/hi/pa = English/हिन्दी/ਪੰਜਾਬੀ), per this phase's explicit requirement.
  Grep-confirmed sole consumer: `mobile/customer-app/src/screens/DeepSeekChatScreen.tsx`.
  No other file imports this module. See `smartbot-language-verification.md`
  for the full rationale and what was NOT changed (the selector UI itself,
  the `withLanguageInstruction()` mechanism).

No other frontend file (super-admin, tenant-portal, mobile/staff-app, or
any other mobile/customer-app file) was modified this round.
