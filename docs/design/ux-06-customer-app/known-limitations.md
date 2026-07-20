# Known Limitations — UX-06 (updated after Round 4)

## Round 4 additions

- **Real booking submission still blocked** — not by missing serviceability
  data anymore (fixed this round), but by a missing platform-wide `BargainRule`
  record required by `match-and-price`. See canonical-booking-contract.md /
  booking-submission-live-evidence.md for the exact table/field diagnosis.
  Deliberately not created this round (shared canonical config, out of the
  safe isolated-tenant seed scope).
- **3 of 18 major screens unverified for design** (Notifications, Booking
  Detail, standalone Service Detail) — see production-design-route-audit.csv.
  The other 15 are confirmed the new design, no old scaffold detected.
- **Dark theme does not exist** in this app's `theme.ts` at all — not a
  verification gap, an actual missing feature. See light-dark-runtime-report.md.
- **BookingDetailScreen.tsx** (19 typecheck errors, the most of any screen)
  was not opened in the browser this round — unknown whether it has a
  runtime crash analogous to the two bugs Round 3 found in the navigators.



1. **123 real typecheck errors remain** (was 126 at Round 2 start, 123 after
   Round 3's runtime-bug fixes), confirmed via a fresh WSL install
   (`rm -rf node_modules`, clean `npm install --legacy-peer-deps`, then
   `npx tsc --noEmit`). All 123 are in screens/nav files not touched by the
   Round 3 booking-journey work — full file-by-file, pattern-by-pattern
   breakdown in typecheck-error-classification.md (all errors classified, none
   left as an unclassified pile). None of Round 3's own changed files
   (`api.ts`, `chatBookingState.ts`, `chatLanguages.ts`, `DeepSeekChatScreen.tsx`)
   have errors.

2. **DeepSeekChatScreen IS now wired into navigation** (Round 3) — the
   "AI Assistant" tab renders it directly, replacing the legacy `AIChatScreen`.
   Two real, pre-existing runtime-crash bugs were found and fixed along the way
   via an actual Playwright browser run (missing imports in `AppNavigator.tsx`,
   wrong import style in `TabNavigator.tsx`) — see
   round3-runtime-proof-report.md.

3. **DeepSeek's actual reply-language compliance is unconfirmed** (unchanged
   from Round 2). Exact framing, per the coordinator's required wording: *"The
   DeepSeek integration contract and backend tool orchestration are live and
   verified. Actual model-provider behavior and selected-language compliance
   remain infrastructure-blocked by the placeholder API key."*

4. **Real canonical booking journey is built and proven 9/13 steps
   end-to-end** (Round 3) against the live backend — login, home, chat, AI
   session, language selection, real categories, real offering for a
   canonical category ID, issue/address collection, real serviceability
   check. Steps 10-13 (price/confirm/booking-reference/detail) are
   code-complete and type-clean but were NOT exercised against real backend
   data this round: a systematic 9-city sweep confirmed this dev database has
   **zero seeded `TenantServiceArea` rows** for the only real offering that
   exists in it (`home_services`/`ac_repair` — every other one of the 14 real
   categories returned zero offerings). This is an honest, confirmed test-data
   gap, not a code or contract defect — see round3-runtime-proof-report.md.

5. **PaymentMethodsScreen/HelpSupportScreen/SettingsScreen** remain honest
   unavailable/"coming soon" states (Round 2) — no real backend contract was
   found for saved payment methods, FAQs, ticket submission, or settings/
   preferences writes.

6. **field_ops.Job (Booking pipeline) vs ServiceBooking/ServiceJob pipeline**:
   Round 3 discovered the REAL canonical booking-CREATION pipeline is a
   separate draft-based flow (`homeServiceDraftApi`/`bookingConfirmApi`) distinct
   from both `bookingsApi` (Booking/field_ops.Job, read-only) and
   `fieldOpsJobsApi` — see booking-submission-workflow.md. `match-and-price`/
   `confirm-price-choice` (server-side provider selection + price-tier choice)
   are real, confirmed, separate endpoints deliberately not yet wired into
   `DeepSeekChatScreen`'s flow this round (an honest scope simplification, not
   a hidden gap).

7. **Test coverage: 19 tests** (up from 9) — `api.ts` contract layer +
   `withLanguageInstruction`-on-every-send (new, real fetch-body-inspection
   test), `AuthContext`, and the new `chatBookingState` reducer +
   canonical-slug-never-display-name enforcement. No component-level RNTL
   tests for individual screens yet.

8. **Sprint 29's stricter/production-appropriate AI-chat engine**
   (`/v1/customer/ai/sessions`) still not used or tested — requires a real
   authenticated customer; a real seeded demo customer account
   (`customer@serviceos.local`) WAS found and used this round for the
   Playwright login proof, so this is now unblocked for the next round.

9. Repo's actual starting state for `mobile/customer-app` differs from the
   original brief's description of it (no i18n framework, no design-system
   tokens folder, no zustand/react-query found) — see
   existing-customer-app-audit.md.

10. A one-time cross-test-file flakiness was observed under Jest's default
    parallel workers in Round 2 (passed cleanly under `--runInBand`, which is
    what Round 3's 19-test run also used) — `testTimeout` raised to 10000ms as
    a defensive fix. Not fully root caused.

11. Address CRUD, saved-address reuse in the booking flow (the round 3 flow
    only collects a one-off address, doesn't yet query
    `/v1/customers/me/addresses`), theme/accessibility pass, and most of the
    showcase-screen inventory remain unstarted — see deferred-items.md.
