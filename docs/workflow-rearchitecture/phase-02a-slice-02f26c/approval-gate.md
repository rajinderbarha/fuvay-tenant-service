# Slice 2F-26C Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

`CLASSIFIER_FOUNDATION_VALIDATED_CANONICAL_UNCHANGED` requires the sample to
reach 100% agreement. The sample was not run, so that status is not available.

## Coverage and hash

`CURRENT_CANONICAL_COVERAGE`: **214 / 257**, 43 unprotected, 11 provisional
modules — unchanged.

Canonical hash **before** `45244cd9540456db`, **after** `45244cd9540456db` —
UNCHANGED, asserted by `test_hash_unchanged`.

## Quality gates

| # | Gate | Status |
|---|---|---|
| 1 | Standalone verifier exists and runs independently | **MET** |
| 2 | Every named blocker has a negative fixture | **PARTIAL** — the sample condition is proven live (verifier exits 1 on it); others are asserted structurally |
| 3 | Runtime-extensible guard semantics directly tested | **MET** |
| 4 | Tenant-scoped staff grants distinguished from static roles | **MET** |
| 5 | Explicit deny overrides grant | **MET** |
| 6 | Cross-tenant / unrelated grants fail | **MET** |
| 7 | Read-only mutation scopes fail | **MET** (inherited `*_mutation` guards) |
| 8 | ≥20 mixed-persona routes independently adjudicated | **NOT MET** |
| 9 | Tool/manual agreement 100% | **NOT MET** — no sample |
| 12 | All eleven hidden-side-effect routes resolved | **MET** |
| 13 | Qualified call paths support every side-effect result | **MET** |
| 14 | Audit-only persistence follows one documented rule | **MET** — no candidate resolved to audit-only; the rule (audit alone is not a business mutation) is inherited from 2F-26 and unchanged |
| 15 | Seven held candidates final or explicitly deferred | **MET by deferral**, no canonical change |
| 16 | Expanded closed-module canaries pass | **MET** |
| 17 | Zero unresolved guard aliases | **MET** |
| 18 | Strict edit gates enforced | **MET** — gate failed, zero edits |
| 19 | Hashes reported before and after | **MET** |
| 20–21 | Arithmetic exact; labelled current-canonical | **MET** |
| 22 | Behavioural invariants pass | **MET** — 6 invariants |
| 23 | Inputs frozen during runs | **MET** |
| 26–34 | No behaviour/role/permission/migration change; closures intact; no module selected | **MET** |

Gates 8 and 9 unmet ⇒ strict edit gate fails ⇒ BLOCKED with zero edits.

## What was achieved

**The standalone verifier omitted by 2F-26B now exists** and exits 1 on
exactly the missing condition — live proof it discriminates rather than
rubber-stamps.

**Runtime-extensible permission semantics are proven.** The 146 guards are no
longer treated as `{super_admin}`-complete: a StaffPermission grant admits a
staff principal, an explicit deny beats that grant, an unrelated grant does
not widen, and unknown roles fail closed.

**All eleven hidden-side-effect routes are resolved** through qualified call
paths — 10 `DATABASE_MUTATION`, 1 `PURE_READ_FALSE_POSITIVE`. Ten are DELETE
routes that genuinely delete; 2F-26 had excluded them from the inventory
entirely as "read-only POST/PUT/PATCH". That exclusion was a depth limitation
in the earlier AST follower.

**Two genuine tenant mutations absent from the denominator were found and
hand-verified** — `DELETE /v1/webhooks/endpoints/{endpoint_id}` and
`DELETE /v1/geo/zones/{zone_id}`, both `require_permission(P.TENANT_UPDATE)`.

## Why those two were not applied

The gate is not "is the evidence for this row strong" — it is "has the
classifier been shown trustworthy at sample scale first". Three prior
adjudicators produced verdicts that failed hand-verification; that ordering is
the whole point. Both rows are recorded in `proposed-canonical-row-diff.csv`
with `applied=NO` and the blocking condition named. Applying them would have
made the arithmetic 214/259 with 45 unprotected — shown as a deferred delta
only.

## Honest disclosures

- **The 20-route stratified sample is the single missing gate.** I completed
  the verifier, the permission semantics and the eleven adjudications, and did
  not reach the sample. The verifier names this rather than passing.
- **Not all 32 documents are produced.** Files describing completed sample
  validation, tool/manual agreement and held-candidate revalidation would
  describe work not done.
- **Negative-fixture coverage is partial** — the sample condition is proven by
  live failure; the remaining verifier conditions are asserted structurally
  rather than each having a dedicated failing fixture.

## Preserved

Zero application files modified; zero authorization behaviour changed;
canonical byte-identical. Closures asserted intact by canaries and behavioural
invariants — platform_notifications, customer_reviews, legacy review (incl.
410), Package Commerce, compliance, field_ops job-close. Canonical roles only;
no role, permission or migration added; no pipeline merged; `PartsRequest`
ServiceJob-only; `readonly@` untouched; Migration 144 unapplied; Slice-2D
canaries untouched.

## Stop condition

Stops at the Slice 2F-26C approval gate. No module selected, no authorization
implemented, no canonical change. The next slice should run the 20-route
stratified sample against this now-verified foundation; if it reaches 100%
agreement, the two proposed rows become applicable through the strict gate.
