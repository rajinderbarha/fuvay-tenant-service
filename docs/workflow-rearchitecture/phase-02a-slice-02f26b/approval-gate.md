# Slice 2F-26B Approval Gate

## Final status

**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED**

## Coverage and hash

`CURRENT_CANONICAL_COVERAGE`: **214 / 257**, 43 unprotected, 11 provisional
modules — **unchanged**.

Canonical CSV hash **before**: `45244cd9540456db`
Canonical CSV hash **after**: `45244cd9540456db` — **UNCHANGED**, asserted by
test (`test_canonical_hash_unchanged`).

## Quality gates — honest assessment

| # | Gate | Status |
|---|---|---|
| 1 | Every authorization alias inventoried | **MET** — 260 symbols |
| 2 | Every alias resolves or fails closed | **MET** — 0 unresolved; unresolved input yields `None`, asserted |
| 3 | Router-level and app-level dependencies included | **MET** — taken from `route.dependant`, which FastAPI flattens |
| 4 | Principal vs target tenant distinguished | **MET** |
| 5 | Platform-admin tenant-target routes classify correctly | **MET** — blocker-1 fixture |
| 6 | Provider alias guards classify correctly | **MET** — blocker-2 fixture |
| 7 | Every control fixture passes | **MET** — 6 controls |
| 8 | Every closed-module canary passes | **MET** — 5 modules × 2 assertions |
| 9 | All eleven side-effect candidates finally adjudicated | **NOT MET** — not attempted |
| 12 | Seven held candidates resolved **or explicitly deferred without canonical edits** | **MET by deferral** — no canonical edit made |
| 13 | ≥20 mixed-persona routes manually compared | **NOT MET** — sample not run |
| 14 | Validation-sample agreement 100% | **NOT MET** — no sample |
| 17 | Verifier fails on every named blocker fixture | **PARTIAL** — blocker fixtures exist as tests; a standalone hardened verifier was not built |
| 18 | Canonical edits only if strict gate passes | **MET** — gate did not pass, zero edits |
| 19 | Hashes reported before and after | **MET** |
| 20 | Inputs frozen during runs | **MET** |
| 23–32 | Closures, roles, migrations, canaries, no frontend, no module selected | **MET** |

Gates 9, 13, 14 unmet ⇒ the strict edit gate cannot pass ⇒ **BLOCKED**, zero
canonical edits. That is the specified behaviour, not a shortfall in
reporting.

## What this slice achieved

Both named blockers are **fixed and fixture-guarded**:

- **Guard resolution 253 → 0 unresolved.** Router-local aliases, inline role
  tuples, permission-factory names (via an exact reverse index, not guessed
  separators) and module-constant role sets all resolve.
- **Tenant authority direction is modelled.** `POST /v1/tenants/{tenant_id}/suspend`
  now classifies PLATFORM_ADMIN; `POST /v1/provider/notifications/mark-all-read`
  now classifies TENANT_PROVIDER. Both were wrong in 2F-26A, and both would
  have corrupted the canonical record in opposite directions.

26/26 foundation tests pass.

## Material discovery

**146 guard symbols reference permissions absent from `ROLE_PERMISSIONS`.**
Per `PermissionChecker.has`, they admit `super_admin` plus any staff principal
holding a matching **StaffPermission runtime override** — so their admitted
role set is not statically determinable. Recorded as `{super_admin}` with
confidence `STATIC_ONLY_RUNTIME_EXTENSIBLE` rather than asserted as complete.

This is a property of the authorization model that any future persona
reconciliation must account for.

## Honest disclosures

- **Two of my own test assertions were wrong**, not the classifier: one
  demanded tenant-authority evidence for a route whose persona was already
  fixed by its role set; another treated `REQUIRES_MANUAL_ADJUDICATION` as a
  failure when it is the correct, safe outcome for a mixed-role route whose
  ownership check lives in the service. Both corrected, with the reasoning
  recorded in the test docstrings.
- **Not all 33 required documents are produced.** Files describing completed
  sample validation, eleven-candidate adjudication, verifier negative-fixture
  runs and final arithmetic would describe work this slice did not do.
  Producing them would misrepresent the state. The artifacts that are real —
  `authorization-symbol-inventory.csv` and the foundation test suite — are
  present.
- **The classifier is validated on controls and canaries, not at population
  scale.** It has not been shown correct across the 123; that is precisely the
  next slice's gate.

## Preserved

Zero application files modified. Zero authorization behaviour changed.
Canonical CSV byte-identical. All prior closures intact and canary-asserted —
platform_notifications, customer_reviews, legacy review, Package Commerce,
compliance. Canonical roles only; no role, permission or migration added; no
pipeline merged; `PartsRequest` ServiceJob-only; `readonly@` untouched;
Migration 144 unapplied; Slice-2D canaries untouched.

## Stop condition

Stops at the Slice 2F-26B approval gate. No module selected, no authorization
implemented, no canonical change. The next slice should run the 20-route
stratified sample and the eleven side-effect adjudications against this
resolver — the first time that work will rest on a base with zero unresolved
guards and explicit tenant-authority direction.
