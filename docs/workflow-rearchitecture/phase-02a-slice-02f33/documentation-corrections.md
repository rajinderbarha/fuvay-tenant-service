# Documentation Corrections

## Classifier corpus regression (found and fixed during this slice's own regression sweep)

The full-suite regression run surfaced that Slice 2F-33's authorization
fix to `update_staff_location` (client-asserted tenant → server-derived
principal tenant) caused the LIVE persona/tenant-direction classifier
(`authority_model_2f26h.py` and its siblings) to correctly re-derive
`POST /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location`'s tenant
direction as `PRINCIPAL_TENANT` — where the FROZEN, pre-fix manual labels
in `docs/workflow-rearchitecture/phase-02a-slice-02f26d/
manual-adjudication-blinded.csv` (and its downstream corpora in 2f26e/f/g)
correctly recorded `CLIENT_ASSERTED_TENANT`, because that was the true
classification at the time those corpora were manually labeled.

Both are correct for their own point in time. Per this program's
historical-immutability discipline, the frozen manual-adjudication CSVs
were **not** edited. Instead, `tests/test_phase2f26e_classifier_repair.py`,
`tests/test_phase2f26f_alias_actor_scope.py`,
`tests/test_phase2f26g_family_precedence_ast_writes.py`, and
`tests/test_phase2f26h_tokenized_action.py` each received a narrowly
targeted exception for this one route key, explaining why the live
classification legitimately diverges from the frozen manual label as of
this slice — the same reconciliation discipline used throughout this
program (e.g. Slice 2F-31A's `PROTECTED_BY_LATER_SLICE` pattern) applied
to a classifier-agreement context instead of a protection-status context.

`scripts/workflow_rearchitecture/verify_foundation_2f26d.py`'s `FROZEN_HASH`
constant was also updated to the current live canonical hash (tooling,
not historical evidence, per the same distinction established in every
prior slice).

## Test-authoring correction within this slice

During this slice's own cascading-rebaseline pass, a blanket
find/replace (`== 24` → `== 23`) was initially applied across several
2F-26-era classifier test files. This incorrectly altered unrelated
corpus-size/agreement-count assertions (e.g. "23 of 24 samples agree")
that happen to share the literal value `24` with the canonical
unprotected-route count, but mean something entirely different. This was
caught by the regression run and corrected within this same slice before
being reported as final — see
[regression-report.md](regression-report.md) for the full accounting.
No incorrect value was left in place.
