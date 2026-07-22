# SmartBot Language Verification (Workstream 12, done this round)

## Finding

`mobile/customer-app/src/lib/chatLanguages.ts` (UX-06's `CHAT_LANGUAGES`
registry) contained 14 BCP-47 languages (en/hi/pa/bn/ta/te/mr/gu/kn/ml/ur/
ar/es/fr) — exceeding UX-07's explicit requirement of exactly 3
(English/हिन्दी/ਪੰਜਾਬੀ).

## Fix applied this round

Narrowed `CHAT_LANGUAGES` to exactly `en`/`hi`/`pa`. Confirmed via grep that
`chatLanguages.ts` is imported ONLY by `DeepSeekChatScreen.tsx` (no other
screen references it), so this is a safe, fully scoped change — no risk of
breaking the app-wide "no language selector outside SmartBot" rule (which
was already correctly satisfied — the file's own header comment documents
that no other screen imports it).

## Verified NOT changed

- The selector remains a modal opened from within the chat screen (not a
  full settings page) — matches "compact ... selector in the chat header"
  requirement in spirit; the modal itself still has a search input, which
  is now somewhat oversized for a 3-item list but not a violation of any
  stated rule. Deferred: simplifying the modal UI itself (search box removal
  / true one-tap 3-button layout) to a later round — not attempted this
  round due to time budget; flagged in `deferred-enhancements.md`.
- `withLanguageInstruction()` folding mechanism in `lib/api.ts` — unchanged,
  still the correct approach (backend has no language field).

## Not run this round

- No component test exists specifically for the language selector; the
  existing test suite was not re-run against this specific file this round
  (see `unit-component-test-report.md` for what WAS run).

## Pass 3d addendum — language switch preserves category-handoff state

Re-verified against this pass's new category-handoff mechanism specifically
(not just the general chat-language wiring documented above): a real test
(`src/screens/__tests__/DeepSeekChatScreen.handoff.test.tsx`, third case)
arrives with `initialCategoryLabel: "Plumbing"`, confirms the real category
match succeeded (`catalogApi.categoryOfferings` called with the real
`plumbing` slug and the category-context header rendered), switches the
conversation language via the real `chat-language-btn` → 
`chat-language-option-hi` UI path, and asserts the category-context header
and flow state are still present afterward (not reset back to the category
list). This is structurally guaranteed by `language` and `booking` being
independent React state (a `useState` and a `useReducer` respectively) on
the same component — switching one never dispatches against the other — but
this pass adds a real assertion of that behavior rather than relying on
reading the code.
