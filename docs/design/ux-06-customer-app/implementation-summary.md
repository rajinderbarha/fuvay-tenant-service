# UX-06 Customer App — Implementation Summary (updated after Round 2)

**Status: CUSTOMER_APP_DESIGN_PARTIAL — foundational contract correction (Round 1)
+ screen rewiring, real WSL test verification, and confirmed-live DeepSeek
contract (Round 2). Navigation restructuring, remaining screen typecheck fixes,
and most feature-building work remain and are honestly deferred (see
deferred-items.md, known-limitations.md).**

## Round 1 (foundational audit + contract correction)

1. Verified worktree/branch lineage before starting — no concurrent-worktree
   interference.
2. Audited the existing `mobile/customer-app` scaffold against the live
   backend's `openapi.json`, found ~15 endpoint groups in `src/lib/api.ts`
   calling nonexistent routes (fake customer OTP auth, fake categories/
   addresses/settings/help/payments paths, the legacy dead `/v1/reviews` route).
3. Rewrote `src/lib/api.ts` to the real, verified endpoint surface, corrected
   auth to the real unified `POST /v1/auth/login`, removed the fake OTP flow.
4. Confirmed zero changes to `app/`, `frontend/*`, `mobile/staff-app`.

## Round 2 (screen fixes, real WSL verification, confirmed DeepSeek contract)

1. Fixed the 6 typecheck-broken screens the Round 1 correction produced:
   - `HomeScreen`/`JobTrackingScreen`/`ServiceHistoryScreen` rewired to the
     real, source-confirmed `fieldOpsJobsApi` (field_ops.Job / Booking
     pipeline, `GET /v1/customer/jobs*`) — live geo-tracking removed rather
     than left calling a guessed endpoint.
   - `PaymentMethodsScreen`/`HelpSupportScreen`/`SettingsScreen` converted to
     honest unavailable/"coming soon" states after confirming no real backend
     contract exists for saved payment methods, FAQs, or settings writes.
     **`SettingsScreen`'s app-wide language selector was removed outright** —
     it was a direct violation of the language-architecture hard rule, not
     just a fake-endpoint issue.
   - Fixed a broad `useAction<R>` generic-inference bug in `hooks/useApi.ts`
     that was cascading into ~9 other screens as spurious errors.
2. Ran the first real WSL verification pass this phase: fresh `npm install`
   (found and fixed two real peer conflicts: deprecated `@types/react-native`,
   missing `@react-native/jest-preset` for RN 0.85's jest-expo), added
   jest-expo + RNTL (no test framework existed before), wrote 9 real passing
   tests (`api.ts` contract layer + `AuthContext`), fixed a real AsyncStorage-
   under-Jest native-module error via the library's documented mock. Fresh
   `tsc --noEmit`: **126 real errors remain, all in screens not yet touched**
   (see known-limitations.md for the per-file breakdown) — none in this
   round's own changed files.
3. Pushed the DeepSeek contract from "two open candidates" to
   **CONFIRMED_REAL**: read `app/engines/ai_conversation/{customer_router,
   service,deepseek_client}.py` directly, then live-curled both session-create
   and send-message against the running backend — got real 200 responses with
   the real DeepSeek tool-calling loop executing (`tools_called` included
   `get_service_categories`/`get_category_offerings`/`get_service_faqs`),
   falling back gracefully because this dev environment's `DEEPSEEK_API_KEY` is
   a placeholder (an infra limitation, documented as such, not a contract gap).
   Confirmed the backend has NO language field anywhere in this engine.
4. Built `src/lib/chatLanguages.ts` (real 14-language BCP-47 registry with
   search) and `src/screens/DeepSeekChatScreen.tsx` (real chat screen against
   the confirmed contract, with a searchable language selector whose selection
   is folded into message text via `withLanguageInstruction` since the backend
   has no language field) — not yet wired into navigation, a deliberate
   scope decision documented in customer-information-architecture.md.
5. Audited navigation/IA for the first time (`AppNavigator.tsx`/
   `TabNavigator.tsx`): found an existing 5-tab structure close to but not
   matching the target Home/Bookings/Chat/Notifications/Account IA — decision
   on the final tab set is documented but not yet implemented.
6. Re-confirmed zero changes to `app/`, `frontend/*`, `mobile/staff-app` after
   this round's work.

## What remains (see deferred-items.md for the full, prioritized list)

126 typecheck errors in untouched screens, navigation restructuring, chat-UI
navigation wiring, screen-consolidation of the 4 overlapping AI-chat screens,
typed pipeline-aware view-model layer, booking submission workflow, theme/
accessibility pass, component-level tests, live Playwright browser proof,
showcase inventory, switching to the Sprint 29 AI engine once real customer
credentials exist, and confirming DeepSeek's actual reply-language compliance
once a real API key is available.

## Final state (Round 2)

- Branch: `design/ux-06-customer-app`
- Worktree: `G:\serviceos-ux06-customer-app`
- Commits this phase: `0775bb5`, `b0b6362` (Round 1), `1d68eda`, `faa0af0`,
  plus this docs commit (Round 2)
- No backend, no other frontend app, touched (re-verified via `git diff --stat`).
