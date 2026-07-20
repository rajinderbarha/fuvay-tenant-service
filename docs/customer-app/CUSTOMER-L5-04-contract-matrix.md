# CUSTOMER-L5-04 — Contract Matrix

Verified by direct reading of `app/engines/customer_flow/router.py` and
`service.py` (no OpenAPI/Swagger spec exists in this repo, and this engine
has no per-field Pydantic response schemas — every field name below is a
literal dict key built in `service.py`, cross-checked against the actual
runtime `zod` validators in this app).

A second, parallel public catalog surface exists
(`app/engines/admin_catalog/customer_router.py`, prefix `/v1/catalog/master`)
built on a different table (`MasterService`, not `MasterOffering`) with a
richer shape (`image_url`, `icon_url`, `estimated_duration_minutes`). It is
**deliberately not used** this sprint: Home already consumes
`/v1/customer/categories` (the `customer_flow` surface), and mixing two
unrelated ID spaces for "the same" category/service would create two
incompatible identifiers for one customer-facing concept. Documented here as
`NOT_APPLICABLE` (a real alternative, not adopted) rather than silently
ignored.

## Category

| Concept | Backend contract | Client type | Validator | API method | Query key | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Category detail | `GET /v1/customer/categories/{slug_or_id}` | `ValidatedCategoryDetail` | `category-detail-schema.ts` | `categoryApi.getCategoryDetail` | `categoryQueryKeys.detail` | `CategoryDetailScreen` | `category-detail-schema.test.ts` | MATCHED |
| Category hierarchy / subcategories | Absent — `ServiceCategory` has no `parent_category_id` column | — | — | — | — | — | — | MISSING_BACKEND |
| Category `image_url` | Column exists on `ServiceCategory` but customer summary only returns `icon_url`/`banner_url` | — | — | — | — | — | — | MISSING_CLIENT (serializer gap, not surfaced) |
| Category flow runtime | `GET /v1/customer/categories/{slug}/runtime` | — | — | — | — | Not used this sprint (feeds CUSTOMER-L5-05's diagnostic flow shell selection, out of scope here) | — | NOT_APPLICABLE (real, deferred) |

## Service (Offering)

| Concept | Backend contract | Client type | Validator | API method | Query key | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Service list (paginated) | `GET /v1/customer/categories/{slug}/offerings` (real `page`/`page_size`/`total`, fixed sort `display_order, name`) | `OfferingListPage` | `offering-schema.ts` | `categoryApi.listOfferings` | `categoryQueryKeys.offerings` | `CategoryDetailScreen` | `offering-schema.test.ts` | MATCHED |
| Service detail | `GET /v1/customer/categories/{slug}/offerings/{slug}` | `ValidatedOfferingDetail` | `offering-schema.ts` | `serviceDetailApi.getOfferingDetail` | `serviceDetailQueryKeys.detail` | `ServiceDetailScreen` | `offering-schema.test.ts` | MATCHED |
| Service filters (brand, service type, duration) | No filter query params beyond `search` (name substring) | — | — | — | — | — | — | MISSING_BACKEND |
| Client-selectable sort | Backend sort is fixed (`display_order, name`); no sort query param | — | — | — | — | — | — | MISSING_BACKEND |
| Service images | `MasterOffering.image_url`/`icon_url` exist in the DB model but `_customer_offering_summary` omits both | — | — | — | — | Icon fallback only, no fake stock imagery | — | MISSING_CLIENT (serializer gap) |
| Included/excluded items | No such fields anywhere on `MasterOffering` | — | — | — | — | — | — | MISSING_BACKEND |
| Preparation instructions | No such field | — | — | — | — | — | — | MISSING_BACKEND |
| Supported brands | No brand↔offering link exposed on any customer endpoint | — | — | — | — | — | — | MISSING_BACKEND |
| Estimated duration | Exists on the parallel `MasterService` shape, absent from the `MasterOffering` shape actually used | — | — | — | — | — | — | MISSING_BACKEND (in the surface used) |
| Related services | No endpoint or field anywhere (`POST /v1/customer/booking/recommendations` is a different, auth-gated, booking-flow feature that explicitly excludes service/offering entities) | — | — | — | — | — | — | MISSING_BACKEND |
| Starting price | `starting_price` (server-computed from `visit_fee`/`appointment_fee`/`base_price`) | `number` | `offering-schema.ts` | included in offering summary | — | Shown with an explicit "not a final quote" disclaimer | covered by offering-schema tests | MATCHED (with caveat, see failure-matrix) |
| `is_available` field | Present but hardcoded `True` server-side for every offering (`service.py` `_customer_offering_summary`) — not derived from real data | `boolean` (parsed, never rendered as a trust signal) | `offering-schema.ts` | — | — | Never rendered as an availability badge | `offering-schema.test.ts` (parses `false` too) | MATCHED but explicitly not trusted — see known-gaps |
| Required-field flags (`requires_address`, `requires_slot`, etc.) | Real, on offering detail's `required_fields` | `ValidatedOfferingDetail.required_fields` | `offering-schema.ts` | — | — | Rendered as informational chips | `offering-schema.test.ts` | MATCHED |

## Search

| Concept | Backend contract | Client type | Validator | API method | Query key | Screen | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| Search | `GET /v1/customer/search?q=&category_id=&page=&page_size=` | `SearchResults` | `search-schema.ts` | `searchApi.search` | `searchQueryKeys.results` | `SearchScreen` | `search-schema.test.ts` | MATCHED |
| Search pagination | `page`/`page_size` accepted but **not functional** — categories are `.limit(5)` regardless of page; offerings use `.limit(page_size)` with no `.offset()` at all | — | documented, not implemented as infinite scroll | — | — | Single-shot fetch only | — | MISMATCHED (param exists, behavior does not) |
| Search suggestions | No endpoint anywhere | — | — | — | — | — | — | MISSING_BACKEND |
| Popular searches | No endpoint anywhere | — | — | — | — | — | — | MISSING_BACKEND |
| Search history (server) | No endpoint anywhere | — | — | — | — | Local-only, customer-scoped (`recent-search-storage.ts`) | `recent-search-storage.test.ts` | MISSING_BACKEND (real local substitute, documented as such) |
| Spelling correction / did-you-mean | No field anywhere | — | — | — | — | — | — | MISSING_BACKEND |
| Search result → service detail (unscoped) | Search offerings carry no `category_id`; offering detail is category-scoped server-side | — | — | — | — | Intentionally non-navigable with an explanatory hint (`SearchServiceResult`) | — | MISMATCHED — see known-gaps |
| Search result → category detail | Category results carry full category summary including `id` | — | — | — | — | Fully navigable | — | MATCHED |

## Error Model

All endpoints return `ApiResponse[dict]` envelopes; errors surface as HTTP
status + a `ServiceOSException` error code (e.g. `CUSTOMER_CATEGORY_NOT_FOUND`,
`CUSTOMER_OFFERING_INACTIVE`). The app's existing `normalizeApiError`
(`api/api-errors.ts`, unmodified this sprint) already maps these by HTTP
status into the app's stable `ApiErrorCategory` union — no new error-handling
layer was needed. `404` is used uniformly for not-found, inactive, and
not-customer-visible categories/offerings (the backend never distinguishes
these three cases in the status code, only in the error message) — the client
therefore cannot show a distinct "hidden" vs. "deleted" message; both render
as the same generic not-found state (see failure-matrix.md).
