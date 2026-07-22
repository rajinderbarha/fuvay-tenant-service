# Slice 2F-26F Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

D-05 and D-06 are repaired and proven repaired. The third holdout reached
21/24 against a required 24/24, so the strict edit gate fails with zero
canonical edits.

## Coverage and hashes

`CURRENT_CANONICAL_COVERAGE`: **214 / 257**, 43 unprotected — unchanged.

| File | Before | After |
|---|---|---|
| `tenant-mutation-endpoint-inventory.csv` | `45244cd9540456db` | `45244cd9540456db` |
| `mutation-enforcement-matrix.csv` | `4c7c3bce02096a43` | `4c7c3bce02096a43` |

The deferred 214/259 position remains **unapplied**.

## Result

| Field | Agreement |
|---|---|
| Persona | **24/24** |
| Tenant direction | **24/24** |
| Capability action | **24/24** |
| Abstention reason | **24/24** |
| Side effect | 23/24 |
| Capability family | 22/24 |
| **All six** | **21/24** |

Across three independent holdouts: **4/24 → 19/24 → 21/24**.

## Quality gates

| # | Gate | Status |
|---|---|---|
| 1-2 | FastAPI/Pydantic aliases normalized; symbol and external name both retained | **MET** |
| 3-5 | Actor/target/scope distinct; actor-only cannot establish ownership; predicates explicit | **MET** |
| 6 | D-05 and D-06 regression tests | **MET** |
| 7-8 | One frozen capability taxonomy, used by manual and tool | **MET** |
| 9 | Manual evidence review mandatory | **MET** — 24/24 PASS, separate artifact |
| 10 | Both burned corpora pass as development regressions | **MET** — 24/24 and 24/24 |
| 11 | Eligible-population arithmetic exact | **MET** — 123−48=75, all mounted |
| 12 | Strata reflect actual availability | **MET** — 4 declared not representable |
| 13 | Behavioural cases tested separately from route strata | **MET** |
| 14 | Third holdout disjoint from both burned sets | **MET** — N19, N28 |
| 15-16 | Manifest, manual and evidence review frozen before classifier | **MET** |
| 17 | ≥24 routes | **MET** — 24 |
| 18 | Normalized comparison contract | **MET** |
| 19 | Every required non-abstained field agrees | **NOT MET** — 21/24 |
| 20 | Zero avoidable abstentions | **MET** — N31 |
| 21 | Every verifier blocker has an executed failing fixture | **MET** — 33/33 fire, clean state restores |
| 22 | Closed-module canaries pass | **MET** |
| 23 | Both proposed routes reconfirmed | **MET** — recorded UNPROTECTED, `applied=NO` |
| 24-26 | Edits only after all gates; both files reconcile; arithmetic exact | **MET** — zero edits |
| 27 | No next module selected | **MET** |
| 28 | Security observations preserved without overstatement | **MET** — 20 total, all static-only |
| 29-32 | Inputs frozen; exact failure identity; invariants; environment | **MET** |
| 33-40 | No app/role/permission/migration change; no merge; PartsRequest; readonly@; 144; 2D canaries; no frontend | **MET** |

Gate 19 unmet ⇒ blocked.

## What was achieved

**D-05 repaired.** Request inputs are normalized to both the Python symbol and
the external request name, across Query/Path/Header/Cookie/Form/File defaults,
`Annotated` metadata, and Pydantic `alias` / `validation_alias` /
`serialization_alias` / `AliasChoices` / `AliasPath`, following nested models.
`tid: UUID = Query(..., alias="tenant_id")` is now seen as a client-asserted
tenant, and `POST /v1/commerce/warranty/claims` classifies exactly as 2F-26E's
manual verdict said it should.

**D-06 repaired.** Handler call arguments are mapped positionally onto the
resolved callee's parameter names. `resend_invite(user_id, inviter_id)` is now
read correctly: the principal occupies an attribution slot, the path id is the
target subject, and no ownership predicate exists — so the classifier abstains
with a reason instead of inventing self-scope. The repair does **not**
over-correct: `DELETE /v1/auth/sessions/{session_id}`, which has a real
ownership predicate, still resolves as genuine self-service.

**The evidence-review contract earned its place immediately.** Requiring an
explicit mutating-GET check caught `GET .../customers/{customer_id}/ltv`
persisting a row via `db.add` + `flush` — precisely the class of error I made
in 2F-26E. Without the checklist I would have recorded it as a pure read.

**Both burned corpora pass at 24/24** on persona and tenant direction, and
33 verifier fixtures all fire and restore.

## Why still blocked

Three disagreements, all genuine tool defects, all in the layer added this
slice:

1-2. **Capability-family prefix precedence** — `^/v1/tenants?\b` and `^/v1/me\b`
sit above the more specific `geography_serviceability` and `media` rules in an
ordered list, so `/v1/tenant/service-areas/...` and `/v1/me/profile-photo` got
the general family. A two-line fix.

3. **Write-regex equality false positive** — `\.is_active\s*=` also matches
`is_active ==` inside a SELECT predicate, so a pure read was called a mutation.

None is fixed. All three were found by, or while adjudicating, the holdout
that measures the classifier.

## Honest disclosures

- **The authorization reasoning is now clean and the taxonomy layer is not.**
  Persona, tenant direction, capability action and abstention are 24/24 on a
  fresh disjoint blinded sample. It would be easy to present that as a pass;
  it is not one. The contract is every required field.
- **The remaining defects are shallow** — two ordering lines and one regex
  character class. That makes them cheap to fix and does **not** make them
  eligible to be fixed here.
- **Not all 46 documents are produced.** Files describing a passing holdout,
  an applied expansion or a rebuilt queue would describe work that did not
  happen. Sixteen real artifacts exist.
- **All three holdouts are burned.** 51 routes remain — two more holdouts of
  this size. That is arithmetic, stated because the mission asked that
  exhaustion not be claimed without it.
- **A formal correction is recorded** against 2F-26E's manual sheet (a
  mutating GET recorded as a pure read). The frozen artifact was **not**
  edited — rewriting it would destroy the evidence that the error happened.
- **Burned-corpus results approve nothing.** The classifier was tuned against
  both.

## Preserved

Zero application files modified; zero authorization behaviour changed; both
canonical files and the matrix byte-identical. Closed-module canaries pass
(field_ops, Package Commerce, customer_reviews, legacy review incl. 410,
compliance). StaffPermission grant, explicit deny, cross-tenant isolation and
unknown-role fail-closed all re-asserted. Canonical roles only; no role,
permission or migration added; no pipeline merged; `PartsRequest`
ServiceJob-only; `readonly@demo-ac-services.local` untouched; Migration 144
unapplied; Slice-2D canaries untouched; no frontend work.

## Stop condition

Stops at the Slice 2F-26F approval gate. No module selected, no authorization
implemented, no canonical change.

**Next slice:** reorder the capability-family table most-specific-first, tighten
the write pattern to exclude equality operators, then validate against a
**fourth** frozen holdout drawn from the 51 remaining routes.
