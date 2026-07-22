# Customer Home — Implementation Report (UX-07 Pass 3d)

Commit: `13c818f` (Home rebuild), plus the nav commits `b3a0fa0` (tab bar /
Chat fold) that Home's navigation calls depend on.

## Files changed

- `mobile/customer-app/src/screens/HomeScreen.tsx` — full rebuild (structure
  in `customer-home-information-architecture.md`). Data sources unchanged
  from the prior screen: `bookingsApi.list()`, `fieldOpsJobsApi.list()`,
  `useAuth()`. No new backend calls were added or needed for Home itself.
- `mobile/customer-app/src/screens/__tests__/HomeScreen.test.tsx` — new,
  6 real (non-snapshot) tests.
- `mobile/customer-app/src/navigation/TabNavigator.tsx` — `AIAssistant`
  route now types `{ initialCategoryLabel?: string } | undefined` params;
  tab icons switched to `@expo/vector-icons`; tab set narrowed to 5.
- `mobile/customer-app/src/navigation/AppNavigator.tsx` — added a `Chat`
  root-stack screen entry (title "Messages") so Profile can still reach the
  real human/provider support surface after it left the primary tab bar.
- `mobile/customer-app/src/screens/ProfileScreen.tsx` — added a "Messages"
  row under Support, navigating to the new `Chat` stack screen.

## Real vs honestly-omitted data

| Element | Source | Real or honest placeholder? |
|---|---|---|
| Greeting name | `useAuth().user.full_name` | Real; time-of-day-only fallback when absent (never fake) |
| Saved location chip | none wired (no Home-facing "default address" endpoint found) | Honest placeholder label, routes to real `AddressBook` |
| Active job | `fieldOpsJobsApi.list(5)` | Real |
| Recent bookings | `bookingsApi.list()` | Real (same source as before) |
| Popular-service tiles | static local list (7 items) | Real UI, but the tile `label` is NOT assumed to equal a real backend category slug — it's passed to SmartBot as free text and matched there (see `category-smartbot-handoff.md`) |
| Trust row | static copy | Honestly scoped — dropped "24/7" (no evidence found) |

## Decision: Chat tab fold, not deletion

`ChatScreen.tsx`'s existing Pass 3b disposition note was re-read and
re-verified this pass: it is backed by a real, distinct `chatApi` contract
(`/v1/customer/chat/threads*`) from SmartBot's `aiConversationApi`
(`/v1/customer/ai-chat/sessions*`). Per the brief's explicit instruction to
use judgment rather than delete a genuine distinct surface, Chat was folded
into `ProfileScreen`'s Support section ("Messages") and given a real
root-stack route (`Chat`) instead of a primary tab slot, freeing that slot
for the required Notifications tab.

## What Home did NOT change

- No changes to `bookingsApi`, `fieldOpsJobsApi`, or any backend call
  signature.
- No changes to `BookingCard`, `Skeleton`, or any shared component's
  public API (only new test-only mocks of `Skeleton` — see
  `theme-stability-non-regression.md`).
- `ThemeContext`/`theme.ts` untouched, per the explicit instruction not to
  touch the working ThemeContext.
