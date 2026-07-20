# CUSTOMER-L5-08 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-07 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 516 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Real booking draft exists: confirmed (`HomeServiceBookingDraft`, L5-06).
4. Draft restoration: confirmed working.
5. Draft versioning: **confirmed absent**, unchanged finding from L5-06.
6. Selected service canonical: confirmed (`MasterService`-space IDs throughout the draft flow since L5-06).
7. Selected service type canonical: confirmed (`offering_type_id`, synced from the L5-05 assistant per L5-06's documented naming assumption).
8. Brand/option answers canonical: confirmed for brand (`brand_id`); option IDs are **not** synced to the draft (unchanged L5-06 finding — the `PUT` endpoint never accepted `service_option_ids_json`).
9. Address valid/customer-owned: confirmed (L5-07, real `CustomerAddress` CRUD, ownership-enforced).
10. Serviceability backend-confirmed: confirmed (L5-07, real `HomeServiceServiceabilityService.check`).
11. Zone/city tier canonical: **confirmed not part of this flow at all** — unchanged L5-07 finding; the real serviceability check never resolves either.
12. Selected SLA valid/unexpired: **not applicable** — L5-07 already established there is no real SLA-option capability; only a free-text `preferred_time_window` exists.
13. Draft serviceability state: confirmed present (`serviceability_status`).
14. Tenant service-area records: confirmed real and understood (`TenantServiceArea`, `TenantServiceAreaService`).
15. Enabled-offering records: confirmed real (`provider_enabled_offerings` table, referenced in `get_area_market_comparison`'s SQL — see contract-matrix.md).
16. Matching engine endpoints: identified — **exactly one real endpoint** (`POST /{draftId}/match-and-price`); a separate list-based flow exists but is explicitly deprecated.
17. Availability/capacity sources: identified — folded into a single canonical `is_bookable` gate (`provider_visibility_statuses`), not a separate customer-visible availability state.
18. Provider health/badge sources: identified — `tenants.health_score` (internal only) and a small, server-computed `public_badges: string[]` list (real, but a closed set of exactly 3 possible literal English strings).
19. No fake provider data in production paths: confirmed — the app has no matching code at all before this sprint.
20. Customer-specific cache clears on logout: confirmed pattern (CUSTOMER-L5-02, unmodified) will cover this sprint's additions too.
21. Existing tests pass: confirmed — 516/516 at sprint start.
22. Working tree: understood — unrelated changes in other engines/frontends from parallel work streams, none touched.

## Existing Implementation Found

- **Matching implementation**: none in the mobile app.
- **Provider representation**: confirmed `Provider = Tenant` — no separate `ProviderCompany`/`ProviderZone` model exists anywhere; the customer-facing "provider" is always a `tenant_id` + `provider_name`.
- **Provider preview**: none built yet; the reserved route `providerPreview` exists (`route-registry.ts`, dev-only placeholder) awaiting this sprint.
- **Ranking implementation**: real, but entirely server-side and never exposes its inputs — the customer-facing API returns exactly one selected provider plus a single fixed explanation sentence, never a ranked list or per-candidate scores.
- **Availability implementation**: none customer-visible — availability is one of eight internal scoring signals folded into eligibility, never surfaced as a discrete customer-facing state.
- **Provider-health integration**: `health_score` exists but is internal-only (never returned by the customer-facing API) — it only influences eligibility and the internal ranking score, and indirectly contributes to the real, coarse `"High Completion"` badge threshold.
- **Badge integration**: real, server-computed, exactly 3 possible values (`"Verified"`, `"Highly Rated"`, `"High Completion"`) — all literal, untranslated English strings requiring client-side localized-label mapping.
- **Placeholder/fake behavior found**: none — no prior sprint fabricated any provider data.

## Real Backend Contract — Central Findings

1. **There is exactly one real, production matching endpoint**:
   `POST /v1/customer/home-services/booking-drafts/{id}/match-and-price` —
   its own docstring explicitly states it is "Provider-First Matching":
   the backend evaluates every eligible Tenant, scores them across 8
   signals, and **auto-selects exactly one** — the customer never sees or
   picks from a list. The list-based alternative
   (`POST .../match-providers`, `POST .../select-provider`) is explicitly
   marked `[DEPRECATED]` in the router with the comment "do not build new
   customer UI against this." This resolves CUSTOMER-L5-08 §26's central
   open question decisively: the real product policy is `AUTO_MATCH`, not
   `CUSTOMER_SELECTS`.
2. **The real endpoint conflates matching and pricing in one call.** Its
   response contains `selected_provider` (customer-safe matching result),
   `selected_provider_price_options` (Low/Mid/High pricing — CUSTOMER-L5-09's
   scope), and `area_market_comparison` (a competitor price comparison —
   also pricing). This sprint calls the real endpoint (there is no
   matching-only variant) but its UI renders **only** the `selected_provider`
   block, never the pricing fields — an explicit, disclosed scope
   boundary, not an oversight.
3. **The customer-safe provider object is minimal**: `{tenant_id,
   provider_name, public_badges: string[], rating: number|null,
   customer_visible_reason: string}` — five fields total. No logo, no
   cover image, no service-area summary, no availability state, no
   earliest-available time, no distance, no review count, no years-active,
   no completed-jobs count, no supported-brands list, no health summary.
   None of these are fabricated to fill out a richer preview than the
   backend actually provides.
4. **`customer_visible_reason` is a single, fixed sentence** — not a set
   of dynamic, per-candidate explanation codes. Every matched provider
   gets the identical string: *"Best matched provider based on service
   coverage, availability, quality, and completion history."*
5. **`public_badges` is a closed, 3-value set**, computed server-side from
   real data (`"Verified"` always present for any eligible match;
   `"Highly Rated"` if `rating >= 4.5`; `"High Completion"` if
   `health_score >= 90`) — but returned as literal, untranslated English
   strings with no stable badge ID, no icon reference, no validity dates.
   This sprint maps these three known strings to localized labels
   client-side; an unrecognized future string fails safe (renders as-is,
   logged as unsupported).
6. **No match session, match ID, expiry, or polling exists.** The call is
   a single synchronous request/response — calling it again simply
   re-runs the full evaluation fresh. There is no async "queued/matching/
   partial results" lifecycle to model.
7. **No-match is a single generic error** (`HOME_BOOKING_NO_PROVIDER_AVAILABLE`,
   "No eligible providers available in {city}. Try a nearby city."), not
   the aspirational taxonomy of `NO_PROVIDER_FOR_SLA`/`NO_PROVIDER_FOR_BRAND`/
   etc. A second, distinct error (`PRICE_OPTIONS_UNAVAILABLE`) can occur
   when a provider is found but has no price configuration — from this
   sprint's perspective both are treated as an honest "couldn't find a
   match right now" outcome, since this sprint cannot distinguish "found
   a provider, pricing broken" from "found no provider" without exposing
   pricing internals it doesn't own.
8. **The draft is updated by the same call** — `selected_tenant_id`,
   `selected_provider_snapshot`, `price_snapshot.price_options`,
   `provider_match_status = "matched"`, `status = "provider_matched"` are
   all written server-side atomically. There is no separate "confirm
   selection" step for this sprint to build (that step, `confirm-price-choice`,
   belongs to CUSTOMER-L5-09 since it deals with the price tier).

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code.

## Deferred Issues

See `CUSTOMER-L5-08-known-gaps.md`.
