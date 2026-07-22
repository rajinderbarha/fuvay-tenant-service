# Category → SmartBot Handoff (UX-07 Pass 3d)

Commit: `be43db2`.

## The real problem being solved

Home's category tiles/search are a static local list (`POPULAR_SERVICES` in
`HomeScreen.tsx`) that predates and does not track the real backend catalog
1:1 (`catalogApi.categories()` returns real `ServiceCategory` rows with
`id`/`slug`/`name` fields that can change server-side). The prior Home
screen's `openCategory()` was honest about this gap in its own code comment
("catId isn't passed through yet ... a real, documented gap") and simply
routed to SmartBot with no context, forcing every customer to re-answer
"what service do you need" even after tapping a specific category tile.

## The fix

`TabNavigator`'s `AIAssistant` route now carries an optional
`{ initialCategoryLabel?: string }` param. `DeepSeekChatScreen` reads it via
its new `route` prop and, on mount:

1. Starts a real AI session if one doesn't exist yet (`startSession()`).
2. Opens the real booking flow (`openBookingFlow()` → `catalogApi.categories()`).
3. Fuzzy-matches `initialCategoryLabel` against the REAL returned category
   list by name (case-insensitive substring, both directions, plus a
   slug-with-underscores-replaced fallback) — **never** assumes the label
   equals a real slug/id.
4. On a match: calls the same `pickCategory()` path a manual tap would use
   (fetches real offerings for that category), so the category step is
   genuinely skipped, not faked.
5. On no match: shows the full category list as before, plus a small
   honest notice ("We couldn't find an exact match for \"X\" — please
   choose below") and pre-fills the free-text issue field with the
   original label so it isn't silently lost.

## Why this is honest, not a shortcut

- The category ultimately used to call `homeServiceDraftApi.start()` is
  always the real `ServiceCategory` object from `catalogApi.categories()`'s
  response — never a client-invented id built from the Home tile's local
  `id` field (`"ac"`, `"plumbing"`, etc, which are Home's own values, not
  guaranteed real backend slugs).
- If the match fails, the customer is never silently routed into a wrong
  category — they see the real list and their original wording is
  preserved as a starting point.

## Verified

`src/screens/__tests__/DeepSeekChatScreen.handoff.test.tsx`:
- match found → `catalogApi.categoryOfferings` called with the real slug,
  category picker text never shown, category-context header present.
- match not found → offerings never fetched, honest notice shown with the
  original label, category list still reachable.
- language switch after a successful handoff → category-context header
  and non-reset flow state both survive (see
  `guided-smartbot-design-contract.md` for why this works structurally).
