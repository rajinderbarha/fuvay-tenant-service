# Slice 2F-26E Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

The four confirmed defects are repaired and proven repaired. The fresh
holdout then found two *new* classifier defects, so agreement is 19/24 and
the strict edit gate fails with zero canonical edits.

## Coverage and hash

`CURRENT_CANONICAL_COVERAGE`: **214 / 257**, 43 unprotected — unchanged.
Canonical hash `45244cd9540456db` before and after, byte-identical.
`mutation-enforcement-matrix.csv` likewise unchanged (`4c7c3bce02096a43`).

The deferred expansion to 214/259 remains **unapplied**.

## Quality gates

| # | Gate | Status |
|---|---|---|
| 1 | One unified resolved-authority model | **MET** |
| 2 | Runtime-extensible semantics affect real persona classification | **MET** — D-01 routes now TENANT_PROVIDER |
| 3 | Shared tenant-direction taxonomy frozen | **MET** — 12 values, defined once |
| 4 | Manual and tool use the same taxonomy | **MET** — N07 |
| 5 | `tenant_authority()` consistent with resolved guards | **MET** |
| 6 | mark-all-read asserts persona AND direction | **MET** — N06 |
| 7 | D-01…D-04 regression tests | **MET** |
| 8 | Avoidable abstentions removed | **MET** — 8/24 → 0/24 on the burned set |
| 9 | Unavoidable abstentions carry exact reason codes | **MET** |
| 10 | Burned-sample regressions pass | **MET** — 24/24 persona and direction |
| 11 | Every verifier blocker has an executed negative fixture | **MET** — 19/19 fire, clean state restores |
| 12 | Fresh holdout excludes all burned routes | **MET** — N19 |
| 13 | Manifest frozen before verdicts | **MET** — `aeeb3fe510bf9671` |
| 14 | Manual frozen before classifier | **MET** — `b02f35736a79eb3d` |
| 15 | ≥24 routes | **MET** — 24 |
| 16 | Required strata represented | **NOT MET** — see disclosures |
| 17 | Abstention contract followed | **MET** |
| 18 | Every non-abstained field agrees | **NOT MET** — 19/24 |
| 19 | Closed-module canaries pass | **MET** — N12, 6 canaries |
| 20 | Proposed routes reconfirmed | **MET** — recorded, `applied=NO` |
| 21-22 | Strict edit gate enforced; edits only after all gates | **MET** — gate failed, zero edits |
| 23-24 | Both CSVs recount identically; arithmetic exact | **MET** — both unchanged |
| 25 | No next module selected | **MET** |
| 26 | Security observations preserved, not overstated | **MET** — 12 new, all marked static-only |
| 27 | Inputs frozen during runs | **MET** |
| 28 | Exact failure/error identity reported | **MET** — 161 passed, 0 failed |
| 29 | Behavioural invariants pass | **MET** |
| 30 | Environment evidence consistent | **MET** |
| 31-38 | No app behaviour/role/permission/migration change; no merge; PartsRequest ServiceJob-only; readonly@ untouched; 144 unapplied; 2D canaries untouched; no frontend | **MET** — zero `app/` files modified |

Gates 16 and 18 unmet ⇒ blocked.

## What was achieved

**All four confirmed defects are repaired, and the repairs are proven by
fixtures that fail when reverted.**

- **D-01** — `plan/upgrade` and `terminate/confirm`, the two routes 2F-26D
  caught being called platform-admin, now classify as
  `TENANT_PROVIDER_MUTATION` with `PRINCIPAL_TENANT`. Admission is modelled
  (`STATIC_AND_RUNTIME_EXTENSIBLE`) rather than collapsed to a role set. The
  repair does **not** over-correct: `deposit/admin-adjust`, whose permission
  *is* in `ROLE_PERMISSIONS` with platform-admin roles, still classifies as
  `PLATFORM_ADMIN_MUTATION` — asserted by its own test.
- **D-02** — one record now feeds persona and direction. The decisive signal
  the old model discarded: `*_mutation` guards run the tenant read-only
  access_scope gate, which presupposes a tenant-side principal.
- **D-03** — one frozen 12-value taxonomy; `NO_TENANT_SCOPE` retired and
  asserted absent.
- **D-04** — burned-sample abstentions 8/24 → 0/24, every one traced to an
  *avoidable* cause (information the resolver already held). Remaining
  abstentions carry reason codes from a closed set.

**Burned-sample regression: 24/24 persona, 24/24 direction, 0 abstentions** —
development evidence only, and labelled as such everywhere. It is not used to
approve anything.

**The verifier now has 19 executed negative fixtures**, each forced to fail,
each naming its exact condition, with the clean state restored afterwards.
2F-26D's verifier asserted several conditions structurally; these are executed.

## Why still blocked

The fresh holdout found two genuine, previously unknown classifier defects:

1. **Alias-blind parameter scan** — `tid: uuid.UUID = Query(..., alias="tenant_id")`
   on `POST /v1/commerce/warranty/claims`. A client-supplied tenant the scan
   does not see because the parameter is not *named* `tenant_id`.
2. **Actor identity read as scope** — on
   `POST /v1/auth/staff/{user_id}/invite/resend`, `user.user_id` is the actor
   argument, not the scope; the classifier inferred self-scoping from it.

Neither is fixed here. Fixing a defect found *by* the holdout and re-running
that same holdout is the circular proof the mission forbids.

## Honest disclosures

- **Of the five disagreements, only two are real classifier defects.** One
  (`GET .../demand/forecast`) is a case where **the tool was right and I was
  wrong** — the GET genuinely persists a `DemandForecast` row. Two are
  capability-column granularity errors substantially mine. I am reporting the
  breakdown rather than either inflating the tool's fault or using "mostly my
  fault" to argue the gate should pass.
- **Gate 16 is not met.** The mission lists 24 required strata; the remaining
  mixed-persona population supports only 5 (`S01`, `S02`, `S08`, `S09`,
  `S10`). Strata such as trusted callback, internal branch, explicit deny and
  customer self-service have **no members** in the 99 remaining routes. The
  holdout is stratified over what exists; it cannot be stratified over what
  does not. Claiming those strata were covered would be false.
- **Not all 38 documents are produced.** Files describing a passing holdout,
  an applied expansion or a rebuilt queue would describe work that did not
  happen.
- **Both holdouts are now burned.** The next repair needs a third.
- **Burned-sample 24/24 is not evidence of correctness** — the classifier was
  tuned against it. Only the 19/24 figure is independent.
- **One of my own tests was wrong** and was fixed rather than weakened: it
  asserted no untracked `app/` files exist, which failed on two files carried
  from earlier work. It now compares against a recorded pre-existing set.

## Preserved

Zero application files modified; zero authorization behaviour changed; both
canonical CSVs byte-identical. Closed-module canaries pass (field_ops,
Package Commerce, customer_reviews, legacy review incl. 410, compliance).
Canonical roles only; no role, permission or migration added; no pipeline
merged; `PartsRequest` ServiceJob-only; `readonly@demo-ac-services.local`
untouched; Migration 144 unapplied; Slice-2D canaries untouched; no frontend
work.

## Stop condition

Stops at the Slice 2F-26E approval gate. No module selected, no authorization
implemented, no canonical change.

**Next slice:** repair the alias-blind parameter scan and the actor-versus-
scope conflation, then validate against a **third** freshly frozen holdout.
If the population cannot supply the required strata, that should be stated as
a permanent limitation of the mixed-persona set rather than worked around.
