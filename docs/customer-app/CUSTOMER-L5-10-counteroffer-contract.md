# CUSTOMER-L5-10 — Counteroffer Contract

## There Is No Counteroffer Capability in This Backend

This document exists to satisfy the spec's required deliverable list
(§73) and to record, definitively, why no counteroffer feature was built.

**Exhaustive verification performed this sprint:**

1. `evaluate_customer_bargain`'s real decision type is
   `Literal["accepted", "rejected", "provider_approval_required"]`
   (`admin_catalog/bargain_engine.py:29`) — there is no `"counter"` value
   anywhere in this type, and the function's own if/elif/else decision
   logic (lines 176-187) has no branch that computes or returns a
   counteroffer amount.
2. `BargainRule.below_floor_action` (default `"reject"`) is a real column
   but is a free-form string with no validated enum, never read inside
   `evaluate_customer_bargain` at all, and used elsewhere only as
   stored/displayed/filtered admin metadata (`admin_catalog/service.py`
   lines 2438, 2499-2513, 2679, 2696; `admin_catalog/admin_router.py`
   lines 874, 880) — never as a behavioral branch that generates a
   counteroffer.
3. A repo-wide, case-insensitive grep for `BargainSession`, `BargainOffer`,
   `BargainAttempt`, `CounterOffer`/`Counteroffer`, `bargain_session`,
   `bargain_offer`, `bargain_attempt`, `counter_offer`, `negotiation`
   returns zero hits anywhere in `app/`.
4. Even the one function that *can* evaluate a raw customer-submitted
   amount (`evaluate_customer_bargain` with `customer_offer` provided) is
   confirmed dead code in every customer-reachable path — its only real
   caller with a non-`None` offer is an **admin-only** preview endpoint
   (`evaluate_bargain_preview`, `admin_catalog/admin_router.py`), gated by
   an admin-only permission.
5. **Decisive**: the entire manual-bargain-rule module (`BargainRule`'s
   raw-offer evaluation, `below_floor_action`, `provider_approval_required`,
   `max_attempts`) is feature-flagged off by default and was explicitly
   deactivated by product decision — `MANUAL_BARGAIN_RULES_ENABLED = False`
   in `app/core/feature_flags.py:15-22`, corroborated by a repo document,
   `MANUAL_BARGAIN_DEACTIVATION_FINAL_REPORT.md`.

## What This Means for the Spec's §23-25 (Counteroffer, Acceptance, Decline)

None of it is implemented. Building a counteroffer UI would mean
fabricating a negotiation experience — a fake "the provider countered
with ₹X" message — that this platform's real backend cannot produce. Per
this project's established, repeatedly-applied principle (see every prior
sprint's `known-gaps.md`), the honest response to an aspirational
capability with no real backend support is to document its absence
prominently, not to simulate it client-side.

## `provider_approval_required` — A Real, Adjacent Concept, Also Unreachable

`evaluate_customer_bargain` can return `"provider_approval_required"` as a
decision when a real numeric offer is evaluated — conceptually the
closest thing to "the provider needs to review this" in the whole
codebase. It is unreachable for the same reasons as above: never called
with a real customer offer from any customer-facing path, and gated
behind the deactivated feature flag. This sprint's `confirm-price-choice`
flow has no equivalent "pending provider approval" outcome — a tier
choice is confirmed immediately, synchronously, with no provider-side
review step.

## If a Future Sprint Re-Enables Manual Bargaining

Should `MANUAL_BARGAIN_RULES_ENABLED` be turned on and a real
counteroffer-capable endpoint be built against `evaluate_customer_bargain`,
this sprint's `BargainState`/`bargain-schema.ts` would need real,
additive extension (new states, new response fields) — not a retrofit of
fabricated states added speculatively today. This document exists so that
future work has an accurate record of exactly what was verified absent,
and why, rather than needing to re-derive it from scratch.
