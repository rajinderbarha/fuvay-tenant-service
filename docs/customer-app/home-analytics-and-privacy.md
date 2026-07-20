# Customer App — Home Analytics and Privacy

## Status: Not Implemented This Sprint

No analytics events (`home_viewed`, `category_selected`, etc.) were wired
this sprint. CUSTOMER-L5-00 built the `logger.track()` adapter interface
but no concrete analytics vendor is authorized/installed (documented as a
gap in every previous sprint's `known-gaps.md`) — adding event *call
sites* with no adapter behind them would produce untestable, unverifiable
"analytics" that silently does nothing, which is worse than being explicit
about the gap.

## What Exists Instead

Safe structured logging (`logger.warn("home.invalid_category_dropped", {
droppedCount })`) — counts only, no entity IDs, no user content. This is
the same pattern CUSTOMER-L5-01's `remote-config`/`startup` modules use for
their own diagnostics.

## Privacy Review of What HomeScreen Touches

- Reads `session.fullName` (for the greeting) and `session.avatarUrl` (for
  the header) — both already held in memory by CUSTOMER-L5-02's session
  store; nothing new is fetched, logged, or persisted.
- Category data has no PII (it's public catalogue content).
- No location, exact coordinates, phone, or email appear anywhere in
  `features/home/`.

## Tracked Gap

Once a real analytics vendor is chosen, the event list in the sprint brief
(§43) should be implemented against `logger.track()`, with the same
PII-exclusion rules already documented in CUSTOMER-L5-00/01's logging
guidance.
