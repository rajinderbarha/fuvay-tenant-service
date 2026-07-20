# Customer App — Home Content Composition

## Compiled Section Types Implemented This Sprint

Only one of the sprint brief's compiled section types has real backing
data and is implemented: `category-grid` ("Services"). All others
(`location-summary`, `search`, `account-action`, `service-rail`,
`recent-activity`, `campaign`, `trust-message`, `support-entry`) are
**correctly omitted** because no backend contract exists for them (see
`CUSTOMER-L5-03-backend-contract-audit.md`) — not built as empty/fake
placeholders, per the sprint brief's own instruction ("do not build a
generic dynamic-screen engine... do not fabricate").

## Section Eligibility

The one implemented section (categories) is omitted entirely (not shown
with an empty grid) when the composed item list has zero entries — see
`HomeScreen.tsx`'s `EmptyState` branch, which only renders when
`categories.data.items.length === 0`, distinct from the loading and error
branches.

## Ordering

`discovery-composer.ts#composeCategorySections`: stable sort by
`(display_order, name)` — the backend's own order is respected first, name
is a deterministic tie-breaker (never random). Verified by a dedicated test
(`composeCategorySections` "produces the same order across repeated
calls").

## Deduplication

By `id`, keeping the first occurrence (the backend already orders by
`display_order`, so the first occurrence is the intended one). Duplicate
count is tracked (`droppedDuplicateCount`) for diagnostics but not
currently surfaced anywhere (no dev inspector integration this sprint —
tracked in `known-gaps.md`).

## Item Caps

`MAX_HOME_CATEGORIES = 12` — Home never renders an unbounded grid even if
the backend returns more (the query itself also requests `page_size: 50`,
well above the display cap, so composition — not the network request — is
what enforces the visible limit).

## Source Priority

Not applicable this sprint in the CUSTOMER-L5-01 remote-config sense (that
priority system is `compiled-defaults | cache-* | remote-*` for the
*startup configuration*, a different concept from Home's data). Home's
categories have exactly one source: the live `GET /v1/customer/categories`
response via TanStack Query's own cache — there is no local disk cache for
category data this sprint (see `home-cache-and-refresh-policy.md`).

## Locale Fallback

The query key includes `locale` (currently hardcoded `"en"` — see
`known-gaps.md`; CUSTOMER-L5-00's `i18next` locale isn't threaded into
`useHomeCategories` yet). The backend response itself has no localized-name
fallback mechanism visible in the audited contract (`name`/`description`
are plain strings, not locale maps) — so there is no client-side locale
fallback to implement for category content specifically; only the
surrounding UI chrome (empty/error states) is localizable, and isn't
localized this sprint (also tracked in `known-gaps.md`, consistent with
CUSTOMER-L5-02's same gap).

## Stale / Degraded Behavior

Not implemented — TanStack Query's `staleTime: 5min` provides basic
staleness semantics, but there's no visible "this data may be outdated"
banner distinct from CUSTOMER-L5-00's generic `OfflineBanner`. Tracked in
`known-gaps.md`.

## Prohibited Dynamic Rendering

Confirmed absent: no `frontend_component_key`/`primary_engine_key` field
returned by the backend is used to dynamically choose a component or
render arbitrary content — those fields are fetched (they're part of the
DTO) but never read by `HomeScreen`/`CategoryCard`. Only compiled,
hand-written components render.
