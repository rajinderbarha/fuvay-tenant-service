# Documentation Corrections — Slice 2F-21

## Corrections to prior-slice documentation

### ROW-LEVEL inventory data: none required
All 20 rows re-verified against the 2F-19/2F-20-recorded values matched
exactly (`coverage-row-diff.csv`); no stale, duplicate, false-positive,
non-tenant, or already-protected row was found.

### MATERIAL CORRECTION to Slice 2F-20's regression report
`docs/workflow-rearchitecture/phase-02a-slice-02f20/regression-report.md`
claimed "45 failed / 11010 passed / 109 errors" and concluded 2F-20
introduced "zero regressions." Slice 2F-21 re-measured the suite twice
(deterministic: 87 failed / 11057 passed / 111 errors / 14 skipped) and
found BOTH claims unsupported.

2F-20 introduced exactly one real regression:
`tests/test_phase2f19_remaining_queue_reconciliation.py::TestCanonicalBaseline::test_226_total_200_protected_26_unprotected`
still asserted `protected == 200` after 2F-20 advanced the canonical
numerator to 206. Three recount assertions exist in the repository;
2F-20 updated two and missed this one.

Root cause of the missed detection: 2F-20's verification grepped the
failure output for `compliance`/`dpdp` keywords only. This test's name
contains neither. Keyword-matching on the module name is not a valid
proof of zero attributable regressions.

Corrective actions taken this slice:
1. The stale assertion was fixed (`protected == 206`,
   `unprotected == 20`) with inline provenance — permitted, as "recount
   tests" are in 2F-21's explicit permitted-changes list.
2. A `## CORRECTION added by Slice 2F-21` section was appended to
   2F-20's `regression-report.md` retracting its conclusion in place,
   rather than silently leaving the false claim standing.
3. Full attribution of all 87 failures is recorded in this slice's own
   `regression-report.md`.

### Standing caveat on earlier slices
Because prior slices used the same keyword-grep verification method and
carried the same 45/11010/109 figure forward without re-measuring, their
"identical baseline / zero regressions" statements should be treated as
UNVERIFIED rather than confirmed. This slice does not retro-audit them
(out of scope), but flags the methodology defect so it is not repeated.

## New finding not previously documented (added, not a correction)
`selected-next-module.md` documents a `CLIENT_AMOUNT_TRUSTED`-class gap on
`tenant_purchase_package`'s `mark_paid` field, discovered this slice by
directly reading the route handler body (`app/engines/package_commerce/tenant_router.py`
lines 106-131) — something no prior slice had done for this route since it
was only ever listed in the queue CSV, never implemented. This is an
ADDITION to the route's documented risk profile (upgraded from the queue
CSV's plain `PERMISSION_ONLY_NOT_SCOPE_AWARE`/severity `MEDIUM` to this
slice's `HIGH` in `remaining-route-inventory.csv`, with the secondary gap
`CLIENT_AMOUNT_TRUSTED` recorded in `remaining-gap-classification.csv`),
not a correction of a prior error — the prior queue CSV's classification
was accurate as far as it went, just incomplete (it had not read the
handler body).

## Forward annotation added
Per this initiative's established pattern (2F-20 annotated 2F-19's
`approval-gate.md`; 2F-19 annotated 2F-18E's), a forward annotation was
added to `docs/workflow-rearchitecture/phase-02a-slice-02f20/approval-gate.md`
confirming 2F-20's closure stands and documenting what 2F-21 did
(reconciliation + selection of `package_commerce.tenant_router` for
Slice 2F-22). See that file's own new closing section for the exact text.
