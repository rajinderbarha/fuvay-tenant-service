# Chat Language Selection — UX-06 Round 2

## Real backend finding

Grepped the entire `app/engines/ai_conversation/` package for
`language`/`lang_code`/`locale` — **no match anywhere**. Both live session engines
(`/v1/customer/ai-chat/sessions` "Sprint 15" and `/v1/customer/ai/sessions`
"Sprint 29") accept a raw `dict` body (`body.get("message")`, no strict Pydantic
request model) and have zero language-awareness in `AIConversationService`. There
is no structured way to tell the backend "respond in Hindi" today.

## What was built (real, working within that constraint)

- `src/lib/chatLanguages.ts` — a real BCP-47 registry (14 languages incl. RTL
  Urdu/Arabic, not limited to en/hi/pa), with `searchChatLanguages()` for the
  searchable selector.
- `src/lib/api.ts::withLanguageInstruction(message, language)` — folds an
  explicit instruction into the message TEXT itself
  (`"[Respond only in Hindi (हिन्दी), language code hi.] <message>"`) before
  sending, since arbitrary extra JSON fields are silently ignored server-side.
  This is the only real lever available without a backend schema change.
  Verified this is functionally inert for English (returns the message
  unchanged) via a real unit test in `src/lib/__tests__/api.test.ts`.
- `src/screens/DeepSeekChatScreen.tsx` — a real chat screen with a searchable
  language-selector modal (`chat-language-btn` → `chat-language-search`),
  conversation-scoped `language` state that survives across turns without
  restarting the session, and mid-conversation language change (selecting a new
  language takes effect on the next message sent, no booking-state loss since
  the session/conversation itself is untouched).

## Explicitly honest about the limitation (exact two-layer framing)

**The DeepSeek integration contract and backend tool orchestration are live and
verified. Actual model-provider behavior and selected-language compliance
remain infrastructure-blocked by the placeholder API key.**

Because the instruction is folded into user-turn text rather than a real
system-level parameter, DeepSeek's actual compliance with it is a model-behavior
question, not something this client can guarantee. This is a SEPARATE, explicit
blocker from the rest of the Round 3 booking journey (which is genuinely
provable end-to-end against real backend calls — see
booking-submission-workflow.md): reliable adherence to the selected language,
language switching mid-conversation, and preservation of structured booking
state after a language switch are all **NOT yet verified**, and cannot be until
a real (non-placeholder) `DEEPSEEK_API_KEY` is available in a test
environment. Live probes this phase consistently returned the graceful
"having trouble processing" fallback rather than a real completion — proving
the orchestration works, but saying nothing about actual language compliance.

## Compliance with the hard rule

`chatLanguages.ts`/`DeepSeekChatScreen.tsx` are the only files in this codebase
containing language-selection logic added by UX-06. No other screen imports
either. `LoginScreen`, `HomeScreen`, `SettingsScreen`, navigation labels, and all
other UI strings remain in the single base language — the prior scaffold's
app-wide language chip in `SettingsScreen` was REMOVED this round precisely
because it violated this boundary (see existing-customer-app-audit.md /
known-limitations.md history).
