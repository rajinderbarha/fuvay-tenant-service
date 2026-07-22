# Regression Report - Slice 2F-31

## Before
Full phase-2F suite green: 2255 passed, 0 failed, 0 errors.

## After the code + canonical change (pre-rebaseline)
49 failures: the intended coverage movement (226->233, 259->262, 33->29, new
hashes), plus assertions in 2F-27A/28/29/30 that treated their point-in-time
artifacts as if they must equal the live canonical set, plus a classifier
discrepancy (`require_staff_or_above_mutation` resolves to
`STAFF_EXECUTION_ROLE_SCOPE_AWARE`, not the `TENANT_MUTATION_ROLE_SCOPE_AWARE`
value I had initially written into the canonical CSV).

## Resolution
- ~30 current recount/hash assertions rebaselined to the new live values.
- 2F-27A/28/29/30 held-candidate and queue-reconciliation assertions reframed
  to account for the 3 Set B additions and 7 Set A closures, with explicit
  "point-in-time artifact vs live state" reconciliation formulas rather than
  loosened equality checks.
- Canonical CSV corrected to the classifier-verified guard_status
  (`STAFF_EXECUTION_ROLE_SCOPE_AWARE`) for the 6 closed routes; three
  historical snapshot CSVs (2F-21, 2F-23) updated to match, since they record
  LIVE runtime re-verification, not frozen decisions.

## Final
- **2290 passed, 0 failed, 0 errors** (plus 35 new N01 tests).
- New failures: none. Resolved failures: 49 (all intended/reconciled).
  Unchanged failures: none. New errors: none.
- Canonical hash `af8388463ac3dbfa`; matrix hash `3066e137e9a23c19`.
- Changed application files: `app/engines/media/new_router.py` only.
