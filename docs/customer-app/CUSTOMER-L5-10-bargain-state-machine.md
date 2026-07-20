# CUSTOMER-L5-10 — Bargain State Machine

## States (`domain/bargain-state.ts`)

| State | Meaning | Real trigger |
|---|---|---|
| `preflight_failed` | A real precondition (reused from CUSTOMER-L5-09's `evaluatePricingPreflight`) is unmet | Draft missing/expired, no address, not serviceable, no provider matched |
| `loading_estimate` | Fetching a fresh Low/Mid/High via `match-and-price` | Screen mount, or an explicit "Try again" after `estimate_unavailable` |
| `estimate_unavailable` | The real `match-and-price` call failed | `HOME_BOOKING_NO_PROVIDER_AVAILABLE`/`PRICE_OPTIONS_UNAVAILABLE`/network/schema-validation failure (same generic-unavailable handling as CUSTOMER-L5-09) |
| `choosing` | Three real tiers are on screen, no choice submitted yet | Estimate loaded successfully, no `confirm-price-choice` call in flight or completed |
| `confirming` | A specific tier's `confirm-price-choice` call is in flight | Customer tapped "Choose" on one tier |
| `confirmed` | The real, backend-resolved `booking_summary` was returned | `confirm-price-choice` succeeded |
| `confirm_failed` | The `confirm-price-choice` call errored | Network/validation failure on submission — the customer can retry by choosing again |

## Deliberately Absent States (and why)

Per the spec's aspirational model (§12), the following states are **not**
part of this union: `CHECKING_ELIGIBILITY`, `NOT_ELIGIBLE`,
`CREATING_SESSION`, `EDITING_OFFER`, `SUBMITTING_OFFER` (distinct from
`confirming`), `OFFER_ACCEPTED`/`OFFER_REJECTED` (distinct from
`confirmed`/`confirm_failed`), `COUNTEROFFER_RECEIVED`,
`ACCEPTING_COUNTEROFFER`, `NEGOTIATED` (distinct from `confirmed`),
`RATE_LIMITED`, `ATTEMPTS_EXHAUSTED`, `EXPIRED`, `INVALIDATED`,
`CANCELLING`, `CANCELLED`. Every one of these corresponds to a backend
capability (eligibility gate, session, counteroffer, attempt limit, rate
limit, bargain-specific expiry/invalidation, cancellation) that this
sprint's exhaustive research (`contract-matrix.md`) confirmed does not
exist. Modeling a state for a capability that cannot occur would mean
either (a) the state is permanently unreachable dead code, or (b) it gets
reached by inference/fabrication rather than a real backend signal —
neither is acceptable per this project's established honesty discipline
(the same principle CUSTOMER-L5-09's state model already applied when it
omitted `CONFLICT`/`EXPIRED`).

## Transition Diagram (real transitions only)

```
preflight_failed ──(precondition becomes met)──> loading_estimate
loading_estimate ──(match-and-price succeeds)──> choosing
loading_estimate ──(match-and-price fails)─────> estimate_unavailable
estimate_unavailable ──(Try again)─────────────> loading_estimate
choosing ──(Choose a tier)─────────────────────> confirming
confirming ──(confirm-price-choice succeeds)───> confirmed
confirming ──(confirm-price-choice fails)──────> confirm_failed
confirm_failed ──(Choose a tier again)─────────> confirming
confirmed ──(Change selection)─────────────────> choosing
```

## Pure, Testable Derivation

`deriveBargainState()` (`domain/bargain-state.ts`) is a pure function over
three plain snapshots (`preflightReasonKey`, an estimate-mutation
snapshot, a confirm-mutation snapshot, and the locally-tracked
`selectedTier`) — it takes no React Query objects directly, so it is
directly unit-testable without mounting any hook or component (mirrors
CUSTOMER-L5-09's `derivePricingState` exactly). `use-bargain.ts` is a thin
wiring layer that feeds real `useMutation` snapshots into this function
and exposes `chooseTier`/`changeSelection`/`refreshEstimate` actions.
