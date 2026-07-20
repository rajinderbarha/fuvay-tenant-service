# Slice 2F-26G Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

D-07 and D-08 are repaired and proven repaired. The fourth holdout reached
23/24 against a required 24/24 — a **new** defect (D-09) in the
capability-action layer — so the strict edit gate fails with zero canonical
edits.

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
| Capability family | **24/24** |
| Side effect | **24/24** |
| Abstention reason | **24/24** |
| Capability action | 23/24 |
| **All six** | **23/24** |

Across four independent holdouts: **4/24 → 19/24 → 21/24 → 23/24**.

## Quality gates

| # | Gate | Status |
|---|---|---|
| 1 | Every family rule inventoried | **MET** — 30 rules + fallback |
| 2 | Family precedence deterministic | **MET** — levelled contract |
| 3 | Specific outrank generic | **MET** — D07-01/02 |
| 4 | Equal-priority conflicts fail closed | **MET** — raises FamilyConflict |
| 5 | Shadowed/unreachable detected | **MET** — audit over all mounted paths, 0 shadowed |
| 6 | D-07 regression tests | **MET** |
| 7 | AST write detection where source available | **MET** |
| 8 | Equality/comparison excluded | **MET** — grammar-level |
| 9 | D-08 regression tests | **MET** |
| 10 | Regex fallback cannot independently prove a mutation | **MET** — LOW_REGEX_FALLBACK, source-unparseable only |
| 11 | All three burned corpora pass | **MET** — 24/24 each on measured fields |
| 12 | Remaining-population arithmetic exact | **MET** — 123−72=51, all mounted |
| 13 | Strata reflect availability | **MET** — 5 declared not representable |
| 14 | Behavioural cases tested separately | **MET** |
| 15 | Holdout disjoint from all burned corpora | **MET** — 72 union, 0 overlap |
| 16-17 | Manifest, manual, evidence frozen before classifier | **MET** |
| 18 | ≥24 routes | **MET** — 24 |
| 19 | Normalized comparison contract | **MET** |
| 20 | Every required non-abstained field agrees | **NOT MET** — 23/24 |
| 21 | Zero avoidable abstentions | **MET** |
| 22 | Every verifier blocker has an executed fixture | **MET** — all fire, clean state restores |
| 23 | Closed-module canaries pass | **MET** |
| 24 | Both proposed routes reconfirmed | **MET** — recorded UNPROTECTED, `applied=NO` |
| 25-27 | Edits only after all gates; files reconcile; arithmetic exact | **MET** — zero edits |
| 28 | No next module selected | **MET** |
| 29 | Security observations preserved without overstatement | **MET** — 28 total, all static-only |
| 30-33 | Inputs frozen; exact failure identity; invariants; environment | **MET** |
| 34-41 | No app/role/permission/migration change; no merge; PartsRequest; readonly@; 144; 2D canaries; no frontend | **MET** |

Gate 20 unmet ⇒ blocked.

## What was achieved

**D-07 repaired with a mechanism, not a reorder.** Capability family now
resolves through a levelled precedence contract (exact path → resource prefix
→ specific nested resource → engine prefix → fallback). The lowest matching
level wins; two equally specific rules that disagree **raise** rather than pick
one. `/v1/tenant/service-areas/...` resolves to `geography_serviceability` and
`/v1/me/profile-photo` to `media` — the two 2F-26F failures — and the rule set
is audited over every mounted path with zero shadowing, zero conflicts, zero
fallback capture. Capability family scored **24/24** on the fresh holdout.

**D-08 repaired at the grammar level.** Write detection walks the AST:
`ast.Assign` / `AnnAssign` / `AugAssign` on an attribute, `setattr`,
`update().values()`, `db.add`/`delete`/`flush`/`commit`. An equality operator
is `ast.Compare`, which the grammar can never confuse with an assignment, so
`Model.is_active == True` inside a SELECT is never a write. The regex fallback
survives only for source that cannot be parsed, excludes every comparison
operator, and is labelled `LOW_REGEX_FALLBACK` — it cannot independently prove
a mutation. Side effect scored **24/24**, including the pure-read that 2F-26F
mis-flagged and the genuine mutating GET on `/customers/{id}/ltv`.

**The evidence-review checklist again earned its place** — it confirmed the six
service-only ownership predicates behind the six abstentions, so those
abstentions are correct rather than guesses.

## Why still blocked — D-09 (new)

`POST /v1/tenants/{tenant_id}/engines/bulk-disable`: manual action
`deactivate`, tool action `create`. The action table matches `/disable\b`
(slash-anchored); the segment is `bulk-disable`, so it fell through to the POST
default. Same class of literalness as D-07, one layer over. Not fixed — found
by the holdout that measures the classifier.

## Honest disclosures

- **Five of six fields are now perfect on a fresh disjoint blinded sample.**
  That is real progress and still not a pass; the contract is every required
  field, and it is one short.
- **D-09 is shallow** — a slash-anchored token that should also match a
  hyphen-joined verb. Cheap to fix, and not eligible to be fixed here.
- **Each repair keeps finding the next instance of the same root pattern**:
  regexes that are too literal for real paths (D-05 alias, D-07 family, D-09
  action). A future slice may be better served replacing pattern-matching in
  the capability layer with token decomposition, rather than patching one
  operator at a time.
- **Not all 46 documents are produced.** Files describing a passing holdout,
  an applied expansion or a rebuilt queue would describe work that did not
  happen. Seventeen real artifacts exist.
- **All four holdouts are burned.** 27 routes remain — one more holdout of
  this size. Arithmetic, stated because the mission required it.
- **Burned-corpus results approve nothing** — the classifier was tuned against
  all three.

## Preserved

Zero application files modified; zero authorization behaviour changed; both
canonical files and the matrix byte-identical. Closed-module canaries pass
(field_ops, Package Commerce, customer_reviews, legacy review incl. 410,
compliance). StaffPermission grant, deny precedence, cross-tenant isolation and
unknown-role fail-closed re-asserted. Canonical roles only; no role, permission
or migration added; no pipeline merged; `PartsRequest` ServiceJob-only;
`readonly@demo-ac-services.local` untouched; Migration 144 unapplied; Slice-2D
canaries untouched; no frontend work.

## Stop condition

Stops at the Slice 2F-26G approval gate. No module selected, no authorization
implemented, no canonical change.

**Next slice:** decompose capability-action matching so hyphen-joined verbs
like `bulk-disable` resolve correctly (D-09), then validate against a fifth
holdout drawn from the 27 remaining routes — the last independent holdout this
population can supply.
