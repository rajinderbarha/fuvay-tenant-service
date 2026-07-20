# Known Limitations — UX-06 (updated after Round 2)

1. **126 real typecheck errors remain**, confirmed via a fresh WSL install
   (`rm -rf node_modules`, clean `npm install --legacy-peer-deps`, then
   `npx tsc --noEmit`). All 126 are in screens/nav files NOT touched this round
   (`BookingDetailScreen`, `QuoteApprovalScreen`, `InvoiceScreen`, `ProfileScreen`,
   `ChatScreen`, `BookServiceScreen`, `AppNavigator`, `TabNavigator`,
   `BookingCard`, `AIAssistantScreen`, `AIChatScreen`, `SmartBotScreen`,
   `AddressBookScreen`, `NotificationsScreen`, `BookingsListScreen`,
   `ReviewScreen`) — genuine fallout from `api.ts` now having real (narrower,
   accurate) types instead of the old fictional ones. Highest-count files:
   `BookingDetailScreen.tsx` (20), `QuoteApprovalScreen.tsx` (19),
   `InvoiceScreen.tsx` (16), `ProfileScreen.tsx` (12). None of this round's own
   changed files (`api.ts`, `AuthContext.tsx`, `LoginScreen.tsx`, the 6 screens
   fixed in Round 2, `useApi.ts`, `chatLanguages.ts`, `DeepSeekChatScreen.tsx`)
   have errors.

2. **DeepSeekChatScreen is not wired into navigation.** Built and confirmed
   type-clean in isolation, but `AppNavigator`/`TabNavigator` weren't touched
   this round given they already account for 12 of the 126 errors — wiring it
   in is next-round work (see customer-information-architecture.md).

3. **DeepSeek's actual reply-language compliance is unconfirmed.** The contract
   (routes, request/response shape) is fully confirmed live; whether DeepSeek
   actually honors the `withLanguageInstruction` text-prefix technique cannot be
   tested until a real (non-placeholder) `DEEPSEEK_API_KEY` is available in a
   test environment.

4. **PaymentMethodsScreen/HelpSupportScreen/SettingsScreen** were converted to
   honest unavailable/"coming soon" states this round rather than left calling
   fake endpoints — no real backend contract was found for saved payment
   methods, FAQs, ticket submission, or settings/preferences writes. These
   remain real gaps, not silently hidden ones.

5. **field_ops.Job (Booking pipeline) vs ServiceBooking/ServiceJob pipeline**:
   this round confirmed `/v1/customer/jobs*` is the field_ops.Job (Booking)
   pipeline, read-only for customers. No unified customer-facing "list all my
   ServiceJobs" route was found beyond `/v1/customer/service-jobs/{id}/tracking`
   (detail-only) and `/v1/customer/my-activity` (cross-pipeline aggregate,
   read-only, not yet wired into any screen). A typed, pipeline-aware adapter
   layer distinguishing the two for UI consumption is still not built.

6. **Test coverage is minimal but real**: 9 tests (5 for the corrected `api.ts`
   contract layer + `withLanguageInstruction`, 4 for `AuthContext`). No
   component-level RNTL tests for actual screens yet, no Playwright browser pass
   this round (backend is confirmed live and reachable, but a full
   login→home→chat-start→booking-list browser proof, matching UX-05C's rigor,
   was not attempted this round given the scope already covered).

7. **Sprint 29's stricter/production-appropriate AI-chat engine**
   (`/v1/customer/ai/sessions`) was not used or tested this round because it
   requires a real authenticated customer and no seeded test credentials were
   available. Confirmed live only for Sprint 15 (`/v1/customer/ai-chat/sessions`,
   works anonymously).

8. Repo's actual starting state for `mobile/customer-app` differs from the
   original brief's description of it (no i18n framework, no design-system
   tokens folder, no zustand/react-query found) — see
   existing-customer-app-audit.md.

9. Booking submission workflow, saved-address CRUD screen audit, theme/
   accessibility pass, and most of the showcase-screen inventory remain
   unstarted — see deferred-items.md for the full, prioritized punch list.

10. A one-time cross-test-file flakiness was observed under Jest's default
    parallel workers (one AuthContext test timed out only in a full parallel
    run, passed cleanly alone and under `--runInBand`) — `testTimeout` raised to
    10000ms as a defensive fix. Documented rather than hidden; not fully root
    caused this round.
