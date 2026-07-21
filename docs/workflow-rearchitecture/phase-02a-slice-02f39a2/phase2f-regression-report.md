# Phase-2F Regression Report — Slice 2F-39A2

Full `tests/test_phase2f*.py` regression, run twice:

| Run | Result | Duration |
|---|---|---|
| A | 2481 passed, 0 failed, 0 errors, 34 warnings | 320.70s |
| B | 2481 passed, 0 failed, 0 errors, 34 warnings | 335.64s |

Collection grew from the 2477 baseline to 2481 (+4 — this slice's new
`test_phase2f39a2_security_apikey_fix.py`).

## One intermediate failure, found and fixed before this clean result

The first run of this suite (before a follow-up fix) found 1 failure:
`test_phase2f26h_tokenized_action.py::TestBurnedCorporaStableFields::test_all_four_corpora_persona_and_direction_stable`.
Root cause: fixing `security.router::create_api_key`'s cross-tenant IDOR
(deriving `tenant_id` server-side instead of trusting the client body)
legitimately changed the live classifier's resolved `tenant_direction`
for that route from `CLIENT_ASSERTED_TARGET_TENANT` to `PRINCIPAL_TENANT`
— exactly the same "forward-progress classifier reclassification"
pattern this test file's growing exemption list already documents for
dozens of other routes fixed in 2F-33/35/36/37. Added the same kind of
narrow, explicitly-commented exemption; re-ran clean (34/34 passed in
that file). Not a broad rebaseline — only one row's classification
changed, with a comment explaining exactly why.
