# Implementation Summary — Slice 2F-26F

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

Coverage **214 / 257**, 43 unprotected. Canonical `45244cd9540456db` and
matrix `4c7c3bce02096a43` unchanged. Zero canonical edits, zero application
files modified.

## D-05 repaired — alias-aware request dataflow

`scripts/workflow_rearchitecture/request_model_2f26f.py` normalizes every
client-controlled input to BOTH its Python symbol and its external request
name, across Query/Path/Header/Cookie/Form/File defaults, `Annotated`
metadata, and Pydantic `alias` / `validation_alias` / `serialization_alias` /
`AliasChoices` / `AliasPath`, following nested models.

`tid: UUID = Query(..., alias="tenant_id")` now resolves to
`tid -> tenant_id (Query:alias)`, and `POST /v1/commerce/warranty/claims`
classifies as `TENANT_PROVIDER_MUTATION` / `CLIENT_ASSERTED_TARGET_TENANT` —
exactly 2F-26E's manual verdict. The inverse error is guarded too: a name
containing "tenant" only in prose is not a tenant identifier.

## D-06 repaired — actor / subject / scope separation

Handler call arguments are mapped **positionally** onto the resolved callee's
parameter names, so a value's meaning comes from the slot it lands in:

| Route | Principal lands in | Verdict |
|---|---|---|
| `POST /v1/auth/staff/{user_id}/invite/resend` | `inviter_id` (attribution) | ACTOR_IDENTITY, no scope → abstain with reason |
| `DELETE /v1/auth/sessions/{session_id}` | subject slot + ownership predicate | genuine SELF_SERVICE_MUTATION |

Scope now requires an ownership predicate, a subject slot, or a scoped
lookup. `actor_id`, `created_by`, `requested_by`, `inviter_id` and friends
never establish it. Unrecognised slots default to `ACTOR_IDENTITY` — fail
closed, since that cannot manufacture scope.

## Shared capability taxonomy frozen

20 families × 18 actions, used by manual sheets, classifier output,
comparison logic and verifier fixtures. Replaces the free-form `capability`
column that absorbed a persona judgement in 2F-26E.

## Manual evidence-review contract

A separate artifact (`third-manual-evidence-review.csv`, 12 checks per route,
24/24 PASS) that must pass before a manual verdict is frozen. It immediately
caught `GET .../customers/{customer_id}/ltv` persisting a row (`db.add` +
`flush`) — the exact class of error made in 2F-26E — and correctly cleared
`/pricing/recommendations` as a pure read.

## Population arithmetic

`123 − 24 − 24 = 75`, zero overlap, all 75 still mounted, zero disappeared.
Eligible-set hash `479d87403ccd131b`. After this holdout, **51 remain**.

## Burned corpora (development evidence only)

| Corpus | Persona | Direction |
|---|---|---|
| 2F-26D (24) | 24/24 | 24/24 |
| 2F-26E (24) | 24/24 | 24/24 |

Neither approves anything; the classifier was tuned against both.

## Third holdout — 21/24

Persona, tenant direction, capability action and abstention reason all
**24/24**. Three failures, all in the capability/side-effect layer added this
slice: capability-family prefix precedence (2), and a write-regex equality
false positive (1). None fixed — each was found by the holdout that measures
the classifier.

## Verifier

33 conditions (19 carried + 13 new + matrix), each with an executed fixture
that forces failure, names its condition and restores clean state.
`--selftest` exits 0; `main()` exits 1 on N09 and N32.

## Verification

- `tests/test_phase2f26f_alias_actor_scope.py` — **41 passed**
- All phase-2F suites (17A, 26, 26B, 26C, 26D, 26E, 26F) — **202 passed, 0 failed, 0 errors**
- Environment: api:8000, postgres:5432, redis:6379 REACHABLE throughout
- Zero `app/` files modified
