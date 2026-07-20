# CUSTOMER-L5-03 — Contract Matrix

Full endpoint documentation already exists in
`CUSTOMER-L5-03-backend-contract-audit.md` (first pass, unchanged — still
accurate, re-verified against `app/engines/customer_flow/router.py`/
`service.py` for this pass). This document adds the parity table the
deepened spec requests.

| Capability | Backend contract | Client type | Runtime schema | API client method | Query key | UI module | Test coverage | Parity |
|---|---|---|---|---|---|---|---|---|
| Customer Home (dedicated) | **no endpoint exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Home modules | **no endpoint exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Categories | `GET /v1/customer/categories` | `CategorySummaryDto` | `categorySummarySchema` | `homeApi.listCategories` | `homeQueryKeys.categories(locale, tenantId)` | `category-grid` (the only real module) | `category-schema.test.ts`, `discovery-composer.test.ts` | MATCHED |
| Featured services | `GET /v1/customer/categories/{slug}/offerings` (real, but not "featured" — just a category's offering list, no featuring/ranking concept) | `OfferingSummaryDto` | `offeringSummarySchema` | `homeApi.listOfferings` | none (unused) | none built | `category-schema.test.ts` covers the schema only | MISSING_CLIENT (UI never calls this — no service-detail destination exists to link results to, per CUSTOMER-L5-04 scope) |
| Recommendations | **no endpoint exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Recently viewed | **no endpoint exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Popular/trending services | **no endpoint exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Promotions/banners | **no endpoint exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Quick actions | **no backend-driven quick-action contract exists** | — | — | — | — | — | — | MISSING_BACKEND |
| Location context | No customer-facing "my saved location" endpoint found in this engine (addresses belong to CUSTOMER-L5-07) | — | — | — | — | — | — | MISSING_BACKEND (this sprint) |
| Search | `GET /v1/customer/search?q=` (real, verified) | not typed this sprint | — | not implemented | — | Search entry omitted entirely from Home (no dead button — CUSTOMER-L5-03 §17 explicitly permits an entry point without full search; this sprint omits even that, since there is no search screen to navigate to yet) | — | MISSING_CLIENT (deferred to CUSTOMER-L5-04, which owns Search) |

## Why So Much Is MISSING_BACKEND

This is not an implementation gap in the mobile client — it reflects the
real state of `app/engines/customer_flow/`, which implements exactly one
customer-facing discovery capability (category + offering listing) and
nothing else. Building UI for the other eleven capabilities the sprint
brief describes would mean fabricating data or contracts that don't exist,
which CUSTOMER-L5-03 §65 explicitly prohibits ("Do not hardcode the
production category catalogue... create fake recommendations... create
fake popularity"). The honest scope of what can be *real* this sprint is
narrower than the brief's full module taxonomy — documented here plainly
rather than papered over.
