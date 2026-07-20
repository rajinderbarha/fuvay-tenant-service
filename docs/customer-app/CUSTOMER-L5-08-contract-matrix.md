# CUSTOMER-L5-08 — Contract Matrix

Verified by direct reading of `app/engines/home_service_booking/service.py`,
`matching_engine.py`, `constants.py`, `customer_router.py`, `tenant_engine/models.py`,
cross-checked by an independent background research pass reaching identical
conclusions on every point below (including several details this client's
own pass had not yet reached, folded in here).

## Endpoint Used

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/customer/home-services/booking-drafts/{draftId}/match-and-price` | Backend auto-selects exactly one eligible provider, computes its price options, and persists the result onto the draft — single synchronous call, no session/polling. |

### Endpoints explicitly NOT used (and why)

| Method | Path | Reason |
|---|---|---|
| `POST` | `.../match-providers` | `[DEPRECATED]` — router docstring: "do not build new customer UI against this." Confirmed unreachable from any real caller (repo-wide grep: only its own definition + tests). |
| `POST` | `.../select-provider` | Same — superseded by the fact that `match-and-price` auto-selects; there is no customer-selection step in the real product. |
| `POST` | `.../confirm-price-choice` | Real, but owns the price-tier confirmation step — out of scope for this sprint (CUSTOMER-L5-09). This sprint never calls it and never lets the customer proceed past provider preview into a price commitment. |

## Request

No body. `category_id`, `master_service_id` (`offering_id`), `city`, `zipcode`, `offering_type_id`, `brand_id` are all read server-side from the draft itself (`customer_router.py:174-184`) — this client sends nothing but the path's `draftId` and the auth token.

## Response — fields this client parses and renders

From `selected_provider` (`build_customer_safe_provider`, matching_engine.py:155-164):

| Field | Type | Rendered? | Notes |
|---|---|---|---|
| `tenant_id` | string | Not displayed | Stored only; used as the stable key/log field, never shown as UI text. |
| `provider_name` | string | Yes | Primary display field. |
| `public_badges` | string[] | Yes | Closed 3-value set (`"Verified"`, `"Highly Rated"`, `"High Completion"`) mapped to localized labels client-side (`badge-label-mapping.ts`); unrecognized values render as-is and log `provider_badge_unmapped`. |
| `rating` | number \| null | Yes | Real `Tenant.rating_average`; renders "Not yet rated" when null. No `review_count` field exists anywhere in this response — never fabricated. |
| `customer_visible_reason` | string | Yes | A **fixed, identical sentence for every match** ("Best matched provider based on service coverage, availability, quality, and completion history.") — not a per-provider dynamic explanation. Rendered verbatim as real backend copy, not treated as if it were candidate-specific reasoning. |

Plus, outside `selected_provider`:

| Field | Type | Rendered? | Notes |
|---|---|---|---|
| `draft_status` | string | Used internally | Written into the local draft cache (matches `useCheckServiceability`'s existing pattern); not shown as raw text. |

## Response — fields that exist but are deliberately never parsed or rendered

| Field | Why excluded |
|---|---|
| `selected_provider_price_options` (`currency`, `low_price`, `mid_price`, `high_price`, `platform_fee_percent`, `platform_fee_amount`, `allowed_offer_min/max`, `payment_mode`) | Pricing/bargain UI is CUSTOMER-L5-09's scope. The zod schema for this sprint has no key for this object at all — `z.object()`'s default unknown-key-stripping means it is structurally impossible for this sprint's parsed type to carry a pricing field, not just a UI choice to hide one. |
| `area_market_comparison` (`area`, `competitor_provider_count`, `area_competitor_min/avg/max`) | Same reason — pricing-adjacent, deferred. |
| `selected_provider_admin` / `internal_score` / `internal_score_breakdown` | Never present in the customer-facing response at all (`reveal_internal_score=False` is hardcoded in `customer_router.py:183`) — nothing to exclude, it structurally cannot arrive. |

## Fields that do NOT exist anywhere in the real contract (aspirational vs. real)

Per the spec's aspirational model, these were checked and confirmed absent — not fabricated to compensate:

- No distance/ETA field (`distance_score` is an internal-only coarse heuristic, `100.0` if exact-zip else `60.0` — never surfaced).
- No availability-state field (folded into the internal eligibility gate as a boolean pass/fail; never returned).
- No `review_count` / number-of-reviews field.
- No provider logo/cover image, no supported-brands list, no years-active, no completed-jobs count, no health summary.
- No candidate list, no ranking position, no per-candidate score, no comparison against runner-up providers.
- No technician identity at this stage (`provider_team_members` is queried only as an aggregate headcount internal to scoring — never selects or exposes a specific technician).
- No match session/match ID/expiry/polling — one synchronous call, re-runnable at will.

## Badge Integrity Finding (important, disclosed)

`"Verified"` is **hardcoded unconditionally** into every `public_badges` list
(matching_engine.py:586) — it does **not** check `Tenant.verification_status`
at all. This is a real backend behavior, not a client bug, but it means the
"Verified" badge is not actually a real verification signal today. This
client renders the badge as the backend sends it (honest passthrough) but
this is documented prominently in `known-gaps.md` as a backend-side data
integrity concern, not silently treated as trustworthy in a way that could
mislead the customer beyond what the backend itself already does.

## Error Contract

| Backend error_code | HTTP | Backend detail message | What this client actually shows |
|---|---|---|---|
| `HOME_BOOKING_NO_PROVIDER_AVAILABLE` | 422 | "No eligible providers available in {city}. Try a nearby city." | Generic "couldn't find a match" state — see below, this client's own `normalizeApiError` (pre-existing, cross-cutting, unmodified this sprint) never reads the response body's `error_code`/`detail` on failure, only the HTTP status. |
| `PRICE_OPTIONS_UNAVAILABLE` | 422 | "Selected provider does not have a customer price range configured yet." | Same generic state — indistinguishable from the above at this client's current error-handling layer. |

**Disclosed architectural finding**: `api-client.ts`'s `performRequest`
(pre-existing since CUSTOMER-L5-01, unmodified) calls
`normalizeApiError(null, { status: res.status, requestId })` on any non-2xx
response — it never calls `res.json()` on the failure path, so the real
backend `error_code`/`detail` body is discarded before this or any other
sprint's code ever sees it. Both real 422 codes above collapse to the same
generic `validation_error` category with a generic safe message. This is a
pre-existing, cross-cutting client limitation (not introduced this sprint,
not fixed this sprint — fixing it would mean changing shared error-handling
infrastructure used by every feature in the app, out of this sprint's
scope) and is why `ProviderPreviewScreen`'s failure state uses one generic
"no match found" copy rather than distinguishing the two real backend
reasons. Filed as a P1 known gap.

## Draft Mutation Side Effects (server-side, this call always performs these)

Every successful call — even a repeated one with an unchanged result —
overwrites `draft.selected_tenant_id`, `draft.selected_provider_snapshot`,
`draft.price_snapshot.price_options`, sets `provider_match_status =
"matched"`, `status = "provider_matched"`, and appends one
`EVENT_PROVIDER_MATCHED` event row. This client's `useMatchProvider`
mutation reflects only the fields it actually parses (`draft_status`,
mirrored provider fields for its own UI state) into the local draft cache —
it does not attempt to read or mirror `selected_provider_snapshot`'s
backend-only `internal_score`/`matching_score_snapshot` sub-fields (which
this client's schema never even accepts).

## Idempotency

Not a create-once operation — calling it again re-runs the full
eligibility/scoring/pricing pipeline and overwrites the draft's fields
(never appends a new draft or reservation). This client's retry/refresh
action on failure or on an explicit "find again" tap simply re-invokes the
same mutation; no local idempotency key is needed or sent (the endpoint has
none in its contract).
