# Language Architecture Compliance — UX-06

## Hard constraint (from the UX-06 brief, per project memory
`project_language_architecture_correction.md`)

App-wide localization is explicitly OUT OF SCOPE for UX-06. Ordinary screens
(Home, Bookings, Chat entry, Notifications, Account, navigation) stay in a single
base UI language permanently. Multilingual behavior is exclusive to the DeepSeek
conversational booking chat.

## What was found in the repo

`src/lib/i18n.ts` exists in `mobile/customer-app` but, on inspection this round, is
a small unrelated helper — not an app-wide translation framework. No
`src/localization/i18n-setup.ts`, no `hi`/`pa` locale bundles, and no
`src/design-system/tokens/breakpoints.ts` were found anywhere in the tree (contrary
to the brief's description of the starting point — see
existing-customer-app-audit.md for the full discrepancy note). There is therefore
no pre-existing app-wide i18n system in this repository to leave alone; the
constraint is satisfied by construction — nothing was added.

## Action taken this round

None of the code changed this round (api.ts, AuthContext, LoginScreen) introduced
any translation, locale file, or language-selector logic outside the DeepSeek
contract layer. The only language-related additions are the `language_code` /
`language_name` fields threaded through `aiConversationApi.createSession` and
`aiConversationApi.sendMessage` in `src/lib/api.ts` — scoped exclusively to the
DeepSeek session contract, per the brief. No other screen, string, or navigation
label was translated or made translatable.

## Going forward

The next round's DeepSeek chat UI work must implement the searchable
BCP-47 language registry + selector *inside the chat surface only*, persisted as
conversation-level metadata, and must not leak into any other screen's copy or
navigation. This doc should be updated when that UI is built to confirm the
boundary was held.
