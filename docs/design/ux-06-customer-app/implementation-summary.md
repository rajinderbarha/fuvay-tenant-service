# UX-06 Customer App — Implementation Summary (updated after Round 3)

**Status: CUSTOMER_APP_DESIGN_PARTIAL — foundational contract correction
(Round 1), screen rewiring + real WSL test verification + confirmed-live
DeepSeek contract (Round 2), and a real, chat-connected canonical booking
journey proven 9/13 steps live end-to-end against the running backend, with
2 real runtime-crash bugs found and fixed via an actual Playwright browser
run (Round 3). Remaining typecheck errors are now fully classified (not an
unclassified pile); 4 of the required 13 runtime-proof steps are blocked by a
confirmed test-data gap (zero seeded service areas), not code — see
round3-runtime-proof-report.md. Substantial feature-building work remains and
is honestly deferred (see deferred-items.md, known-limitations.md).**

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

## Round 3 (real canonical booking journey wired into chat + navigation)

1. Corrected a Round 1/2 assumption: `bookingsApi`/`fieldOpsJobsApi` are
   read-only (no `POST` create). Discovered the REAL canonical booking-creation
   pipeline by reading `app/engines/home_service_booking/customer_router.py` +
   `app/engines/final_records/confirm_router.py` directly — a draft-based flow
   (`homeServiceDraftApi` + `bookingConfirmApi`) with a real, confirmed
   `Idempotency-Key` header mechanism.
2. Corrected `catalogApi`'s `ServiceCategory`/`ServiceOffering` field names
   after reading `app/engines/customer_flow/service.py` (Round 1 had guessed
   without reading source).
3. Built `src/lib/chatBookingState.ts`: a typed reducer where every state
   transition requires a real API response payload — never an assumed
   progression. `canonicalSlugsFor()` is the single choke point sending real
   backend slugs onward, enforced by a real test that the sent value is never
   the display name.
4. Rewired `DeepSeekChatScreen.tsx` to a real, structured "Book a service" flow
   (category picker → offering picker → issue/address → serviceability check
   → server-returned price display → idempotent confirm → real booking
   reference → navigate to BookingDetail) and wired it into real navigation
   (`TabNavigator`'s "AI Assistant" tab).
5. Ran a genuine Playwright browser session against a real Expo web dev server
   and the live backend, logged in as a real seeded demo customer. Found and
   fixed 2 real, pre-existing runtime-crash bugs (missing imports in
   `AppNavigator.tsx`, wrong import style in `TabNavigator.tsx`) that a
   typecheck pass alone hadn't revealed the true severity of. Proved 9 of 13
   required sequence steps genuinely real end-to-end; steps 10-13 blocked by a
   confirmed test-data gap (zero seeded `TenantServiceArea` rows for the only
   real offering in this dev DB), not a code defect.
6. Expanded tests from 9 to 19 (chatBookingState reducer, canonical-ID
   enforcement, a real fetch-body-inspection test proving
   `withLanguageInstruction` is applied on every `sendMessage` call).
7. Fully classified all 123 remaining typecheck errors by file:line + root-
   cause pattern (typecheck-error-classification.md) — none left unclassified.
8. Corrected the DeepSeek framing per the coordinator's exact required
   wording: contract + tool orchestration are live and verified; model-
   provider behavior and language compliance remain infra-blocked by the
   placeholder API key — kept as two explicitly separate claims.
9. Re-confirmed zero changes to `app/`, `frontend/*`, `mobile/staff-app`.

## What remains (see deferred-items.md for the full, prioritized list)

123 typecheck errors in untouched screens (fully classified, prioritized fix
list included), consolidating the 3 now-redundant legacy AI-chat screens,
wiring `match-and-price`/`confirm-price-choice` (server-side provider
selection) into the booking flow, using saved addresses instead of one-off
text entry, navigation IA restructure, typed pipeline-aware view-model layer,
theme/accessibility pass, per-screen component tests, exercising the full
booking journey against a database with real seeded service areas, switching
to the Sprint 29 AI engine, and confirming DeepSeek's actual reply-language
compliance once a real API key is available.

## Final state (Round 3)

- Branch: `design/ux-06-customer-app`
- Worktree: `G:\serviceos-ux06-customer-app`
- Commits this phase: `0775bb5`, `b0b6362` (Round 1); `1d68eda`, `faa0af0`,
  `9e97180` (Round 2); `772f183`, `d98bfa7` (Round 3), plus this docs commit
- No backend, no other frontend app, touched (re-verified via `git diff --stat`).
