# Slice 2F-26 Approval Gate

## Final status

**APPLICATION_WIDE_MUTATION_INVENTORY_EXPANDED**

Genuine tenant/provider mutations were added to the denominator on exact
route-level evidence, so `EXPANDED` is the correct status rather than
`RECONCILED`.

## The finding

The prefix-based inventory identified tenant routes by
`/v1/tenant|provider|staff`. Slice 2F-25 showed that misses real capabilities.
Rebuilding from persona, capability and side-effect evidence shows the blind
spot was **eight times larger** than the `/v1/reviews` case that exposed it:

**28 further tenant/provider mutations had never been counted. 26 are
unprotected.**

| | before | after |
|---|---|---|
| denominator | 229 | **257** |
| numerator | 212 | **214** |
| unprotected | 17 | **43** |
| modules queued | 7 | **11** |

The largest new module is `app.engines.auth.router` (12 routes): MFA
confirm/disable, password change, staff invite, **staff permission updates**,
staff deactivate, impersonation, API-key create/revoke/patch. Credential- and
permission-mutating surfaces that a prefix sweep never looked at.

## Evidence discipline

- **Two-source rule.** No route entered the denominator without BOTH a
  tenant-derivation expression and a persistent side effect, recorded per row
  in `canonical-row-diff.csv` and asserted by
  `test_every_addition_carries_two_source_evidence`. 7 single-signal
  candidates were **held**, not added.
- **Zero removals.** 55 canonical rows disagreed with the automated
  classifier; adjudication attributes this to indirect tenant derivation and
  service-layer delegation, not to absent capabilities. Workstream 6 forbids
  removal without exact evidence.
- **Persona never from prefix.** Classification uses the authoritative tenant
  source and the dependency chain.

## Quality gates

Every mounted route (2299) exported and behaviour-classified; no
`UNKNOWN_BEHAVIOR`; every mutation has a persona; 31 mutating GETs and 145
read-only POST/PUT/PATCH identified; every canonical row resolves to a mounted
route; every confirmed tenant mutation has a canonical row; no duplicate keys;
no `UNKNOWN_PROTECTION`/`UNVERIFIED`; protected + unprotected == denominator;
queue accounts for all 43 routes once; verifier exits zero with negative
fixtures proving it can fail; no module selected.

## Regression

Zero new failing node IDs, zero new error node IDs, run twice with identical
results under a stable measured environment. +43 passed reconciles exactly
(42 new tests + 1 widened assertion).

## Honest disclosures

- **My pre-slice baseline was contaminated by my own concurrent write** to the
  canonical CSV and was discarded; 2F-25A run 2 used instead. A background
  baseline is only valid if shared state stays frozen for its whole duration.
- **Four bugs in my own tooling**, each fixed before any result was trusted:
  an empty route walk (FastAPI wrapper nesting) that would have read as "no
  routes found"; a prefix-based persona rule that disagreed with 149 of 229
  canonical rows; an audit/external marker overlap that made pure reads look
  like mutations; and cross-engine method-name collisions in AST following.
  Plus a path-form normalization fix without which the denominator would have
  moved wrongly in both directions.
- **I was wrong about a route my tooling flagged.** I suspected
  `GET /v1/commerce/.../deposit` was a false positive; it lazily creates a row
  via `_get_or_create_deposit`. A genuine mutating GET.
- **257 is still not a proven-complete figure.** 123 MIXED_PERSONA mutations
  remain unadjudicated and could contain tenant capabilities. Confidence is
  much higher than the prefix-based 229, but the denominator can still move.
- **Protection status for the 28 additions reflects declared guards only** —
  no object-ownership or state-integrity audit was performed on them.

## Preserved

No application file modified; no authorization behaviour changed (asserted by
behavioural invariants, not inferred from a clean diff). All prior closures
intact — field_ops, Booking, quote-checklist, invoice-lineage,
platform-notifications, compliance, Package Commerce, customer_reviews, legacy
review engine, legacy `POST /v1/reviews` 410. Canonical roles only; no role,
permission or migration added; no pipeline merged; `PartsRequest`
ServiceJob-only; `readonly@` untouched; Migration 144 unapplied; Slice-2D
canaries untouched.

## Stop condition

Stops at the Slice 2F-26 approval gate. **No next module was selected** and no
authorization was implemented — 26 newly discovered unprotected routes raise
the denominator only. 11 modules / 43 routes now await selection.
