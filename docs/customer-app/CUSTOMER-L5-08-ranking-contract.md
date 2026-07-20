# CUSTOMER-L5-08 — Ranking Contract

## Real Ranking Is Entirely Server-Side and Opaque to the Customer

`compute_provider_score()` (matching_engine.py:107-119) computes a weighted
sum across 8 signals for every eligible candidate; `rank_candidates()` /
`select_best_candidate()` (lines 122-133) pick the single highest-scoring
one. None of this — not the score, not the sub-scores, not the weights, not
the candidate count among eligible providers — is ever returned to the
customer (`reveal_internal_score=False` is hardcoded in the customer
router). This is a deliberate backend design choice (the router's own
docstring: "the customer never sees or picks from a list"), not a gap this
client works around.

## What This Client Can and Cannot Show

| Aspirational UI element | Real backend support | This sprint's behavior |
|---|---|---|
| "Why this provider" reasoning | One fixed sentence, identical for every match | Rendered verbatim as the real `customer_visible_reason` — not treated as if it were dynamic/personalized. |
| Ranking position ("#1 of 5 matched") | Candidate count exists internally (`candidate_count`/`excluded_count`) but only inside the *no-match* failure path's internal return value — never forwarded into the success response or the HTTP error body | Not shown. There is no real data path to a ranking position on a successful match. |
| Score/quality breakdown | `internal_score_breakdown` (8 named sub-scores) exists but only when `reveal_internal_score=True`, which the customer router never sets | Not shown — structurally absent from every response this client can ever receive. |
| Comparison to runner-up providers | Does not exist at all — no runner-up is retained or returned anywhere | Not shown. |

## Weighting Reference (documented for completeness; never exposed to the customer)

`matching_engine.py:60-88` defines named weight constants (e.g.
`WEIGHT_DISTANCE = 0.10`) combined in `compute_provider_score()`. This
client does not read, mirror, or attempt to reconstruct this formula
client-side anywhere — the customer-safe object never contains enough
information to do so, and this sprint does not fabricate a plausible-looking
score to fill that gap.
