# Route Denominator Reconciliation — Slice 2F-39A4

| Metric | After 2F-39A3 | After 2F-39A4 |
|---|---|---|
| Unresolved route-method records (unclassified) | 0 | 0 (unchanged — this slice resolves depth, not volume) |
| `PRODUCT_DECISION_REQUIRED` (verification-depth backlog) | 21 | **5** |
| Confirmed authorization defects found and fixed this slice | 0 (2F-39A3 fixed 2, different routes) | **9** |
| N01 standing blocker rows (separate, unchanged) | 3 (counted within the 21) | 3 (still separate, not counted within the 5) |
| Routes verified safe (no fix needed, compensating check confirmed) | — | 4 |

## What "261/261 classified; 0 unclassified" still means

Unchanged from 2F-39A3: every one of the 261 originally-unresolved routes
has exactly one final classification. This slice did not touch that count —
it worked entirely within the 21 `PRODUCT_DECISION_REQUIRED` rows, which
were already classified (correctly) as needing further verification before
any safety claim.

## What changed

Of the 21: **9 confirmed real defects, now fixed. 4 confirmed safe** (no
code change — a compensating check already existed, matching the
`rotate_api_key` precedent). **3 remain N01 territory**, untouched by
design. **5 remain genuinely unresolved**, each with a complete
reviewer-bar-compliant evidence record in `known-limitations.md`, pending
an explicit human product/caller-model decision — not guessed at.
