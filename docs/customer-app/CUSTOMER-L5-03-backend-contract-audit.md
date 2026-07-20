# CUSTOMER-L5-03 — Backend Contract Audit

Read directly from `app/engines/customer_flow/router.py` and
`app/engines/customer_flow/service.py`.

## Endpoints Used

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/v1/customer/categories?search=&category_type=&page=&page_size=` | optional (guest browsing allowed server-side; this app requires auth per product policy — see below) | `{ items: CategorySummary[], total, page, page_size }`, active + customer-visible only, ordered by `display_order, name` |
| GET | `/v1/customer/categories/{slug}` | optional | Category detail + `required_steps`/`optional_steps` — not used this sprint (no category-detail screen yet) |
| GET | `/v1/customer/categories/{slug}/offerings` | optional | Offering summaries for a category — `home-api.ts#listOfferings` exists but is not called by `HomeScreen` yet (no service-detail screen to link to) |
| GET | `/v1/customer/search?q=` | optional | Category/offering search — not used this sprint (CUSTOMER-L5-04 scope) |

## Response Shapes (verified from `service.py`)

`_customer_cat_summary()`:
```
id, name, slug, description, category_type, icon_url, banner_url,
customer_flow_type, frontend_component_key, primary_engine_key,
available_offering_count, display_order
```

`_customer_offering_summary()`:
```
id, name, slug, description, offering_class, customer_flow_type,
primary_engine_key, pricing_model, starting_price, visit_fee,
appointment_fee, requires_type, requires_brand
```

`starting_price` is a **real** backend field (`o.default_visit_fee`/
`default_appointment_fee`/`default_base_price`, whichever is set) — safe to
display per CUSTOMER-L5-03 §18 ("starting-price label only if backed by a
valid pricing contract"). No rating, discount, or provider-count field
exists anywhere in this contract, so none of those are displayed (they
would be fabricated).

## No Dedicated Home-Composition Endpoint

There is no `/v1/customer/home` (or similar) endpoint — CUSTOMER-L5-03 §28's
"preferred priority 1" (dedicated home-composition endpoint) does not
exist. This sprint uses priority 2/3 instead: a single bounded request
(`GET /v1/customer/categories`) for the one section this sprint implements.
No modules/marketplace-modules/campaigns/recommendations/recent-activity
endpoints exist anywhere in this codebase — those sections are correctly
omitted rather than fabricated (see `home-content-composition.md`).

## Auth Policy Decision

The backend's docstring says "guest browsing supported for category/
offering listings" — the endpoint itself does not require authentication.
This sprint's `route-registry.ts` still marks `home` as `access:
"authenticated"` per the sprint brief's own acceptance criteria (§52.7:
"guest cannot reach Home"), which is a **product/UX policy decision**, not
a backend limitation — a future sprint could make Home guest-accessible if
that policy changes, without any backend work.

## Not Implemented / Not Available

- Marketplace modules (Automotive, Restaurants, etc.) — no such concept
  exists in this backend at all; `remote-config`'s `modules[]` (CUSTOMER-
  L5-01) is a separate, forward-looking concept with no live data source
  yet. Home does not render a module grid this sprint (correctly omitted
  per §12/§14 — "do not show empty module placeholders").
- Campaigns/banners — no endpoint.
- Recommendations/popular/recently-used — no endpoint.
- Location/service-area summary — no customer-facing "my saved location"
  endpoint was found in this engine; deferred to whichever sprint owns
  addresses (matches this sprint's own §10, which permits omitting the
  section entirely when no location flow exists).
