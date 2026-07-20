# Known Limitations — UX-06 Round 1

1. **No fresh WSL install/typecheck/test pass performed this round.** All backend
   contract verification was done via `openapi.json` inspection (PowerShell) against
   the live server at `http://localhost:8000`; no `npm install`/`tsc`/`jest`/Playwright
   pass was run in WSL this round. Do not assume a specific pass/fail count — none is
   claimed. This is the first item for the next round.

2. **Six existing screens are now typecheck-broken by the api.ts correction**:
   `HomeScreen.tsx`, `JobTrackingScreen.tsx`, `ServiceHistoryScreen.tsx` reference
   removed exports (`jobsApi.list/.myJobs/.get/.trackStaff`, `StaffLocation`) that
   need rewiring to the corrected `serviceJobsApi`/`bookingsApi`; `PaymentMethodsScreen.tsx`,
   `HelpSupportScreen.tsx`, `SettingsScreen.tsx` reference API groups
   (`paymentMethodsApi`, `helpApi`, `settingsApi`) for which **no real backend contract
   was found at all** in the live openapi.json — these three need either a
   confirmed real contract or an honest `MOCK_DESIGN_ONLY`/removed-from-navigation
   treatment, not a guessed-at endpoint.

3. **DeepSeek session contract has two live candidates** (`/v1/customer/ai-chat/sessions`
   vs `/v1/customer/ai/sessions`) and the exact request schema (does it really accept
   `language_code`/`language_name`?) was not confirmed against the Python service code
   this round — see deepseek-conversation-contract.md. No chat UI was built against
   an unconfirmed schema.

4. **Four overlapping legacy chat-shaped screens exist** (`AIChatScreen.tsx`,
   `AIAssistantScreen.tsx`, `SmartBotScreen.tsx`, `ChatScreen.tsx`) — not consolidated
   or evaluated this round.

5. **Booking/ServiceJob pipeline separation in view models is not yet built.**
   `api.ts` now correctly keeps `bookingsApi` (Booking→field_ops.Job surface) and
   `serviceJobsApi` (ServiceBooking→ServiceJob surface) as separate exports with
   separate real routes, but no typed adapter/view-model layer distinguishing the two
   pipelines for UI consumption exists yet (deferred-items.md).

6. **No IA/navigation, Home/discovery, booking-submission, or showcase screen work**
   was done this round — this round was scoped to auditing the existing app and
   correcting its foundational (auth + API contract) layer, which every other screen
   depends on.

7. Repo's actual starting state for `mobile/customer-app` differs from the brief's
   description of it (no i18n framework, no design-system tokens folder, no
   zustand/react-query found) — see existing-customer-app-audit.md. Future rounds
   should treat the brief's description of the baseline as aspirational, not
   authoritative, and re-check the actual tree.
