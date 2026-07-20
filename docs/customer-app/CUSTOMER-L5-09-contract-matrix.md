# CUSTOMER-L5-09 — Contract Matrix

Verified by direct reading of `app/engines/home_service_booking/service.py`,
`matching_engine.py`, `constants.py`, `customer_router.py`,
`app/engines/admin_catalog/models.py` (`BargainRule`, `ServicePricingRule`),
`app/engines/admin_catalog/bargain_engine.py`, `app/engines/pricing/models.py`
(`CityTierConfig`) — cross-checked by an independent background research
pass reaching identical conclusions, plus several additional confirmed
details folded in here (exact `DRAFT_EXPIRY_HOURS = 24`, exact dead-code
status of `bargain_enabled`, exact `price_status` update-site list).

## Endpoint Used

| Method | Path | Purpose | This sprint's use |
|---|---|---|---|
| `POST` | `/v1/customer/home-services/booking-drafts/{draftId}/match-and-price` | Re-derives the matched provider **and** its Low/Mid/High price options in one call (already partially used by L5-08). | **Primary and only estimate source.** L5-08 parsed only `selected_provider`; this sprint additionally parses `selected_provider_price_options`. Re-called for revalidation (no separate revalidate endpoint exists). |

## Endpoints Investigated and Explicitly NOT Used (with parity status)

