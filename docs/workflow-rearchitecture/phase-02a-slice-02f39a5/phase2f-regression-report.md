# Phase-2F Regression Report — Slice 2F-39A5

Full `tests/test_phase2f*.py` regression, run twice (after fixing a
classifier-corpus exemption regression caused by the `ingest_event` fix
legitimately changing both resolved `persona` and `tenant_direction`):

| Run | Result | Duration |
|---|---|---|
| A | 2526 passed, 0 failed, 0 errors, 38 warnings | 367.84s (0:06:07) |
| B | 2526 passed, 0 failed, 0 errors, 38 warnings | 341.96s (0:05:41) |

Collection grew from the 2519 baseline (Slice 2F-39A4) to 2526 (+7 —
this slice's new `test_phase2f39a5_final_decisions.py`). Identical,
clean results across both runs.

## Interim (pre-fix) run, for the record

An initial run before the classifier exemption fix showed 3 failures
(the same 3 files as Slice 2F-39A4's interim run:
`test_phase2f26f_alias_actor_scope.py`, `test_phase2f26g_family_precedence_ast_writes.py`,
`test_phase2f26h_tokenized_action.py`), 2523 passed, 335.39s. Root
cause: restricting `analytics.router::ingest_event` to `require_super_admin`
legitimately changed the live classifier's resolved values for
`/v1/analytics/events/ingest` on **both** fields —
persona `TENANT_PROVIDER_MUTATION` → `PLATFORM_ADMIN_MUTATION` and
`tenant_direction` `CLIENT_ASSERTED_TARGET_TENANT` → `GLOBAL_PLATFORM_SCOPE`
— unlike prior instances of this pattern, which only affected
`tenant_direction`. Fixed by extending the relevant exemption logic in
all 3 files (see the commit "Slice 2F-39A5: update 3 frozen classifier
corpora..."), not by weakening any frozen corpus's own historical labels.
`appointment.router::hold_slot`'s tenant check did not trigger a
classifier change (its resolved `tenant_direction` was unaffected by
this particular classifier script's evidence detection), so no
exemption was needed for that route.
