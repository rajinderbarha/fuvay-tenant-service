# Customer IA / Navigation Audit — UX-06 Round 2

## Current structure (as found, `src/navigation/`)

`AppNavigator.tsx` is a native-stack root: shows `LoginScreen` when logged out;
when logged in, shows a `Tabs` root (`TabNavigator`) plus a flat stack of
detail/flow screens layered on top (BookService, BookingDetail, JobTracking,
SmartBot, AIAssistant, QuoteApproval, Review, Invoice, Settings, Notifications,
AddressBook, ServiceHistory, HelpSupport, PaymentMethods).

`TabNavigator.tsx` currently has **5 tabs**: Home, Bookings (`BookingsListScreen`),
AI Assistant (`AIChatScreen`), Chat (`ChatScreen`), Profile (`ProfileScreen`).

## Comparison against the UX-06 target IA (Home/Bookings/Chat/Notifications/Account, max 5 tabs)

The existing 5-tab structure is close to the target but not identical:

| Existing tab | Target tab | Gap |
|---|---|---|
| Home | Home | Match |
| Bookings | Bookings | Match |
| AI Assistant (`AIChatScreen`) | — | Overlaps with the "Chat" concept; the brief's target IA names Chat as the DeepSeek entry point, not a 4th tab alongside it |
| Chat (`ChatScreen`) | Chat | This is likely the customer↔provider/staff messaging thread list (now correctly wired to `/v1/customer/chat/threads` this round), distinct from the AI assistant |
| Profile (`ProfileScreen`) | Account | Naming only |
| — | Notifications | **Missing as a tab** — `NotificationsScreen` exists but is only reachable via stack push, not a tab |

**This round's assessment**: the existing app conflates "AI Assistant" and "Chat"
as two separate tabs, when the target IA implies one "Chat" tab should likely be
the DeepSeek entry point (this round's `DeepSeekChatScreen.tsx`, not yet wired to
navigation — see deepseek-conversation-contract.md), with customer↔provider
messaging reachable from within a booking/job detail context instead of its own
top-level tab. Alternatively, Notifications could take the 5th tab slot instead
of a separate Chat tab, with the AI Assistant absorbing both AI + human handoff
(the real backend does support a handoff endpoint —
`POST /v1/customer/ai/sessions/{id}/handoff` in the Sprint 29 engine).

## Decision NOT made this round

Given the risk of breaking the already-fragile `AppNavigator`/`TabNavigator`
(which alone account for 12 of the 126 outstanding typecheck errors) under this
round's time constraints, **no navigation restructuring was done this round**.
`DeepSeekChatScreen.tsx` was built and typechecks cleanly in isolation but is
intentionally not yet wired into either navigator. This is a deliberate,
documented deferral (see deferred-items.md), not an oversight.

## Recommendation for the next round

1. Fix `AppNavigator.tsx`/`TabNavigator.tsx`'s own typecheck errors first (they're
   part of the 126, not caused by this round's api.ts changes — likely stale
   `as never` navigation param casts).
2. Land on a final 5-tab decision: Home / Bookings / Chat (DeepSeek entry,
   `DeepSeekChatScreen`) / Notifications / Account. Move customer↔provider
   messaging (`ChatScreen`, now wired to the real `/v1/customer/chat/threads`)
   to be reachable from a booking/job detail screen instead of its own tab,
   consistent with it being conversation-per-job rather than a standalone inbox.
3. Consolidate the four overlapping AI-chat-shaped screens
   (`AIChatScreen`/`AIAssistantScreen`/`SmartBotScreen`/`ChatScreen`) into
   `DeepSeekChatScreen` + the real customer-chat-threads screen, removing the
   redundant ones.
