# CUSTOMER-L5-04 — Security Review

## Untrusted Content

- Category/service names, descriptions rendered as plain `AppText` — never
  interpolated as HTML/markup, no `dangerouslySetInnerHTML` equivalent used
  anywhere in React Native.
- Image URLs (`icon_url`/`banner_url`) validated by the existing
  `httpsOrRelativeImageUrl` zod refinement (reused unmodified from
  CUSTOMER-L5-03) — rejects any non-`https://`/non-relative scheme
  (`javascript:`, `data:`, etc.); a rejected URL falls back to a generic
  icon rather than being rendered.
- No `eval`, no dynamic `require`, no backend-supplied component-name
  resolution anywhere in the new code — `resolveModuleRenderer`-style
  registries were not needed here since there is exactly one screen per
  real route, not a dynamic module system.

## Search Query Privacy

- Raw search text is normalized before use and never logged — every
  `logger.*` call around search passes only `queryLengthBucket()` /
  `resultCountBucket()`, confirmed by reading `SearchScreen.tsx` and
  `search-queries.ts` directly (grep for `logger\.` in both files shows no
  raw-string argument).
- Recent searches are stored locally, customer-scoped, and never sent to
  analytics — `use-recent-searches.ts` only reads/writes `AsyncStorage`.
- No third-party SDK receives search query text (none is integrated in this
  app at all yet).

## Route and Navigation Safety

- `categoryId`/`serviceId` route params are branded (`CategoryId`/
  `ServiceId`) — a compile-time guard against passing the wrong kind of ID,
  though runtime validation still lives at the deep-link boundary
  (`deep-link-validator.ts`'s `[A-Za-z0-9_-]{1,64}` pattern), not in the
  branded type itself.
- Deep links to `categoryDetail`/`serviceDetails` still pass through the
  existing centralized `evaluateRouteAccess` guard — a deep link cannot
  bypass the `access: "authenticated"` requirement; an unauthenticated deep
  link is deferred to the pending-destination store, not granted early
  access.
- No full service/category object is ever passed through route params —
  only the branded ID strings (`{ serviceId, categoryId }`). Screens always
  re-fetch by ID rather than trusting a passed-in object, so a stale or
  tampered navigation param cannot inject fake service data — the real
  content always comes from the authoritative `useServiceDetail`/
  `useCategoryDetail` query.

## Tenant Isolation

The real endpoints used this sprint carry no tenant-scoping parameter or
auth dependency at all (see contract-matrix.md) — they are public catalog
reads. Query keys still include `tenantId` defensively (so a future backend
change that does add tenant scoping does not silently share cache entries
across tenants), but this is UNVERIFIED against a live multi-tenant dataset,
not proven — see known-gaps.md.

## Booking-Boundary Safety

`evaluateBookingBoundary()` fails closed: any input that isn't explicitly
"authenticated AND dev build" resolves to a non-available outcome. There is
no path in `ServiceDetailScreen` that can navigate to `BookingAssistant`
without passing through this evaluator first — `handleBookPress` checks
`boundary !== "AVAILABLE"` and returns early otherwise.

## No Production Mocks

Grepped `features/category/`, `features/service-detail/`, and
`features/search/` for `mock`, `fake`, `TODO`, `FIXME`, hardcoded category
or service names — none found. All rendered data traces to a real,
schema-validated backend response.
