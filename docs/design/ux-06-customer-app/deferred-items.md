# Deferred Items — UX-06 Round 1

Following UX-05's disposition vocabulary (KEEP_AND_REDESIGN / API_CONTRACT_REQUIRED /
MOCK_DESIGN_ONLY / NOT_APPLICABLE), scoped to what this round could not reach:

| Item | Disposition | Reasoning |
|---|---|---|
| HomeScreen/JobTrackingScreen/ServiceHistoryScreen rewiring | KEEP_AND_REDESIGN | Real backend contracts exist (`serviceJobsApi`, `bookingsApi`), just need the screens re-pointed and a `job.status`/`job.job_number` shape reconciliation |
| PaymentMethodsScreen | API_CONTRACT_REQUIRED | No `/v1/*payment*method*` customer route found anywhere in openapi.json; consistent with the "no platform payment processing" rule — may simply not be a real feature. Needs explicit confirmation before rebuilding. |
| HelpSupportScreen (FAQ + tickets) | API_CONTRACT_REQUIRED | No `/v1/help/*` route found. Needs confirmation of whether a support/ticket engine exists under a different name (e.g. complaints engine has real routes — `/v1/customer/complaints*` — possibly the intended surface for "help") |
| SettingsScreen (notification/theme/language prefs) | API_CONTRACT_REQUIRED | No `/v1/settings/{id}/preferences` route found; `/v1/customer/notifications/preferences` IS real and could cover the notification-toggle portion |
| DeepSeek chat UI (screen, state machine, language selector) | KEEP_AND_REDESIGN, blocked on contract confirmation | Needs the two-engine ambiguity resolved (see deepseek-conversation-contract.md) before building against a schema |
| Typed pipeline-aware view-model/adapter layer | KEEP_AND_REDESIGN | High-value, cheap once the underlying `api.ts` corrections (done this round) are stable; not started |
| Customer IA/navigation (5-tab) | Not evaluated | `AppNavigator.tsx`/`TabNavigator.tsx` exist in the scaffold and were not opened this round |
| Booking submission workflow | Not started | Depends on catalog + pipeline view-model work above |
| Light/dark theme, accessibility pass | Not evaluated | `src/styles/theme.ts` exists in the scaffold, not audited this round |
| Fresh WSL install/typecheck/test/build verification | Not started | See known-limitations.md item 1 |
| Live Playwright login proof | Not started | Backend is confirmed live and reachable at localhost:8000 this round, but no browser pass was run |
| Showcase screen inventory | Not started | No showcase screens exist yet in this app |
