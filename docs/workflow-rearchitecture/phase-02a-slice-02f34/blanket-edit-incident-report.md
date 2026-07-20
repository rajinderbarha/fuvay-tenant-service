# Blanket-Edit Incident Report

## What happened

During Slice 2F-33's cascading rebaseline (required because the coverage
figures moved 238→241/262→264/24→23), a blanket `sed` find/replace
(`== 24` → `== 23`) was applied across several 2F-26-era classifier test
files without first checking whether every occurrence of the literal `24`
in those files actually meant "canonical unprotected route count." Six
assertions in `tests/test_phase2f26d_blinded_validation.py`,
`test_phase2f26e_classifier_repair.py`, `test_phase2f26f_alias_actor_
scope.py`, `test_phase2f26g_family_precedence_ast_writes.py`, and
`test_phase2f26h_tokenized_action.py` were incorrectly altered — these
files use `24` to mean "24 samples in a holdout corpus," an unrelated
coincidental numeric collision.

## How it was caught

Slice 2F-33 ran the FULL `tests/test_phase2f*.py` suite (not just the
directly-touched files) before reporting completion. The full run
surfaced these 6 failures immediately.

## How it was fixed

Reverted the incorrect `24`→`23` changes in all 6 files via a second,
narrowly-scoped `sed` restricted to exactly those 5 files. One of the 6
reverted values (`test_agreement_is_23_of_24` in 2F-26g) was itself a
genuine `23`-of-`24` classifier-agreement figure that the revert
incorrectly restored to `24` — caught by a second full-suite run and
fixed individually.

## A second, more subtle round

Slice 2F-33's authorization fix (deriving `update_location`'s and
`create_zone`'s tenant server-side instead of trusting the client)
**legitimately** changed what the LIVE persona/tenant-direction
classifier (`authority_model_2f26h.py` and siblings) reads for those 2
routes — from `CLIENT_ASSERTED_TENANT` (correct before the fix) to
`PRINCIPAL_TENANT` (correct after the fix). This surfaced as 5 more test
failures across the same 5 classifier files. This was NOT a mistake — it
is the correct, expected consequence of the authorization fix. Per this
program's historical-immutability discipline, the frozen manual-
adjudication corpora were **not** edited to match; instead, each affected
test received a narrowly-scoped, documented exception for exactly these
2 route keys, explaining why the live classification legitimately
diverges from the frozen historical label.

## Verification this slice

Re-ran the affected 5 classifier test files this slice: all pass (176/176
across the combined suite, confirmed as part of this slice's own full
regression run). No incorrect literal value remains in any test file.
