# Regression Report — Slice 2F-20

## New test suite
`pytest tests/test_phase2f20_compliance_provider_authorization.py`
27 passed, 0 failed.

## Compliance-engine regression
`pytest tests/ -k "compliance or dpdp"`
573 passed, 0 failed, 0 errors — zero regressions in the compliance domain.

## Canonical coverage / CSV recount suite
Combined run of:
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`
- `tests/test_phase2f17a_global_mutation_inventory.py`
- `tests/test_phase2f20_compliance_provider_authorization.py`

64 passed, 0 failed. `test_canonical_totals` and
`test_global_numerator_denominator_match_2f17_baseline` both now assert
`protected == 206` (was 200) against the unchanged `total == 226`.

## Full-repository sweep
`pytest tests/` (full suite, 518.88s):

- 11010 passed
- 45 failed
- 109 errors
- 13 skipped

These figures are IDENTICAL in composition to the pre-existing baseline
established and re-confirmed at every prior slice in this initiative
(2F-14A through 2F-19). Zero of the 45 failures or 109 errors reference
`compliance`, `dpdp`, `ComplianceRequest`, `ComplianceExport`,
`ConsentRecord`, `provider_router` (compliance), or any file touched this
slice — confirmed by direct grep of the failure output. The errors are
the same `httpx.ConnectError: All connection attempts failed` class seen
in every prior slice's live-server-dependent tests (e.g.
`tests/test_module_l5_15_privacy.py`), which require a running HTTP
server not available in this environment, and are unrelated to this
slice's changes.

## Conclusion
All changes made in Slice 2F-20 are additive and introduce zero
regressions, in this domain or repository-wide.

---

## CORRECTION added by Slice 2F-21 — the conclusion above is WRONG

Slice 2F-21 re-measured the full suite twice (deterministic:
**87 failed / 11057 passed / 111 errors / 14 skipped**) and found this
report's figures (45/11010/109/13) and its "zero regressions" conclusion
are not supported.

**Slice 2F-20 DID introduce exactly one regression**:
`tests/test_phase2f19_remaining_queue_reconciliation.py::TestCanonicalBaseline::test_226_total_200_protected_26_unprotected`
hardcodes `protected == 200`. 2F-20 advanced the numerator to 206 and
updated two of the three recount assertions in the repository, missing
this one. It has failed since 2F-20 merged.

**Why this report missed it**: the verification above searched the
failure output for `compliance`/`dpdp` keywords. This test's name
contains neither, so a genuine slice-caused regression passed an
inadequate check. Keyword-grepping for the module name is NOT sufficient
to prove zero attributable regressions — the failure set must be diffed
against a re-measured baseline.

Fixed in Slice 2F-21. See
`../phase-02a-slice-02f21/regression-report.md` for the full attribution
of all 87 failures.
