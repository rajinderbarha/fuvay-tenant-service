# UX-07 Pass 3b — Customer-App Screen Dark-Mode Migration Report

Date: 2026-07-21
Worktree: G:/serviceos-ux07-cross-app, branch design/ux-07-cross-app-production-readiness

## Scope

Migrate the remaining customer-app screens off the static `theme`/`gs` import
(`src/styles/theme.ts`) onto the real `useTheme()` hook
(`src/context/ThemeContext.tsx`), mirroring the pattern already established
in `LoginScreen.tsx`, `HomeScreen.tsx`, and `SettingsScreen.tsx`. This was a
visual/token swap only — no API calls, navigation, or functional behavior
were changed.

## Screens migrated (14)

1. `AddressBookScreen.tsx`
2. `BookingDetailScreen.tsx`
3. `BookingsListScreen.tsx`
4. `ChatScreen.tsx`
5. `HelpSupportScreen.tsx`
6. `InvoiceScreen.tsx`
7. `JobTrackingScreen.tsx`
8. `NotificationsScreen.tsx`
9. `PaymentMethodsScreen.tsx`
10. `ProfileScreen.tsx`
11. `QuoteApprovalScreen.tsx`
12. `ReviewScreen.tsx`
13. `ServiceDetailScreen.tsx`
14. `ServiceHistoryScreen.tsx`

Each screen now calls `const { theme } = useTheme();` and builds its
`StyleSheet` via a `makeStyles(theme: Theme)` function, using the same
semantic tokens already defined in `theme.ts` (no new tokens invented). The
shared `gs.*` helper styles (`screen`, `row`, `label`, `sep`, `card`,
`sectionTitle`) that each screen used from the old static export were
inlined into each screen's own `makeStyles` (mirroring how `HomeScreen.tsx`
already does this — there is no shared themed `gs` equivalent yet, so each
screen defines the handful of shared keys it needs).

## ChatScreen disposition

**Kept — genuinely distinct from the AI assistant, not a duplicate.**
`ChatScreen` is backed by the real human/provider chat contract:
`chatApi` → `/v1/customer/chat/threads*` (`listThreads`, `getMessages`,
`sendMessage`, `markRead`), confirmed live in `src/lib/api.ts`. This is a
customer↔technician/staff thread tied to a job/booking.
`DeepSeekChatScreen` is a separate AI conversational-booking assistant
(`aiConversationApi` → `/v1/customer/ai-chat/sessions*`). The two call
different endpoint families, serve different purposes, and are both wired
into `TabNavigator.tsx` (`AIAssistant` tab → `DeepSeekChatScreen`, `Chat` tab
→ `ChatScreen`) — no dead route, no duplication. Only the theme import was
migrated; no removal, no redirect.

## Bug fixed incidentally during migration

`NotificationsScreen.tsx`'s `TYPE_COLOR.booking` was the literal string
`"var(--info)"` — a CSS custom-property reference, not a valid React Native
color value, so the unread-notification dot for `booking`-type notifications
was silently rendering with an invalid/undefined color. Since `TYPE_COLOR`
had to move inside the component to access `theme` anyway, it was corrected
to `theme.colors.info`.

## Confirmed-real endpoints (not fixture data)

- `InvoiceScreen` → `invoiceApi.get()` → real `GET /v1/customer/service-invoices/{id}`.
- `QuoteApprovalScreen` → `quoteApi.get/approve/reject()` → real
  `/v1/customer/quotes/*`. Per `api.ts`'s own Round 5 note, a few optional
  `Quote` fields (`visit_fee`/`labour_cost`/`parts_cost`/`recommended_work`/
  `technician_notes`) were widened but not re-verified live that round —
  this remains a documented, pre-existing gap in `known-limitations.md`, not
  something newly discovered or silently patched in this pass.

`PaymentMethodsScreen`'s content/copy was left untouched per instruction
(already a correct `SAFE_INFORMATIONAL_SCREEN` from a prior round) — only
its theme tokens were migrated.

## Verification

Performed a clean from-scratch install to rule out the working-tree-drift
class of issue previously logged for this repo (`rm -rf node_modules
package-lock.json`, fresh `npm install --legacy-peer-deps --no-audit
--no-fund`, 866 packages installed):

- **Tests: 58/58 passing** (`node node_modules/jest/bin/jest.js`) — same
  total as at HEAD before this pass; no screen-level test files exist yet,
  so this pass didn't add or remove any test cases.
- **Typecheck: 0 errors** introduced by this pass. `tsc --noEmit` reports 7
  pre-existing errors, confirmed present at HEAD via `git stash` before any
  of this pass's edits:
  - 2× `TS7016` in `AuthContext.test.tsx` / `ThemeContext.test.tsx` — missing
    type declarations for `@testing-library/react-native`.
  - 5× `TS7031` in `TabNavigator.tsx` — implicit-any `focused` binding
    parameters in tab-icon render callbacks.
  None of these 7 pre-existing errors are in any of the 14 migrated screens.

## Out of scope (left for a follow-up pass, per instruction)

Responsive-width work, accessibility audits, and Playwright were explicitly
excluded from this session and are not addressed here.
