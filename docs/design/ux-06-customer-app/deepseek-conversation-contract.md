# DeepSeek Conversational Booking — Contract Audit

## Backend reality (verified against live openapi.json + `app/engines/ai_conversation/`, `app/engines/ai_chat/`)

Two distinct AI-chat engines exist in the backend:

1. **`app/engines/ai_conversation/`** — session-based, persistent, customer-scoped.
   Real routes (confirmed in `openapi.json`):
   - `POST /v1/customer/ai-chat/sessions` — create a session (optional `category_id`)
   - `POST /v1/customer/ai-chat/sessions/{session_id}/messages` — send a message
   - `GET /v1/customer/ai-chat/sessions/{session_id}/messages` — history
   - `POST /v1/customer/ai-chat/sessions/{session_id}/close` — end session
   - `deepseek_client.py` in this engine strongly suggests this is the real
     DeepSeek-backed proxy (backend holds the key, never the app).
   - There is a **second**, separate customer AI surface at `/v1/customer/ai/sessions*`
     (note: `ai/sessions`, not `ai-chat/sessions`) with additional draft/handoff/reset
     routes — this looks like a newer or parallel booking-draft-oriented engine. Both
     exist live; this round did not have time to determine which one is the intended
     production path for UX-06's DeepSeek chat vs. which is legacy/parallel. **This is
     an open question, not resolved this round** (see known-limitations.md).

2. **`app/engines/ai_chat/`** — a simpler, non-session `POST /v1/ai/chat` +
   `GET /v1/ai/chat/meta`. Referenced in repo memory as the target of MODULE-L5-48
   (fixed two broken AI tools with nonexistent model imports), confirming this engine
   is live and has been debugged before. Not session-based, so it cannot carry
   per-conversation language metadata or booking-draft state across turns the way
   the UX-06 brief requires — **not used** as the chat contract for this reason.

## Decision made this round

`aiConversationApi` in `src/lib/api.ts` targets `/v1/customer/ai-chat/sessions*`
(the session-based engine) because it is the only one of the two session-based
options this round had time to confirm end-to-end route shapes for, and it is the
only shape that supports the persistent, resumable, language-taggable conversation
the brief requires. The client-side request bodies now include `language_code` /
`language_name` fields on session-create and send-message (see
chat-language-selection.md) — **these fields are speculative**, added because the
brief requires a language-aware contract, but their presence/effect was not
confirmed against the actual `ai_conversation` service/schema code this round (only
the route paths and top-level request/response shape were checked via openapi.json,
not the full Pydantic request model). This must be verified against
`app/engines/ai_conversation/service.py` / the actual `SessionCreateRequest` /
`MessageRequest` schemas before the chat UI is built against it for real — flagged
in deferred-items.md.

## No frontend chat UI was built this round

Given the contract ambiguity above (two live session engines, unconfirmed request
schema for language fields), no chat screen/state-machine work was done this round
beyond fixing the existing `aiConversationApi` client to point at real paths. Per
the brief's honesty requirement, no MOCK_DESIGN_ONLY chat screen is claimed as
DeepSeek-integrated; the existing `AIChatScreen.tsx` / `AIAssistantScreen.tsx` /
`SmartBotScreen.tsx` / `ChatScreen.tsx` files (four overlapping legacy chat-shaped
screens already in the scaffold) were not touched this round and should be
consolidated into a single real chat surface in the next round once the schema
question above is resolved.
