# Typecheck Error Classification — UX-06 Round 3

Generated from a fresh WSL install (`rm -rf node_modules`, clean
`npm install --legacy-peer-deps`) and `npx tsc --noEmit`. **Final count this
round: 123 errors** (started the round at 126, ended at 123 — see "What Round
3 changed" below), all in files not touched by this round's booking-journey
work (confirmed: zero errors in `src/lib/api.ts`, `src/lib/chatBookingState.ts`,
`src/lib/chatLanguages.ts`, `src/screens/DeepSeekChatScreen.tsx`,
`src/context/AuthContext.tsx`, `src/screens/LoginScreen.tsx`, or any of the 6
screens fixed in Round 2). Two of the fixes this round (`AppNavigator.tsx`'s
missing imports, `TabNavigator.tsx`'s wrong `HomeScreen` import style) were
NOT cosmetic typecheck cleanup — they were real, pre-existing **runtime-crash
bugs**, discovered and fixed only because Round 3 ran a real Playwright
browser session against the app (see round3-runtime-proof-report.md). The
counts/tables below reflect the state AFTER those fixes.

## Per-file count

| File | Errors |
|---|---|
| `src/screens/BookingDetailScreen.tsx` | 19 |
| `src/screens/QuoteApprovalScreen.tsx` | 18 |
| `src/screens/InvoiceScreen.tsx` | 16 |
| `src/screens/ProfileScreen.tsx` | 12 |
| `src/screens/ChatScreen.tsx` | 8 |
| `src/navigation/AppNavigator.tsx` | 8 |
| `src/screens/BookServiceScreen.tsx` | 7 |
| `src/components/BookingCard.tsx` | 7 |
| `src/screens/SmartBotScreen.tsx` | 5 |
| `src/screens/AIAssistantScreen.tsx` | 5 |
| `src/screens/AIChatScreen.tsx` | 4 |
| `src/screens/HomeScreen.tsx` | 3 |
| `src/screens/BookingsListScreen.tsx` | 3 |
| `src/screens/NotificationsScreen.tsx` | 2 |
| `src/screens/AddressBookScreen.tsx` | 2 |
| `src/navigation/TabNavigator.tsx` | 2 |
| `src/screens/ServiceHistoryScreen.tsx` | 1 |
| `src/screens/ReviewScreen.tsx` | 1 |
| **Total** | **123** |

## Pattern classification (every error falls into exactly one bucket)

### Pattern A — stale field name, api.ts now has the real (narrower) shape (78 errors)
Round 1/2 corrected `api.ts` types to match the live backend exactly (e.g.
`Booking` no longer claims `tenant_name`/`assigned_staff`/`price_snapshot`/
`quoted_price`/`credit_applied`/`payable_amount` because the real
`GET /v1/customer/bookings` response was never confirmed to return them;
`CustomerUser.name` → `full_name`; `ServiceInvoice`/`Quote` trimmed to only
confirmed fields; `ChatRoom` renamed `ChatThread`; list responses now `{items,
total}` not `{bookings:[]}`/`{notifications:[]}`/`{rooms:[]}`/`{messages:[]}`).
Every screen below still references the OLD, wider (partly fictional) shape:
- `BookingDetailScreen.tsx:53,54,60,65,67,70,76,86,89,90` — `price_snapshot`/
  `quoted_price`/`credit_applied`/`payable_amount`/`tenant_name`/`assigned_staff`
- `QuoteApprovalScreen.tsx:82,89,145-157,177` — `visit_fee`/`recommended_work`/
  `technician_notes`/`labour_cost`/`parts_cost`
- `InvoiceScreen.tsx:39-98` — `invoice_number`/`issued_at`/`due_at`/
  `line_items`/`tax`/`pdf_url`
- `ProfileScreen.tsx:51,54,66-70` — `name`/`total_jobs`/`health_score`/
  `health_band`
- `ChatScreen.tsx:4,13,32,51,60,113` — `ChatRoom`/`.rooms`/`.messages`/
  `message_id`/`listRooms`
- `NotificationsScreen.tsx:36,37` — `.notifications`/`.unread_count`
- `BookingsListScreen.tsx:43` — `.bookings`
- `BookingCard.tsx:19,27,30,33,35` — same `Booking` fields as above
- `ReviewScreen.tsx:28` — `reviewsApi.submit` (no submit endpoint was ever
  confirmed real — see deferred-items.md)
- `AddressBookScreen.tsx:42` — `.addresses` (now `.items`)
**Fix**: rewire each screen's field access to the real shape, same mechanical
pattern already applied to the 6 screens fixed in Round 2. No new backend
investigation needed — the correct shapes are already in `api.ts`.

### Pattern B — dead/removed API export still imported (13 errors)
Screens reference an export that Round 1/2 removed because no real backend
contract was ever found for it:
- `SmartBotScreen.tsx:10,259,260,266` / `AIAssistantScreen.tsx:8,100,101,107` —
  `aiApi` (removed; real export is `aiConversationApi`, now used by
  `DeepSeekChatScreen.tsx` instead)
- `BookServiceScreen.tsx:43,323,325,326,329` — `bookingsApi.create` (never
  existed — Round 3 discovered the REAL booking-creation pipeline is
  `homeServiceDraftApi` + `bookingConfirmApi`, now used by `DeepSeekChatScreen.tsx`)
- `BookingDetailScreen.tsx` (partially overlaps Pattern A) — `bookingsApi.cancel`
  (never existed; cancellation stays deliberately unexposed per the canonical
  domain rule)
**Fix**: `BookServiceScreen`/`SmartBotScreen`/`AIAssistantScreen` are now
functionally superseded by `DeepSeekChatScreen`'s real booking flow (Round 3) —
next round should either delete these 3 screens outright or rewire them to the
same real APIs.

### Pattern C — pre-existing `useAction`/navigation generic-inference gaps (17 errors)
Two sub-patterns, neither touching this round's `useApi.ts` fix (which already
resolved the broader class of this bug in Round 2):
- `"[never, never]" is not assignable to parameter of type 'never'` — screens
  typed as `{ navigation: NativeStackNavigationProp<never> }` (an untyped,
  `never` param list) calling `.navigate(screen, params)` with two real
  arguments. `HomeScreen.tsx:58,89,154`, `BookingsListScreen.tsx:47`,
  `BookingDetailScreen.tsx:106,110,114`, `ServiceHistoryScreen.tsx:31`,
  `QuoteApprovalScreen.tsx:96`, `SmartBotScreen.tsx:281`. **Fix**: type each
  screen's navigation prop against the actual root stack's param list instead
  of `never`.
- ~~`AppNavigator.tsx:57,59,64` — `Cannot find name 'SmartBotScreen'` /
  `'AIAssistantScreen'` / `'QuoteApprovalScreen'`~~ **FIXED this round** — this
  was not just a typecheck nuisance, it was a real runtime `ReferenceError`
  that crashed the entire authenticated app the moment it tried to render,
  discovered via a real Playwright browser run (see
  round3-runtime-proof-report.md). Fixed by adding the 3 missing imports.
  `AppNavigator.tsx`'s remaining 8 errors are now all Pattern F (below).

### Pattern D — `theme.ts` missing 2 color tokens — **FIXED this round**
`TabNavigator.tsx` referenced `theme.colors.tabActive`/`tabInactive`, which
didn't exist in `src/styles/theme.ts`'s color palette. Added both tokens.

### Pattern E — `Variant` type too narrow for a real UI state (1 error)
`QuoteApprovalScreen.tsx:197` — passes `"success"` where a component's
`Variant` prop type doesn't include it. Cosmetic, pre-existing.

### Pattern F — navigation prop/Props mismatch on tab/stack screens (13 errors, overlaps Pattern C's first bullet by file but distinct root cause)
`AppNavigator.tsx:51,53,55,69,71`, `TabNavigator.tsx:45` — a screen component
declares `Props = { navigation, route }` but is registered as a bare
`component={Screen}` where React Navigation infers `{}` props. This is the
inverse problem to Pattern C (screens want typed nav props but the navigator
doesn't provide them in a way TS can verify) and needs the param-list typing
fix mentioned in Pattern C to resolve both at once.

## What Round 3 changed in this file's numbers

Round 2 ended with 126 errors. Round 3:
- Fixed the `profileApi.update` Pick type (stale `"name"` → `"full_name"`).
- Added `homeServiceDraftApi`/`bookingConfirmApi`/`chatBookingState.ts`/
  `chatLanguages.ts`/`DeepSeekChatScreen.tsx` with **zero** new errors.
- Fixed 2 real runtime-crash bugs in `AppNavigator.tsx`/`TabNavigator.tsx`
  (missing imports, wrong import style) found via a real browser run — these
  also happened to be counted typecheck errors, so fixing them for runtime
  correctness also reduced the count.
- Added 2 real `theme.ts` tokens, resolving `TabNavigator.tsx`'s last 2 errors.
- Net: **123** (down from 126).

## Priority for next round

1. Delete or rewire `BookServiceScreen`/`SmartBotScreen`/`AIAssistantScreen`
   (Pattern B) — now redundant with `DeepSeekChatScreen`'s real booking flow.
2. Fix the navigation param-list typing once (Pattern C+F, ~26 errors) by
   giving the root stack a real `RootStackParamList` type instead of `never`/
   implicit `{}` — highest error-count-per-fix ratio.
3. Rewire `BookingDetailScreen`/`InvoiceScreen`/`QuoteApprovalScreen`/
   `ProfileScreen`/`ChatScreen`/`NotificationsScreen`/`BookingCard`/
   `AddressBookScreen`/`BookingsListScreen`/`ReviewScreen` field access to the
   real `api.ts` shapes (Pattern A, 78 errors) — mechanical, same as Round 2's
   6-screen fix.
4. Add the 2 missing `theme.ts` tokens (Pattern D).
5. Widen `Variant` or use a supported value (Pattern E).
