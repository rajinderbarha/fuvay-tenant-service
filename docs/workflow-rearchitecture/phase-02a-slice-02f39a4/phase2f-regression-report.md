# Phase-2F Regression Report — Slice 2F-39A4

Full `tests/test_phase2f*.py` regression, run twice (after fixing 3
classifier-corpus exemption regressions caused by this slice's
`generate_invoice`/`create_order` fixes legitimately changing resolved
`tenant_direction`):

| Run | Result | Duration |
|---|---|---|
| A | 2519 passed, 0 failed, 0 errors, 34 warnings | 345.72s (0:05:45) |
| B | 2519 passed, 0 failed, 0 errors, 34 warnings | 345.44s (0:05:45) |

Collection grew from the 2500 baseline (Slice 2F-39A3) to 2519 (+19 —
this slice's new `test_phase2f39a4_defect_remediation.py`). Identical,
clean results across both runs.

## Interim (pre-fix) run, for the record

An initial run before the classifier exemption fixes showed 3 failures
(`test_phase2f26f_alias_actor_scope.py::TestBurnedCorpora::test_second_burned_corpus_persona_and_direction_recovered`,
`test_phase2f26g_family_precedence_ast_writes.py::TestBurnedCorpora::test_second_corpus`,
`test_phase2f26h_tokenized_action.py::TestBurnedCorporaStableFields::test_all_four_corpora_persona_and_direction_stable`),
2516 passed, 419.31s. Root cause: this slice's `generate_invoice` and
`create_order` fixes legitimately changed the live classifier's resolved
`tenant_direction` for `/v1/payments/invoices` and `/v1/payments/orders`
from `CLIENT_ASSERTED_TARGET_TENANT` to `PRINCIPAL_TENANT` — the same
forward-progress reclassification pattern already applied many times in
this program. Fixed by extending the relevant exemption tuples (see the
commit "Slice 2F-39A4: update 3 frozen classifier corpora..."), not by
weakening any frozen corpus's own historical labels.
