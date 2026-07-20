# CUSTOMER-L5-04 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-04-runtime-evidence.md`.
   Identical constraint to CUSTOMER-L5-02/03's own P0 gap. The primary
   reason this sprint's gate is PARTIAL.

## P1

2. **Global search cannot deep-link SERVICE results to full detail.** The
   `/v1/customer/search` endpoint's offering results carry no `category_id`,
   and the real offering-detail endpoint is category-scoped
   (`/categories/{slug}/offerings/{slug}`). `SearchServiceResult` is
   intentionally non-interactive for this reason, with an explanatory hint
   ("Open from its category to view full details") rather than a guessed or
   broken destination. A category-scoped search entry point (e.g. a "Search
   within this category" action from `CategoryDetailScreen`) would close
   this gap but was not built this pass — the route param
   (`Search: { initialQuery?: string }`) has no category-scope field yet.
3. **Tenant/region isolation is UNVERIFIED, not proven.** The real endpoints
   used this sprint have no tenant or region scoping in their request/response
   shape at all (confirmed by reading the router — no auth dependency, no
   tenant/region query param). Query keys defensively include `tenantId`
   anyway, but there is no live multi-tenant dataset in this environment to
   prove isolation actually holds if the backend contract changes to add
   real tenant scoping later.
4. **Category service search filter exists in the API client but has no UI.**
   `categoryApi.listOfferings({ search })` is wired and real, but
   `CategoryDetailScreen` does not expose a search input for it — the
   sprint's real, higher-value gap was the missing screens themselves, not
   in-category filtering. See filter-and-sort-contract.md.
5. **No component/render tests for the three new screens** — only one level
   below (`ServiceListItem`) has a render test; `CategoryDetailScreen`,
   `ServiceDetailScreen`, `SearchScreen` are verified by TypeScript
   compilation and manual code review only, consistent with every previous
   sprint's same deprioritization (no prior sprint in this repo has a
   screen-level render test either).

## P2

6. **`AUTH_REQUIRED` booking-boundary outcome is architecturally unreachable
   in practice** — `serviceDetails` itself already requires
   `access: "authenticated"`, so a customer can never reach
   `ServiceDetailScreen` unauthenticated in the first place. Kept for
   defensive completeness and to protect a future relaxation of that route's
   access policy, exactly like CUSTOMER-L5-03's identical `AUTH_REQUIRED`
   note for its own module-visibility evaluator.
7. **No distinct 429 (rate-limited) customer message.** `ApiError`'s
   `rate_limited` category renders through the same generic search-error
   state as any other failure — not incorrect, but not a bespoke
   "you're searching too fast" message either. Untestable without a live
   backend that actually rate-limits.
8. **`is_available` is parsed but never surfaced**, since it is hardcoded
   `True` server-side for every offering and therefore carries no real
   information — this is a deliberate non-feature, not an oversight, but is
   worth flagging in case a future backend change makes the field
   meaningful and nobody remembers to revisit the client.
9. **No analytics events actually wired to a vendor** — `logger.*` calls
   exist (`service_booking_started`, `search_results_loaded`, etc.) but, as
   with every previous sprint, there is no analytics SDK integrated in this
   app at all; these are structured logs only.

## P3

10. **Category `image_url` and offering `image_url`/`icon_url`/
    `estimated_duration_minutes` exist in the database models but are not
    returned by the customer-facing serializers** — a backend serializer
    gap, not a frontend omission. Documented in contract-matrix.md as
    `MISSING_CLIENT`. `ServiceListItem` uses a generic icon rather than
    fabricating stock imagery.
11. **Orphaned locale-scoped cache entries are never proactively evicted**
    on a language change — same low-impact, documented-not-fixed pattern as
    CUSTOMER-L5-03's identical gap for Home's own category cache.
