# D-09 Regression Report — Slice 2F-26H

`POST /v1/tenants/{tenant_id}/engines/bulk-disable`:
tokens include `bulk` and `disable`; `disable` → `deactivate`; POST does not
override with create; family `tenant_governance`; persona
`TENANT_PROVIDER_MUTATION`; direction `PRINCIPAL_TENANT`; action `deactivate`.

Counter-tests (no blanket inversion): create/confirm/resend/recalculate/delete
endpoints keep their actions; `get_export_job` and `get_disabled_count` nouns
are not read as verbs. All in `tests/test_phase2f26h_tokenized_action.py`; the
D-09 route is a permanent regression fixture (`A15`).
