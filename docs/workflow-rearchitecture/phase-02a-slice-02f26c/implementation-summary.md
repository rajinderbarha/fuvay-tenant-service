# Implementation Summary — Slice 2F-26C

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

Coverage remains **214 / 257**, 43 unprotected, 11 provisional modules.
Canonical hash **`45244cd9540456db`** before and after — unchanged, asserted by
test. Zero canonical edits, zero application files modified.

## What this slice completed

### 1. Standalone foundation verifier — BUILT (the 2F-26B omission)

`scripts/workflow_rearchitecture/verify_foundation_2f26c.py`, independently
executable with a `__main__` entry point, checking guard resolution, tenant
authority direction, runtime-extensible permission semantics, mixed-persona
non-finalization, the eleven candidates, sample size and agreement, canonical
freeze, and documentation honesty.

**It currently exits 1** — on exactly one condition: the validation sample was
not run. That is live proof of discrimination, not a defect.

### 2. Runtime-extensible permission semantics — PROVEN

The 146 guards whose permission is absent from `ROLE_PERMISSIONS` are now
modelled correctly. All seven required cases pass:

| Case | Result |
|---|---|
| super_admin admitted statically | PASS |
| staff **without** override denied | PASS |
| staff **with** matching grant admitted | PASS |
| explicit deny overrides grant | PASS |
| unrelated grant does not widen | PASS |
| unknown role fails closed | PASS |
| runtime-extensible guard NOT treated as statically super-admin-only | PASS |

`{super_admin}` is confirmed **not** their complete admitted set: a
StaffPermission override admits a staff principal at runtime, and an explicit
deny beats a grant.

### 3. All eleven hidden-side-effect routes — FULLY ADJUDICATED

Each traced through a **qualified** call path: service class from the
parameter annotation or module import, bound method resolved on that exact
class, body inspected for real writes. No unqualified name matching.

| Behaviour | Count |
|---|---|
| DATABASE_MUTATION | 10 |
| PURE_READ_FALSE_POSITIVE | 1 (`POST /v1/public/register/verify`) |

| Persona | Count |
|---|---|
| PLATFORM_ADMIN_MUTATION | 5 |
| TENANT_PROVIDER_MUTATION | 4 |
| PUBLIC_OR_UNAUTHENTICATED_MUTATION | 1 |
| PRODUCT_DECISION_REQUIRED | 1 (`DELETE /v1/chat/messages/{message_id}`) |

**Finding:** these were classified "read-only POST/PUT/PATCH" by 2F-26 and
excluded from the inventory entirely. Ten of them are DELETE routes that
genuinely delete. The exclusion was a depth limitation in the earlier AST
follower, not a property of the routes.

Of the four tenant routes, **two are already in the canonical CSV**
(checklist-templates) and **two are not**:

- `DELETE /v1/webhooks/endpoints/{endpoint_id}` — `require_permission(P.TENANT_UPDATE)`
- `DELETE /v1/geo/zones/{zone_id}` — `require_permission(P.TENANT_UPDATE)`

Both hand-verified by reading the router source. They are genuine tenant
mutations missing from the denominator.

### 4. Closed-module canaries — expanded and passing

platform_notifications, customer_reviews, legacy review, Package Commerce,
compliance, field_ops and the legacy 410 all assert unchanged.

## Why still BLOCKED, and why nothing was applied

The strict edit gate (WS9) requires **all twelve** conditions, including
WS9.7: a 20-route stratified sample at 100% tool/manual agreement.

That sample was **not run**. One unmet condition ⇒ zero canonical edits ⇒
`GLOBAL_COVERAGE_RECONCILIATION_BLOCKED`, hash preserved.

The two proposed additions are therefore recorded in
`proposed-canonical-row-diff.csv` with `applied=NO` and the reason, not
merged. Had they been applied the arithmetic would be 214/259 with 45
unprotected; that is shown as a deferred delta only.

This is the gate working as designed. The evidence for those two rows is
strong — qualified call path plus hand verification — but "strong evidence for
this row" is not the gate; the gate is "the classifier has been shown
trustworthy at sample scale first". After three prior adjudicators produced
verdicts that failed hand-verification, that ordering is the point.

## Honest disclosures

- **The 20-route sample is the single missing gate.** I built the verifier,
  the permission semantics and the eleven adjudications, and ran out of scope
  before the stratified sample. The verifier names this precisely rather than
  passing.
- **Not all 32 documents are produced.** Files describing completed sample
  validation, tool/manual agreement and held-candidate revalidation would
  describe work not done. The artifacts that are real are listed below.
- **The seven held candidates were not revalidated** this slice — permitted by
  WS7 as an explicit deferral, and they cause no canonical change.

## Real artifacts

`hidden-side-effect-route-adjudication.csv` (11 rows),
`hidden-side-effect-qualified-call-graph.csv`,
`proposed-canonical-row-diff.csv` (2 rows, not applied),
`canonical-coverage-arithmetic.csv`,
`closed-module-classification-canaries.csv`, plus
`verify_foundation_2f26c.py` and 23 passing tests.
