# Implementation Summary — Slice 2F-26D

## Final status: CLASSIFIER_VALIDATION_FAILED_CANONICAL_UNCHANGED

Coverage remains **214 / 257**, 43 unprotected. Canonical hash
**`45244cd9540456db`** before and after. Zero canonical edits, zero
application files modified.

## What was done

### 1. Blinded stratified sample — frozen before any verdict

24 routes across 6 strata drawn from the 123 mixed-persona population,
selected on structural attributes only (method, path prefix, `{tenant_id}`
presence). Manifest hash `bc878c81f76e54e6`, frozen 10:53:20.

### 2. Independent manual adjudication — frozen before the classifier ran

All 24 handlers read from mounted-route source and adjudicated on nine
fields. Manual hash `ad0e23e162b4fb6c`, frozen 10:55:21 — **before** the
first classifier invocation of the slice. Both hashes are asserted in tests,
so the ordering is falsifiable, not merely claimed.

### 3. Comparison — the gate fails

| Dimension | Agreement |
|---|---|
| Persona | 14/24 |
| Tenant direction | 6/24 |
| **Combined** | **4/24 = 16.7%** (required 100%) |

### 4. Four defects registered

- **D-01 (high)** — runtime-extensible permissions collapsed to
  `{super_admin}`; `plan/upgrade` and `terminate/confirm` mis-classified as
  platform-admin. Measured directly: `tenant_owner` **is** admitted with a
  StaffPermission grant, and both handlers call
  `_assert_own_tenant_or_super_admin` — dead code if only super-admins arrive.
  **This is the exact error 2F-26C's mission named**; that slice proved the
  semantics in tests and never wired them into the classifier.
- **D-02** — `tenant_authority()` returns `UNKNOWN` on 14/24, inconsistently:
  the same guard resolves correctly on one path and not another. It is also
  wrong on 2F-26B's own control route — that fixture only ever asserted
  persona, so the dimension it introduced was never tested.
- **D-03 (mine)** — 4 disagreements come from my manual sheet using
  `NO_TENANT_SCOPE`, outside the tool's vocabulary.
- **D-04** — 8 `REQUIRES_MANUAL_ADJUDICATION`: correct fail-safe behaviour,
  but not agreement.

### 5. Verifier with real negative fixtures

`scripts/workflow_rearchitecture/verify_foundation_2f26d.py` — 16 named
blocking conditions, `--selftest` proving each can fail, real exit code **1**
on 6 conditions today.

### 6. Two proposed rows reconfirmed, still not applied

Both mounted, both `require_permission(P.TENANT_UPDATE)`, both genuine
tenant mutations. Gate failed ⇒ `applied=NO`.

## What was deliberately not done

**The classifier was not touched.** Resolver hash `b1e61c218e745194`
unchanged, asserted by test. Tuning it and re-running this sample would
manufacture agreement, which the mission forbids.

**The nine remaining hidden-side-effect dispositions were not reconfirmed** —
once the gate failed, that work fed a decision that could not be taken.

## Verification

- `tests/test_phase2f26d_blinded_validation.py` — **25 passed**
- All phase-2F suites (17A, 26, 26B, 26C, 26D) — **123 passed**
- Zero `app/` files modified; the only new files are one test and one script
- Environment: api:8000, postgres:5432, redis:6379 all REACHABLE

## Artifacts

`frozen-sample-manifest.csv`, `manual-adjudication-blinded.csv`,
`tool-vs-manual-comparison.csv`, `sample-freeze-evidence.md`,
`classifier-defect-register.md`,
`authorization-observations-not-remediated.md`,
`canonical-coverage-arithmetic.csv`, `proposed-canonical-row-diff.csv`,
`approval-gate.md`, plus the verifier and test suite.

## Side finding

Manual reading surfaced apparent cross-tenant weaknesses on ~7 sampled routes
(client-asserted `tenant_id` with no ownership assertion; an audit-log write
endpoint open to any authenticated principal). Recorded in
`authorization-observations-not-remediated.md`, **not remediated** — this
slice selected no module. From static reading only; not executed against a
live tenant pair.
