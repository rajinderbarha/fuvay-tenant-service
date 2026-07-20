# CUSTOMER-L5-10 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-09 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 550 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Real booking draft exists: confirmed.
4. Draft restoration: confirmed working.
5. Draft versioning: **confirmed absent**, unchanged finding since L5-06 — no `version`/`revision` counter anywhere on the draft.
6. Selected provider/match valid: confirmed (`draft.selected_tenant_id`, `provider_match_status`, from L5-08).
7. Selected SLA valid: still not applicable — unchanged from L5-07 (only free-text `preferred_time_window`).
8. Pricing estimate valid: confirmed (L5-09's `price_snapshot.price_options`, real Low/Mid/High from `match-and-price`).
9. Estimate revision current: **still not applicable** — unchanged L5-09 finding, no revision counter exists anywhere in the real pricing data.
10. Estimate not expired: **still not applicable** — unchanged L5-09 finding, no price-specific TTL exists; only the generic 24h draft `expires_at`.
11. Currency canonical: confirmed hardcoded `"INR"` server-side, unchanged from L5-09.
12. Bargain eligibility backend-sourced: **re-verified and reconfirmed absent** — no `bargain_allowed`/eligibility field is ever returned to the customer anywhere in this flow (unchanged L5-09 finding, now further confirmed: see Central Findings below).
13. Internal bargain floor not exposed: confirmed both by contract (never returned) and by this sprint's own new code (never parsed/rendered).
14. Bargain engine endpoints identified: **exactly one real endpoint** — `POST /{draftId}/confirm-price-choice`, tier-choice only (`"low"|"mid"|"high"`), documented exhaustively in L5-09's contract-matrix.md and re-confirmed here.
15. Attempt/rate-limit rules identified: **confirmed to not exist** for this endpoint or anywhere in this engine — no rate-limit middleware, no attempt-count field, no cooldown field found anywhere in `home_service_booking`.
16. Bargain-session model identified: **confirmed to not exist** — exhaustive repo-wide grep for `BargainSession`/`BargainOffer`/`BargainAttempt`/`CounterOffer`/`bargain_session`/`counter_offer` (case-insensitive) returns zero hits anywhere in `app/`.
17. Counteroffer behavior identified: **confirmed to not exist** — `evaluate_customer_bargain`'s real decision set is exactly `"accepted" | "rejected" | "provider_approval_required"` (`admin_catalog/bargain_engine.py:29`) — no `"counter"` decision exists in the function's logic. `BargainRule.below_floor_action` is a real column (default `"reject"`) but is confirmed to be pure stored metadata — never branched on by any code path anywhere (verified: every reference is either the column definition, a create/update payload field, or an admin list-filter parameter; none is an `if below_floor_action == ...` behavioral branch).
18. Negotiated-price persistence identified: confirmed — `confirm_price_choice` writes into `draft.booking_summary` (`selected_price_tier`, `customer_offer`, `allowed_offer_min/max`, `platform_fee_amount`, `payment_mode`) — there is no separate `negotiated_price` table/record; the "negotiated price" **is** the tier-derived amount stored in this JSON blob.
19. Audit events identified: confirmed — `EVENT_PRICE_ESTIMATED` (`actor_type=ACTOR_CUSTOMER`) is emitted on every `confirm_price_choice` call, real and already wired.
20. No fake bargaining in production paths: confirmed — no bargain UI exists anywhere in the mobile app before this sprint.
21. No client-side floor calculation controls behavior: confirmed by design — this sprint never computes or infers a floor; it only ever submits a tier name.
22. Existing tests pass: confirmed — 550/550 at sprint start.
23. Working tree: understood — unrelated parallel work in other engines/frontends, none touched.
24. No unrelated changes overwritten: confirmed.

## Existing Bargain Implementation Found

None in the mobile app. `features/pricing/` (L5-09) renders Low/Mid/High but never calls `confirm-price-choice`; its own contract-matrix.md already fully documented that endpoint's contract "for CUSTOMER-L5-10's benefit."

## Central Findings — Real Bargain Capability Is Far Smaller Than the Spec's Aspirational Model

This sprint's mandatory-first-action research (a direct, exhaustive
repo-wide investigation, cross-checked by an independent background
research pass) establishes with high confidence:

1. **There is no bargain-session model, no counteroffer model, no
   offer-attempt model, and no bargain-specific rate-limit/cooldown
   mechanism anywhere in this backend.** The platform's entire real
   "negotiation" capability is: the customer picks one of three
   backend-computed tiers (`low`/`mid`/`high`) via
   `confirm-price-choice`, and the backend resolves and stores the exact
   corresponding amount. There is no free-text/custom-amount offer input
   anywhere the customer can reach, no multi-round negotiation, and no
   provider-generated counteroffer capability.
