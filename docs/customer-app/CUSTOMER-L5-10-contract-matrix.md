# CUSTOMER-L5-10 — Contract Matrix

Verified by direct reading of `app/engines/home_service_booking/service.py`,
`customer_router.py`, `constants.py`, `app/engines/admin_catalog/bargain_engine.py`,
`app/engines/admin_catalog/models.py` (`BargainRule`), `app/engines/admin_catalog/service.py`,
`app/engines/admin_catalog/admin_router.py` — plus an exhaustive repo-wide
grep for any bargain-session/offer/attempt/counteroffer persistence model
and any bargain-specific rate-limit/cooldown mechanism, cross-checked by an
independent background research pass.

## Endpoint Used

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/customer/home-services/booking-drafts/{draftId}/confirm-price-choice` | The platform's entire real customer-facing "negotiation" capability: customer picks `low`/`mid`/`high`, backend resolves and stores the exact corresponding amount from the already-computed `price_snapshot.price_options` (CUSTOMER-L5-09). |

## Endpoints/Concepts Investigated and Confirmed NOT to Exist (parity: `MISSING_BACKEND`)

Per this sprint's exhaustive research, **none** of the following spec-requested
concepts correspond to any real, reachable backend capability:

| Spec concept | Investigated | Result |
|---|---|---|
| `get bargain eligibility` | Grepped for any eligibility field/endpoint | `MISSING_BACKEND` — no `bargain_allowed`/eligibility field or endpoint exists anywhere. |
| `create bargain session` / `get bargain session` | Grepped for `BargainSession`, `bargain_session` (case-insensitive, whole repo) | `MISSING_BACKEND` — zero hits. No session concept exists; `confirm-price-choice` is a single stateless call against the draft. |
| `submit customer offer` (free-text/custom amount) | Read `confirm_price_choice`'s full request handling | `MISSING_BACKEND` — the endpoint accepts only `{"price_tier": "low"\|"mid"\|"high"}`, never a raw amount. |
| `get counteroffer` / `accept counteroffer` / `reject counteroffer` | Read `evaluate_customer_bargain`'s full decision logic; grepped for `CounterOffer`, `counter_offer` | `MISSING_BACKEND` — the real decision set is exactly `"accepted"\|"rejected"\|"provider_approval_required"`; no `"counter"` decision or counteroffer-amount generation exists anywhere. |
| `submit revised offer` | Re-read `confirm_price_choice` for a resubmission guard | `MATCHED` (as "re-pick a different tier") — the endpoint has no guard against being called again with a different tier; this is the real, honest equivalent of a "revised offer." |
| `cancel bargain session` | N/A (no session exists to cancel) | `NOT_APPLICABLE` — this sprint's "skip/cancel" action simply means "never call confirm-price-choice, proceed at the pricing screen's estimate" (see bargain-architecture.md's Fixed-Price/Skip Boundary). |
| `get bargain history` | N/A (no session/offer log exists) | `MISSING_BACKEND` — the only audit trail is the generic `home_service_booking_draft_events` table's `EVENT_PRICE_ESTIMATED` rows (backend-internal; not exposed via any customer-facing history endpoint). |
| Attempt limits (`max_attempts`, `attempts_used`, `attempts_remaining`) | Read `BargainRule.max_attempts`; grepped for attempt-tracking columns/logic in `home_service_booking` | `MISSING_BACKEND` — `BargainRule.max_attempts` is a real column but confirmed never read by the customer-facing flow (admin-only, same dead-code status as `bargain_enabled`). No attempt counter exists on the draft or anywhere else. |
| Rate limiting / cooldown (`Retry-After`, `cooldown_seconds`) | Grepped for `rate_limit`, `RateLimit`, `throttle`, `cooldown` across `home_service_booking/` and shared middleware | `MISSING_BACKEND` — no bargain-specific rate limiting exists; only the app-wide generic HTTP client retry/backoff (pre-existing, cross-cutting, unrelated to bargaining specifically) applies. |
| `attach negotiated price to draft` (dedicated endpoint) | N/A | `NOT_APPLICABLE` — `confirm-price-choice` itself both computes AND attaches in one call; there is no separate attach step. |
| `invalidate bargain` (dedicated endpoint) | N/A | `MISSING_BACKEND` — no invalidation endpoint exists; re-calling `match-and-price` (L5-09) already overwrites `price_snapshot` fresh, and this sprint's screen always re-derives its own preflight state from the current draft on every mount (see bargain-architecture.md). |

## `confirm-price-choice` — Full Contract (re-confirmed this sprint)

- **Request**: `{"price_tier": "low" | "mid" | "high"}` — raw dict, no Pydantic model, `body["price_tier"]` KeyErrors on a missing key (real, disclosed backend robustness gap, unchanged from L5-09's known-gaps.md).
- **Response**: `{"booking_summary": {...}, "draft_status": "..."}`.
  `booking_summary` fields: `selected_tenant_id`, `selected_provider_name`,
  `selected_zipcode`, `selected_price_tier`, `customer_offer`,
  `allowed_offer_min`, `allowed_offer_max`, `platform_fee_amount`,
  `payment_mode`.
- **Server-side validation**: `price_tier` must be one of the three literal
  strings (422 `INVALID_PRICE_TIER` otherwise); `draft.selected_tenant_id`
  and `draft.price_snapshot.price_options` must already exist (422
  `HOME_BOOKING_NO_PROVIDER_AVAILABLE` otherwise — same code L5-08/L5-09
  already handle for their own preconditions). The actual amount is always
  read back from the backend's own already-stored `price_options` — never
  accepted as a client-submitted number.
- **Repeatable**: yes, confirmed — calling it again with a different tier
  simply overwrites `booking_summary`'s tier-related fields and appends a
  new `EVENT_PRICE_ESTIMATED` audit event; no duplicate-submission guard
  exists or is needed (there's no session/attempt state to corrupt).
- **Draft mutation**: writes only into `draft.booking_summary` (merged, not
  replaced) — does **not** change `draft.status`, `draft.price_status`, or
  `draft.provider_match_status`.

## Fields — Classification (per §11/§35's requested field list)

| Spec-requested field | Real backend equivalent | Classification |
|---|---|---|
| `bargain_session_id` | None | `MISSING_BACKEND` |
| `estimate_id` / `estimate_revision` | None (unchanged from L5-09) | `MISSING_BACKEND` |
| `current_offer` | `booking_summary.customer_offer` (only after a successful call — the resolved amount, not a pending/in-progress offer) | `MATCHED` (renamed semantics — this is the *result*, not an in-flight offer) |
| `current_counteroffer` | None | `MISSING_BACKEND` |
| `negotiated_price` | `booking_summary.customer_offer` (+ `selected_price_tier` for context) | `MATCHED`, `CUSTOMER_VISIBLE` |
| `attempt_limit` / `attempts_used` / `attempts_remaining` | None | `MISSING_BACKEND` |
| `cooldown_until` | None | `MISSING_BACKEND` |
| `expires_at` (bargain-specific) | None (only the generic draft `expires_at`, unchanged from L5-09) | `MISSING_BACKEND` |
| `revision` (session revision) | None | `MISSING_BACKEND` |
| `allowed_offer_min` / `allowed_offer_max` | Real, present in `booking_summary` | `SUPPORTED`, `INTERNAL_ONLY` this sprint — same reasoning as L5-09's identical fields: these are bargain-floor/ceiling-adjacent internals, not rendered. |
| `platform_fee_amount` | Real, present in `booking_summary` | `SUPPORTED`, `INTERNAL_ONLY` — not rendered, same reasoning as L5-09. |
| `payment_mode` | Real, present in `booking_summary` | `SUPPORTED`, `CUSTOMER_VISIBLE` — reused verbatim from L5-09's own rendering of this identical fixed value. |

## Error Contract

| Backend error_code | HTTP | Meaning | This sprint's handling |
|---|---|---|---|
| `INVALID_PRICE_TIER` | 422 | Malformed tier value | Cannot occur from this client — it only ever sends one of the three literal, UI-controlled values. Not customer-reachable; no dedicated UI state needed. |
| `HOME_BOOKING_NO_PROVIDER_AVAILABLE` | 422 | No matched provider/price options on the draft yet | Same generic unavailable-state handling already established in L5-08/L5-09's contract-matrix docs — this sprint's own preflight check (mirroring L5-09's pattern) prevents reaching this screen without a valid `price_snapshot` in the first place, so this is a defense-in-depth case, not an expected customer-facing path. |

No new error codes are introduced by this sprint's real flow.

## Decisive Confirmation: Manual Bargaining Is Product-Deactivated

`app/core/feature_flags.py:15-22` — `MANUAL_BARGAIN_RULES_ENABLED` defaults
to `False`; `AUTO_PRICE_OPTIONS_ENABLED`/`PROVIDER_FIRST_MATCHING_ENABLED`
default to `True`. A repo document,
`MANUAL_BARGAIN_DEACTIVATION_FINAL_REPORT.md`, records this as a
deliberate product decision. This means the raw-offer/floor/
`below_floor_action`/`provider_approval_required`/`max_attempts` machinery
in `bargain_engine.py`/`BargainRule` — the only place in this codebase
that superficially resembles the spec's counteroffer/attempt-limit model —
belongs to a module the product has explicitly turned off. The real, live,
product-intended flow is the one this sprint implements:
`match-and-price` → `confirm-price-choice`. This is not this sprint's own
scope judgment call; it is what the backend's own feature-flag
configuration and deactivation report state directly.

## Confirmed: No Rate Limiting Applies to This Flow

`app/core/security.py:44-61`'s `RATE_LIMITS` table covers only
`auth:*`/`api:*`/`webhook:delivery` keys. `customer_router.py`'s
`confirm_price_choice` route has no `rate_limiter` dependency. No app-wide
rate-limit middleware exists in `app/main.py`. `rate_limiter.check_and_raise`
is called from exactly 4 files (`auth/router.py`, `enterprise_grid/router.py`,
`platform_commerce/router.py`, `rag/router.py`) — `home_service_booking`
is not among them.
