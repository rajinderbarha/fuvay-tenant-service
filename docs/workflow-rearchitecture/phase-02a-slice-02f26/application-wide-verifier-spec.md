# Application-Wide Verifier Spec — Slice 2F-26

`scripts/workflow_rearchitecture/verify_app_wide.py` — exits non-zero on any
failure.

## Checks

| Group | Check |
|---|---|
| Inventory | every mounted route exported (>2000) |
| Inventory | every route has a behaviour classification |
| Inventory | no route remains `UNKNOWN_BEHAVIOR` |
| Inventory | every genuine mutation has a persona |
| Inventory | mutating-GET and read-only-POST audits exist |
| Canonical | no row carries `UNKNOWN_PROTECTION` / `UNVERIFIED` / empty |
| Canonical | no duplicate canonical route keys |
| Canonical | protected + unprotected == denominator |
| Canonical | every canonical row resolves to a mounted route |
| Canonical | every confirmed tenant mutation has a canonical row |
| Blind spot | generic-prefix tenant mutations are represented (a sweep finding none has not looked) |
| Non-vacuity | docstring text cannot satisfy a source check |
| Non-vacuity | WHERE-clause inspection ignores SELECT column lists |
| Honesty | no document claims completeness while checks fail |

## Non-vacuity by construction

Two traps were hit for real earlier in this initiative, so the verifier guards
against both **and proves it does**:

**Prose matching.** 2F-24 asserted `Depends(get_current_user)` was absent and
matched a *comment* describing its removal; 2F-25A asserted `ServiceJob` was
absent and matched a *docstring* saying it is not used. `strip_prose()` parses
the AST and removes docstrings, then re-unparses, so a check can never be
satisfied by documentation. The verifier tests this on a function whose
docstring deliberately mentions `db.add(` and `tenant_id` while its body does
neither.

**Whole-statement SQL matching.** 2F-25 asserted `"tenant_id" in str(stmt)`,
which passes even for a completely unscoped query because every
`SELECT reviews.*` lists the column. `where_clause()` splits on `WHERE` and
inspects only the criteria. The verifier builds an unscoped and a scoped
statement and asserts the helper distinguishes them.

## Negative fixtures

`TestVerifierDiscrimination` proves the verifier can fail:
- it passes on the current tree;
- an injected failing condition is recorded in `FAILURES`;
- a lying docstring does not satisfy a source check;
- `str(unscoped_stmt)` contains `tenant_id` (the trap) while
  `where_clause(unscoped_stmt)` does not.