2. **`evaluate_customer_bargain`** (`admin_catalog/bargain_engine.py`),
   the one function in this codebase that *can* evaluate a raw numeric
   customer offer against a floor and produce `"accepted"`/`"rejected"`/
   `"provider_approval_required"`, is real and fully implemented — but is
   confirmed dead code in every customer-reachable path (only used
   internally by `compute_price_tiers` with `customer_offer=None`, purely
   for its range-validation side effect; its only real caller with a
   non-`None` offer is an **admin-only** preview endpoint,
   `evaluate_bargain_preview` in `admin_catalog/admin_router.py`).
3. **Consequence, stated plainly**: this sprint honestly implements the
   real capability — a structured tier-choice screen calling
   `confirm-price-choice` — and does **not** build a custom-offer input,
   counteroffer UI, attempt counter, cooldown timer, or rate-limit
   handling, because none of those have any real backend behavior to
   render. Building them would mean fabricating a negotiation experience
   this platform does not actually have. This is documented exhaustively
   in `CUSTOMER-L5-10-contract-matrix.md` and `known-gaps.md`.
4. **`confirm-price-choice` is safely re-callable.** No guard prevents
   calling it a second time with a different tier — each call simply
   merges a fresh `selected_price_tier`/`customer_offer` into
   `draft.booking_summary`. This sprint uses this real behavior as the
   honest equivalent of "revise your choice" — the customer can change
   their tier pick freely before continuing, with the backend as the sole
   source of truth for the resulting amount each time.
5. **The real request body is unvalidated raw JSON** — a missing
   `price_tier` key raises an unhandled `KeyError` server-side rather
   than a clean 422 (already flagged in L5-09's known-gaps.md for this
   sprint's benefit). This client always sends a well-formed body, so
   this gap is not triggered by any real user action, but is documented
   again here since this is the sprint that actually calls the endpoint.
6. **The real "booking review boundary" precondition** is
   `draft.booking_summary.selected_price_tier` (written by
   `confirm-price-choice`) — `build_booking_summary`'s (`/summary`
   endpoint, CUSTOMER-L5-11 scope) `ready_for_confirmation` flag requires
   exactly this field to be one of `"low"|"mid"|"high"`. This sprint does
   not call `/summary` (out of scope), but its own screen's "Continue"
   action is gated on having just received a successful
   `confirm-price-choice` response, which is the same real precondition.

## Cross-Check: Independent Research Pass — Fully Confirmed, One Decisive New Fact

An independent background research pass reached identical conclusions on
every point above, and additionally surfaced the decisive, final piece of
evidence: **the entire manual-bargain-rule module is feature-flagged OFF
by default and was explicitly product-deactivated.**
`app/core/feature_flags.py:15-22`:
```python
MANUAL_BARGAIN_RULES_ENABLED = "manual_bargain_rules_enabled"
AUTO_PRICE_OPTIONS_ENABLED = "auto_price_options_enabled"
PROVIDER_FIRST_MATCHING_ENABLED = "provider_first_matching_enabled"

DEFAULT_FLAGS = {
    MANUAL_BARGAIN_RULES_ENABLED: False,
    AUTO_PRICE_OPTIONS_ENABLED: True,
    PROVIDER_FIRST_MATCHING_ENABLED: True,
}
```
A repo document, `MANUAL_BARGAIN_DEACTIVATION_FINAL_REPORT.md`, records
this as a deliberate product decision, not an oversight. This removes any
remaining ambiguity: this platform's real, live, product-intended pricing
model for Home Services is `AUTO_PRICE_OPTIONS_ENABLED` +
`PROVIDER_FIRST_MATCHING_ENABLED` (both `True` by default) — i.e., exactly
the `match-and-price` → `confirm-price-choice` tier-pick flow this sprint
implements — while the raw-offer/floor/`below_floor_action`/counteroffer
machinery in `bargain_engine.py`/`BargainRule` belongs to the deactivated
`MANUAL_BARGAIN_RULES_ENABLED` module. Building a counteroffer/attempt-limit/
rate-limit UI against that module would mean building a customer-facing
frontend for a backend capability its own product owners have turned off.

Also newly confirmed: `rate_limiter` (`app/core/security.py:44-61`) has a
real, scoped `RATE_LIMITS` table covering only `auth:*`/`api:*`/
`webhook:delivery` keys — `home_service_booking` is not among them, and
`customer_router.py`'s `confirm_price_choice` route has no `rate_limiter`
dependency at all. No app-wide rate-limit middleware exists in
`app/main.py` either. This is not a gap in this specific endpoint — it is
confirmation that no rate-limiting concept applies to this flow anywhere.

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code. `ProviderPreviewScreen`'s (L5-08) and
`PricingEstimateScreen`'s (L5-09) navigation targets are unchanged by this
sprint — `PricingEstimateScreen`'s existing "Continue" button already
targets the `bookingReview` route name via... **correction**: it currently
targets `BookingReview` directly (per L5-09's code), meaning L5-09 did not
route through a dedicated bargain stage at all. This sprint inserts the
real bargain screen between them — see `pricing-architecture` note in
`CUSTOMER-L5-10-bargain-architecture.md` for the exact navigation change
this requires (an intentional planned insertion, not a defect).

## Deferred Issues

See `CUSTOMER-L5-10-known-gaps.md`.
