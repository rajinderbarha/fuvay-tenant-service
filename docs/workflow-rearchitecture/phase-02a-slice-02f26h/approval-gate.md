# Slice 2F-26H Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

D-09 is repaired and proven repaired. The fifth and final independent holdout
reached 22/24 against a required 24/24, so the strict edit gate fails with zero
canonical edits — and this was the **last** independent holdout the original
123-route population can supply.

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
| Side effect | **24/24** |
| Capability family | **24/24** |
| Capability action | 23/24 |
| Persona | 23/24 |
| Tenant direction | 23/24 |
| **All five** | **22/24** |

Five independent holdouts: **4 → 19 → 21 → 23 → 22**.

## Quality gates

| # | Gate | Status |
|---|---|---|
| 1 | Every action rule inventoried | **MET** |
| 2 | Path/function/service tokens normalized | **MET** |
| 3 | Hyphen, underscore, CamelCase recognized | **MET** |
| 4 | D-09 regression | **MET** |
| 5 | POST does not default to create | **MET** |
| 6 | Strong action conflicts fail closed | **MET** |
| 7 | Synonym mappings documented | **MET** |
| 8 | Resource nouns not treated as verbs | **MET** — get_export_job, disabled_count |
| 9 | Every action-verifier blocker has an executed fixture | **MET** — 18 fixtures, all fire |
| 10 | All four burned corpora pass | **MET on stable fields** — persona/dir/family/side_effect 24/24; action diverges by design (see below) |
| 11 | Final eligible-population arithmetic exact | **MET** — 123−96=27 |
| 12 | Holdout disjoint from all burned sets | **MET** — 96 union, 0 overlap |
| 13 | Reserve set frozen | **MET** — 3 routes |
| 14-15 | Manifest, manual, evidence frozen before classifier | **MET** |
| 16 | 24 routes | **MET** |
| 17 | Normalized comparison contract | **MET** |
| 18 | Every required field agrees | **NOT MET** — 22/24 |
| 19 | Zero avoidable abstentions | **MET** |
| 20 | Closed-module canaries pass | **MET** |
| 21 | Both proposed routes reconfirmed | **MET** — UNPROTECTED, `applied=NO` |
| 22-24 | Edits only after all gates; files reconcile; arithmetic exact | **MET** — zero edits |
| 25 | No next module selected | **MET** |
| 26 | Security observations qualified | **MET** — 37 total, all static-only |
| 27-30 | Inputs frozen; exact failure identity; invariants; environment | **MET** |
| 31-38 | No app/role/permission/migration change; no merge; PartsRequest; readonly@; 144; 2D canaries; no frontend | **MET** |

Gate 18 unmet ⇒ blocked.

## What was achieved

**D-09 repaired with a tokenized model, not a patched regex.** The action
classifier tokenizes the path, endpoint and qualified service-method names
(splitting `/`, `-`, `_` and CamelCase), maps verbs through a **documented**
synonym table, resolves through an explicit 7-level precedence, and **fails
closed** when two equally strong sources disagree. `bulk-disable` →
`deactivate`; `bulk-enable` → `activate`; `terminate/confirm` → `confirm`;
`api-keys/rotate` → `rotate`. Crucially, **POST no longer defaults to create** —
a POST with no reliable action evidence returns
`REQUIRES_MANUAL_ACTION_ADJUDICATION`.

**Resource nouns are not verbs.** `get_export_job` → the head `get` is a read
helper, so `export` (a later noun token) is never read as the action;
`get_disabled_count` does not yield `deactivate`. Both are executed fixtures.

**18 action-verifier fixtures** all fire when violated and restore clean state.

## Why still blocked, and why this is terminal

The two fifth-holdout disagreements are adjudication-boundary cases:

1. `POST /v1/compliance/portability-requests` — tool `export`, manual abstained.
   The tool skipped the `request` stopword and reached `export` in
   `request_export`; that is defensible and my manual was the weaker call.
2. `POST /v1/serviceability/check` — tool abstained (self-referential identity,
   no ownership predicate, no tenant), manual assigned a tenant persona from
   the path. The tool's conservative abstention is the stronger call.

On both, **the tool is at least as defensible as the frozen manual verdict.**
But the contract is exact agreement between a manual verdict frozen before the
run and the classifier output, and WS15 forbids revising the manual to match
and re-scoring. So the honest result is 22/24, and it blocks.

**Per WS16, this was the final independent holdout.** All five 24-route
holdouts (120 of 123 routes) are burned; the 3 reserve routes are insufficient
alone. **Classifier-driven canonical reconciliation on this population is
exhausted.** The classifier is materially stronger across nine repaired defects
but has not reached 100% independent agreement, and no sixth holdout may be
built from burned routes.

## Honest disclosures

- **The blocker is now manual-adjudication precision, not the classifier.** On
  a fresh disjoint sample the tool matched or beat my manual on every field
  except where my manual over- or under-reached on two boundary routes. That is
  a real and unusual state: the tool is good enough that single-reviewer manual
  error is the limiting factor. WS16 strategy 1 (dual review) or 3 (external
  reviewer) is the honest path forward.
- **Burned-corpus action divergence is by design.** The four burned manual
  sheets predate the D-09 repair and used the old POST→create convention. Their
  persona/direction/family/side_effect remain 24/24; the action column
  legitimately changed. This is documented, not a regression.
- **Not all 35 required documents claim a pass.** The four conditional
  canonical-edit artifacts are intentionally omitted and listed
  `NOT_PRODUCED` in `artifact-manifest.csv` because the gate failed.
- **This population's independent-validation budget is spent.** Stated as
  arithmetic (123 − 96 = 27; 24 used here; 3 reserve).

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

Stops at the Slice 2F-26H approval gate. No module selected, no authorization
implemented, no canonical change.

**Next step is a process decision, not another same-population holdout.** The
recommended path is WS16 strategy 1 or 3 — dual-review or an external
cross-check of the classifier against a fresh population — because same-set
independent validation is now exhausted.
EOF
echo written