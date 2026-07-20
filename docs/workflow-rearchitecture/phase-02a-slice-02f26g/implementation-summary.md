# Implementation Summary — Slice 2F-26G

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

Coverage **214 / 257**, 43 unprotected. Canonical `45244cd9540456db` and
matrix `4c7c3bce02096a43` unchanged. Zero canonical edits, zero application
files modified.

## D-07 repaired — deterministic capability-family precedence

`scripts/workflow_rearchitecture/capability_rules_2f26g.py` replaces the
ordered regex list with a levelled contract: exact path (L1) → resource prefix
(L2) → specific nested resource (L3) → engine prefix (L4) → fallback (L5). The
lowest matching level wins; within a level the highest explicit priority wins;
two equally specific rules that disagree **raise `FamilyConflict`** rather than
silently pick one.

`/v1/tenant/service-areas/...` → `geography_serviceability` (L2),
`/v1/me/profile-photo` → `media` (L2) — the two 2F-26F failures — while
`/v1/tenants/x/suspend` and `/v1/me/preferences` keep their general families.
Audited over every mounted path: **0 shadowed, 0 conflicts, 0 fallback
capture**. Fresh-holdout capability family: **24/24**.

## D-08 repaired — AST-based write detection

`scripts/workflow_rearchitecture/write_detector_2f26g.py` walks the AST and
recognises only genuine mutations: `Assign`/`AnnAssign`/`AugAssign` on an
attribute, `setattr`, `update().values()`, ORM bulk update/delete,
`db.add`/`delete`/`flush`/`commit`. An equality operator is `ast.Compare`,
which the grammar cannot confuse with `ast.Assign`, so `Model.is_active ==
True` inside a SELECT is never a write. The regex fallback survives only for
unparseable source, excludes `== != <= >= :=`, and is `LOW_REGEX_FALLBACK`
confidence — it cannot independently justify canonical inclusion.

12/12 assignment-vs-comparison fixtures pass. Fresh-holdout side effect:
**24/24**, including the pure-read 2F-26F mis-flagged and the genuine mutating
GET on `/customers/{id}/ltv`.

## Population arithmetic

`123 − 24 − 24 − 24 = 51`, zero pairwise overlap, all 51 still mounted.
Eligible hash `67a4a51614489bd8`. After this holdout, **27 remain**.

## Burned corpora (development evidence only)

| Corpus | Result |
|---|---|
| 26D (24) | persona 24/24, direction 24/24 |
| 26E (24) | persona 24/24, direction 24/24 |
| 26F (24) | family 24/24, side_effect 24/24 |

Neither approves anything; the classifier was tuned against all three.

## Fourth holdout — 23/24

Persona, tenant direction, capability family, side effect and abstention all
**24/24**. One miss: capability action on `bulk-disable` (tool `create`,
manual `deactivate`) — a **new** defect D-09 where the action regex `/disable`
does not match the hyphenated `bulk-disable`. Not fixed — found by the holdout
that measures the classifier.

## Verifier

36 conditions (carry-forward + 8 D-07 + 9 D-08 + freeze-integrity), each with
an executed fixture that forces failure and restores clean state. `--selftest`
exits 0; `main()` exits 1 on N09 only. Family-rule and write-detector hashes
asserted unchanged since freeze (F01/F02).

## Verification

- `tests/test_phase2f26g_family_precedence_ast_writes.py` — **38 passed**
- All phase-2F suites (17A, 26, 26B–G) — **240 passed, 0 failed, 0 errors**
- Environment: api:8000, postgres:5432, redis:6379 REACHABLE throughout
- Zero `app/` files modified

## Known limitations

- D-09 open (deliberately). All four holdouts burned; 27 remain (one more).
- Capability action still pattern-based — same literalness that produced D-07.
- Security observations (28) static-only, none executed.
