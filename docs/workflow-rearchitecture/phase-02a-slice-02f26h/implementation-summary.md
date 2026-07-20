# Implementation Summary — Slice 2F-26H

## Final status: GLOBAL_COVERAGE_RECONCILIATION_BLOCKED

Coverage **214 / 257**, 43 unprotected. Canonical `45244cd9540456db` and
matrix `4c7c3bce02096a43` unchanged. Zero canonical edits, zero application
files modified.

## D-09 repaired — tokenized capability-action inference

`scripts/workflow_rearchitecture/action_model_2f26h.py`:

- **WS2 tokenization** — splits path, endpoint and service-method names on
  `/`, `-`, `_` and CamelCase. `bulk-disable` → `[bulk, disable]`.
- **WS3 synonym mapping** — a documented verb→action table
  (`action-synonym-mapping.csv`), never silent lexical similarity. The
  suspend/terminate→deactivate collapse is explicitly noted as a taxonomy
  limitation, not an invented equivalence.
- **WS4 precedence** — override → state-machine → service verb → endpoint verb
  → path verb → strong HTTP fallback → `REQUIRES_MANUAL_ACTION_ADJUDICATION`.
  **POST never auto-means create.**
- **WS5 conflict** — two equally strong sources that disagree fail closed.
- Leading-verb (function names) vs trailing-verb (REST paths) resolution, with
  a noun-stopword list so `get_export_job` and `get_disabled_count` do not read
  their noun tokens as verbs.

`bulk-disable` now resolves to `deactivate` with persona
`TENANT_PROVIDER_MUTATION` and direction `PRINCIPAL_TENANT`.

## Population arithmetic

`123 − 24×4 = 27`, zero pairwise overlap, all mounted. Eligible hash
`2d206d745cadb84b`. Fifth holdout = 24; reserve = 3.

## Burned corpora (development evidence only)

Persona/direction 24/24 on all four; family/side_effect 24/24 on 26F/26G. The
`capability_action` column legitimately diverges from the four pre-repair
manual sheets (which used POST→create); this reflects the D-09 semantic change
and is documented, not a regression.

## Fifth (final) holdout — 22/24

Side effect and capability family **24/24**. Two disagreements, both
adjudication-boundary cases where the tool's answer is at least as defensible
as the frozen manual verdict:
`portability-requests` (tool `export` vs manual abstain) and
`serviceability/check` (tool abstain vs manual tenant persona).

Per WS16 this was the **last** independent holdout from the 123-route
population; independent validation of this population is now exhausted.

## Verifier

18 action fixtures + comparison + freeze conditions, each executed, each fires
when violated and restores clean state. `--selftest` exits 0; `main()` exits 1
on N09 only.

## Verification

- `tests/test_phase2f26h_tokenized_action.py` — **34 passed**
- All phase-2F suites (17A, 26, 26B–H) — **274 passed, 0 failed, 0 errors**
- Environment: api:8000, postgres:5432, redis:6379 REACHABLE throughout
- Zero `app/` files modified

## Bottom line

The classifier is materially stronger across all nine repaired defects
(D-01…D-09). On a fresh disjoint blinded sample it matched or beat single-
reviewer manual adjudication on every field except two boundary calls. It did
not reach the required 100%, and the population's independent-validation budget
is spent. The honest next step (WS16) is a process choice — dual-review or an
external cross-check on a fresh population — not another same-set holdout.
