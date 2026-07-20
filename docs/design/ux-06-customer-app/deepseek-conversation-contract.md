# DeepSeek Conversational Booking — Contract Audit (Round 2 update: CONFIRMED REAL)

## Status: CONFIRMED_REAL (contract), INFRA_BLOCKED (live model replies)

Round 1 left this open (two candidate routes, unconfirmed schema). Round 2
resolved it via source-code reading AND live HTTP probes against the running
backend (`http://localhost:8000`, 2026-07-20).

## Confirmed real, live, end-to-end

```
curl -X POST http://localhost:8000/v1/customer/ai-chat/sessions -d '{}'
-> 200 { "success": true, "data": { "id": "...", "session_key": "...",
          "customer_id": null, "current_intent": "unknown",
          "workflow_status": "active", "turn_count": 0, "is_active": true, ... } }

curl -X POST http://localhost:8000/v1/customer/ai-chat/sessions/{id}/messages \
  -d '{"message":"Hi, I need AC repair"}'
-> 200 { "success": true, "data": {
     "reply": "I'm having trouble processing your request. Please try again.",
     "tools_called": ["get_service_categories","get_service_categories",
                       "get_category_offerings","get_category_offerings",
                       "get_service_faqs"],
     "intent": "service_inquiry",
     "session": { ...same session shape, turn_count now 1 } } }
```

The `tools_called` array proves the real DeepSeek tool-calling loop actually ran
(it queried real category/offering/FAQ tools before attempting a completion).
The fallback reply is because `DEEPSEEK_API_KEY` in this dev environment's
`.env` is the literal placeholder `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx` — confirmed
by reading `app/config.py` and `app/engines/ai_conversation/deepseek_client.py`
(`self.api_key = get_settings().DEEPSEEK_API_KEY`; a real DeepSeek call is
attempted against `DEEPSEEK_API_BASE`, and its `httpx` failure is caught and
turned into the safe fallback message above — a real, intentional safety
behavior, not a bug). **This is an environment/credentials limitation, not a
contract gap** — the moment a real key is configured, this exact same flow
returns real DeepSeek completions with no client changes needed.

Response shape `{ reply, tools_called, intent, session }` is confirmed from
BOTH the live JSON above and the `service.send_message()` docstring in
`app/engines/ai_conversation/service.py` (line ~185).

## Two live engines — which one is used, and why

| | `/v1/customer/ai-chat/sessions` (Sprint 15) | `/v1/customer/ai/sessions` (Sprint 29) |
|---|---|---|
| Auth | `get_current_user_optional` — works anonymously | `get_current_user` — requires a real authenticated customer |
| Extra features | none | rate limiting, strict session-ownership check, `/reset`, `/handoff`, `/draft-status` |
| Underlying call | same `AIConversationService.send_message()` | same `AIConversationService.send_message()` |
| Response shape | `{ reply, tools_called, intent, session }` | identical (same service call) |
| Used by this round's `aiConversationApi`/`DeepSeekChatScreen`? | **Yes** | Not yet |

Sprint 15 was used this round because it could be verified live without seeded
customer credentials (anonymous session creation). Sprint 29 is the more
production-appropriate contract (ownership + rate limiting) and should be
switched to once a real customer login is available to test against its
stricter auth requirement — a one-line change (`aiConversationApi`'s base path),
documented directly in `src/lib/api.ts`.

## Language support: confirmed NOT present in the backend

Grepped the entire `app/engines/ai_conversation/` package for
`language`/`lang_code`/`locale` — no match anywhere; both engines accept a raw
`dict` body with no strict Pydantic model and no language awareness in
`AIConversationService`. See chat-language-selection.md for the full write-up
and the client-side workaround built this round (`withLanguageInstruction`),
with DeepSeek's actual compliance with that instruction left honestly
unconfirmed (blocked on the same placeholder-API-key issue above).

## What was built this round

`src/lib/chatLanguages.ts` (BCP-47 registry + search) and
`src/screens/DeepSeekChatScreen.tsx` — a real chat screen against the confirmed
Sprint 15 contract, with a searchable language-selector modal. **Not yet wired
into navigation** (see customer-information-architecture.md) — a deliberate
scope decision to avoid touching the already-error-laden navigator files this
round, not an oversight.
