# UX-07 Pass 3e — Status Rationale (Guided SmartBot Restructure)

## Scope actually executed this pass

This pass was scoped very narrowly against real time/effort budget available. It
delivered a real, tested, honest subset of the full Pass 3e mission
(guided-SmartBot restructure + Home/SmartBot responsive + accessibility +
Playwright evidence). It did NOT attempt the full mission — see
`deferred-pass-4-work.md` (renamed/updated) for the explicit remainder.

## What is real and verified

1. **Real contract read first.** `DeepSeekChatScreen.tsx` and
   `chatBookingState.ts` were read in full before any change. Finding: the
   free-text DeepSeek chat (`aiConversationApi`) has NO backend-exposed
   question/options/step-count structure — the `/messages` endpoint only
   returns `tools_called` (tool names) and a synthesized `reply` string. The
   one surface in this app that genuinely has real, structured
   question-then-real-options turns is the **guided booking flow modal**
   (category -> offering -> [brand] -> [offering type] -> issue/address ->
   serviceability -> price -> confirm), driven by `chatBookingReducer`. This
   pass's restructure work targeted that real surface, not a fabricated one on
   top of the free-text chat.
2. **Compact header** added to the booking-flow modal: back/close control,
   service-specific title (`{category.name} Assistant`, falling back to the
   handoff label), no fabricated icon system beyond the existing Ionicons set.
3. **Honest progress indicator**: `progressLabel`/`progressPct`/
   `currentStepIndex`/`stepsFor` in `DeepSeekChatScreen.tsx` compute "Step X of
   Y" from the real reducer step + real conditional steps (brand /
   ac_repair-offering-type), never a fabricated fixed count. Verified by test.
4. **Collapsed-by-default answers-so-far summary** (`booking-summary-toggle`,
   `booking-summary-*`), showing only real gathered fields (category, offering,
   issue, address). Expand/collapse is accessible
   (`accessibilityState.expanded`).
5. **Editing an earlier answer**: implemented honestly as "Start over"
   (`booking-start-over`), NOT a fabricated partial-edit/dependency-invalidation
   system. Rationale: the real backend draft binds category/offering (and
   brand) at creation time via `homeServiceDraftApi.start`/`updateFields` —
   there is no real "go back to offering, keep the address" contract to
   emulate without inventing backend behavior that doesn't exist. "Start over"
   resets only the local `chatBookingReducer` state; it reuses the existing
   `session.id` and does **not** call `aiConversationApi.createSession` again
   (verified by test — no duplicate session).
6. **Accessible names added** to every real option row that previously had
   none: category rows, offering rows, offering "Details" link, brand rows,
   ac_repair offering-type rows (all `accessibilityRole="button"` +
   descriptive `accessibilityLabel`). Progress row and summary toggle also
   carry accessible labels/state.
7. Booking/pricing/address/schedule/confirmation logic, the
   `ServiceBooking->ServiceJob` contract, and all backend code were **not**
   touched — confirmed by diff (`package-config-drift-report.md`/git diff
   below only shows `DeepSeekChatScreen.tsx` + one new test file).

## What was NOT attempted (see known-limitations.md for full list)

- Home screen responsive/accessibility work (only SmartBot's guided-flow modal
  was touched this pass).
- Language-control-as-segmented-control redesign (kept the existing modal
  language picker — already narrowed to 3 languages in a prior pass; this pass
  did not redesign its presentation).
- Optional photo-flow UI (no existing photo-upload capability was found wired
  into this screen or `lib/api.ts` within the time available to verify
  thoroughly — not implemented rather than inventing a new upload endpoint).
- Full CRITICAL/HIGH accessibility audit CSV across Home+SmartBot.
- 320/360/390/430px Playwright/Expo-web visual evidence.
- The full ~20-document deliverable set listed in the mission brief — only the
  documents in this file's directory listing that accompany this pass were
  produced; treat any doc named in the original brief but absent here as not
  written.

## Final status

**UX07_INTEGRATION_PARTIAL** — a real, tested, narrowly-scoped slice of the
guided-SmartBot restructure shipped; the responsive/accessibility/Playwright
breadth of the full mission was not executed and is not claimed.