| Method | Path | Parity status | Reason not used |
|---|---|---|---|
| `POST` | `.../price-estimate` | `UNREACHABLE` (from this sprint's real flow) | Real, working, city-tier-aware endpoint — but architecturally independent of provider matching (no provider dependency, produces one `base_price` not a Low/Mid/High trio, sets a different draft status `"price_estimated"`). This app's real navigation flow (Serviceability → ProviderPreview → this sprint) never precedes provider matching with it. See pricing-resolution.md for the full analysis of why it is out of scope rather than fabricated into this flow. |
| `POST` | `.../confirm-price-choice` | `MATCHED` (contract), `NOT_APPLICABLE` (this sprint) | Real, exact tier-only contract (verified below) — but this **is** the bargain/tier-acceptance step this sprint is explicitly forbidden from implementing ("bargain offer submission... bargain acceptance"). CUSTOMER-L5-10's scope. |
| `POST` | `.../match-providers`, `.../select-provider` | `UNREACHABLE` | Deprecated (confirmed dead in L5-08's research, unchanged). |
| `POST` (admin) | `.../evaluate_bargain_preview` (`admin_catalog/admin_router.py`) | `NOT_APPLICABLE` | Admin-only preview tool, different router, different auth. Confirms there is no customer-reachable numeric counter-offer engine anywhere in this platform today. |

## `confirm-price-choice` — Full Contract (documented for CUSTOMER-L5-10's benefit, not called this sprint)

- **Request**: `{"price_tier": "low" | "mid" | "high"}` — a raw, non-Pydantic-validated dict; a missing `price_tier` key raises an unhandled `KeyError` server-side (a real, disclosed backend robustness gap — see known-gaps.md).
- **Response**: `{"booking_summary": {...}, "draft_status": "..."}`. `booking_summary` contains `selected_tenant_id`, `selected_provider_name`, `selected_zipcode`, `selected_price_tier`, `customer_offer`, `allowed_offer_min/max`, `platform_fee_amount`, `payment_mode` — the customer's chosen amount is always read back from the backend's own already-stored `price_snapshot.price_options`, never accepted as a client-submitted number (hard-enforced, `service.py:687-696`).

## Response — Fields This Sprint Parses and Renders

From `selected_provider_price_options` (`compute_price_tiers`, matching_engine.py:223-233):

| Field | Type | Classification | Rendered? |
|---|---|---|---|
| `currency` | string | SUPPORTED, CUSTOMER_VISIBLE | Yes — used for all money formatting. Always `"INR"` today (hardcoded backend-side; see pricing-semantics.md). |
| `low_price` | number | SUPPORTED, CUSTOMER_VISIBLE | Yes — "Lower estimate." |
| `mid_price` | number | SUPPORTED, CUSTOMER_VISIBLE, DERIVED (backend-computed midpoint) | Yes — the primary/expected amount (backend-computed, never client-recomputed). |
| `high_price` | number | SUPPORTED, CUSTOMER_VISIBLE | Yes — "Upper estimate." |
| `platform_fee_percent` | number | SUPPORTED, INTERNAL_ONLY this sprint | Not rendered as a line item — no product-approved customer-facing fee breakdown exists; noted for completeness only (see §29 guardrail against exposing internal fee/margin structure). |
| `platform_fee_amount` | number | SUPPORTED, INTERNAL_ONLY this sprint | Not rendered — same reasoning; this is the fee baked into `low_price`/`high_price`, not a separate customer line item the backend labels as such. |
| `allowed_offer_min` / `allowed_offer_max` | number | SUPPORTED, INTERNAL_ONLY this sprint | Not rendered — these are `confirm-price-choice`'s internal bargain-floor/ceiling inputs (CUSTOMER-L5-10 concern), numerically identical to `low_price`/`high_price` in the current formula but conceptually distinct and out of this sprint's display scope. |
| `payment_mode` | string | SUPPORTED, CUSTOMER_VISIBLE | Yes — rendered as a one-line "pay the provider directly" note (real, fixed value `"customer_pays_provider_directly"`). |

Plus, outside the price-options object:

| Field | Rendered? |
|---|---|
| `selected_provider` (all 5 fields, unchanged from L5-08) | Yes — reused, this screen shows the same provider summary L5-08 already established. |
| `draft_status` | Used internally (draft cache patch), not shown as raw text. |

## Response — Fields Never Parsed (structural, via schema, not just UI choice)

| Field | Why excluded |
|---|---|
| `area_market_comparison` | Competitor/market pricing data, not part of the customer's own estimate explanation; no requirement in this sprint's spec asks for a competitor price comparison UI. |
| `selected_provider_admin` / internal score fields | Never present in the customer-facing response at all (unchanged from L5-08). |

## Field Existence Reality Check (per the spec's own requested field list)

| Spec-requested field | Real backend equivalent | Status |
|---|---|---|
| `estimate_id` | None — `price_snapshot` has no ID, only nested inside the draft itself | `MISSING_BACKEND` |
| `revision` / `pricing_rule_version` | None — no revision counter anywhere on price data | `MISSING_BACKEND` |
| `valid_from` / `expires_at` (price-specific) | None — only the generic draft-level `expires_at` (24h from draft creation, `DRAFT_EXPIRY_HOURS = 24`) exists | `MISSING_BACKEND` |
| `components` (itemized) | None — `price_options` is five flat numbers, no component array | `MISSING_BACKEND` |
| `included_items` / `excluded_items` | None as structured data — see pricing-semantics.md for how this sprint handles this honestly via static, product-reviewed copy tied to the real `payment_mode` value, not fabricated per-estimate data | `MISSING_BACKEND` |
| `bargain_allowed` | None — `BargainRule.bargain_enabled` exists in the DB but is never read by this flow or returned to the customer | `MISSING_BACKEND` |
| `bargain_floor` | Exists internally (`allowed_offer_min`) but this sprint does not expose it (per explicit instruction) | `SENSITIVE`, never rendered |
| `tax_amount` | None anywhere in this flow's responses | `MISSING_BACKEND` |
| `pricing_model` | `MasterService.pricing_model` exists and is real, but is not part of `match-and-price`'s response — it's already fetched separately via the draft's own `pricing_model` enrichment field (`_enrich_draft`, confirmed present on `useDraft`'s response since L5-06) | `MATCHED` (via a different, already-integrated endpoint) |

## Error Contract

| Backend error_code | HTTP | Meaning | This sprint's handling |
|---|---|---|---|
| `HOME_BOOKING_NO_PROVIDER_AVAILABLE` | 422 | No eligible provider (same as L5-08) | Generic unavailable state — same client-side error-body-discard limitation documented in L5-08's contract-matrix.md, unchanged and still not fixed this sprint (cross-cutting, out of scope). |
| `PRICE_OPTIONS_UNAVAILABLE` | 422 | Matched provider has no configured `BargainRule` customer range | Same generic unavailable state — indistinguishable from the above at this client's current error layer, same as L5-08's identical finding. |

No new error codes are introduced by this sprint's real flow — `match-and-price`'s error surface is unchanged from L5-08's already-documented contract.

## Currency and Tax — Explicit, Disclosed Limitation

`currency` is hardcoded `"INR"` server-side (`compute_price_tiers`'s default parameter, never overridden by its only real caller). This client reads and displays whatever `currency` value the backend sends (correct, forward-compatible behavior) but does not claim genuine multi-currency support is exercised today — there is exactly one currency in the real data this sprint can observe. No tax field exists anywhere in this flow's responses; this sprint's UI states plainly that tax status is not specified by the backend rather than guessing "included" or "excluded."
