# Deferred Items — UX-06 (updated after Round 2)

Following UX-05's disposition vocabulary (KEEP_AND_REDESIGN / API_CONTRACT_REQUIRED /
MOCK_DESIGN_ONLY / NOT_APPLICABLE):

| Item | Disposition | Reasoning |
|---|---|---|
| ~~HomeScreen/JobTrackingScreen/ServiceHistoryScreen rewiring~~ | **DONE (Round 2)** | Rewired to real `fieldOpsJobsApi` |
| ~~PaymentMethodsScreen~~ | **DONE (Round 2)** | Honest unavailable state, real contract confirmed absent |
| ~~HelpSupportScreen~~ | **DONE (Round 2)** | Real contact card kept, fake FAQ/ticket UI → "coming soon" |
| ~~SettingsScreen~~ | **DONE (Round 2)** | App-wide language selector REMOVED (hard rule violation); notif prefs → "coming soon" |
| ~~DeepSeek contract confirmation~~ | **DONE (Round 2)** | Live-confirmed via source read + curl; see deepseek-conversation-contract.md |
| DeepSeek chat UI navigation wiring | KEEP_AND_REDESIGN | `DeepSeekChatScreen.tsx` built and typechecks clean, not yet added to `AppNavigator`/`TabNavigator` — deliberately deferred to avoid touching those already-broken files this round |
| Consolidate 4 overlapping AI/chat screens | KEEP_AND_REDESIGN | `AIChatScreen`/`AIAssistantScreen`/`SmartBotScreen`/`ChatScreen` should collapse into `DeepSeekChatScreen` (AI) + the real customer-chat-threads screen (human) |
| Fix remaining 126 typecheck errors | KEEP_AND_REDESIGN | All in screens not yet touched (`BookingDetailScreen`, `QuoteApprovalScreen`, `InvoiceScreen`, `ProfileScreen`, `ChatScreen`, `BookServiceScreen`, `AppNavigator`, `TabNavigator`, `BookingCard`, `AIAssistantScreen`, `AIChatScreen`, `SmartBotScreen`, `AddressBookScreen`, `NotificationsScreen`, `BookingsListScreen`, `ReviewScreen`) — see known-limitations.md #1 for the per-file breakdown |
| Typed pipeline-aware view-model/adapter layer | KEEP_AND_REDESIGN | High-value, cheap once remaining screens are stable; not started |
| Customer IA/navigation restructure (5-tab decision) | KEEP_AND_REDESIGN | Audited this round (see customer-information-architecture.md) — decision on final tab set not yet made/implemented |
| Booking submission workflow | Not started | Depends on catalog + pipeline view-model work above |
| Light/dark theme, accessibility pass | Not evaluated | `src/styles/theme.ts` exists in the scaffold, not audited |
| Component/screen-level RNTL tests | Not started | Only lib/context-level tests exist so far (9 tests) |
| Live Playwright login→home→chat→bookings proof | Not started | Backend confirmed live and reachable; not attempted this round |
| Showcase screen inventory | Not started | No showcase screens exist yet in this app |
| Switch AI chat to Sprint 29 engine (`/v1/customer/ai/sessions`) | Not started | Requires real seeded customer credentials to test its stricter auth; one-line change once available |
| Confirm DeepSeek reply-language compliance live | Not started | Blocked on a real (non-placeholder) `DEEPSEEK_API_KEY` in a test environment |
