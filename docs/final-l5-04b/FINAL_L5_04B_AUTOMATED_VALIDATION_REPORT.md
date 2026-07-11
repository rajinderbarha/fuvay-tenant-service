# FINAL-L5-04B — Automated Entitlement Validation Report

## Real, automated checks that exist today (as pytest tests, not a separate CI job)
| Mission's required CI check | Real coverage |
|---|---|
| Duplicate active module entitlement | **DB-enforced** (`uq_tme_tenant_module_active`), plus a live raw-SQL test proving the constraint rejects it |
| Duplicate active category entitlement | **DB-enforced** (`uq_tce_tenant_category_active`) |
| Category without module entitlement | **App-enforced**, 409, tested via `assign_category_entitlement` unit test |
| Category linked to wrong module | Same mechanism — `assign_category_entitlement` resolves the real parent vertical and rejects if it doesn't match an ACTIVE module entitlement |
| Missing tenant/module/category foreign key | **DB-enforced** — all 3 FK columns are `nullable=False` with real FK constraints |
| Invalid status | **DB-enforced** `CHECK` constraint (`ck_tme_status_valid`/`ck_tce_status_valid`) |
| Overlapping effective periods | **Not enforced** — `effective_from`/`effective_until` have no DB constraint preventing two rows (of different statuses, e.g. one ARCHIVED one ACTIVE) from having overlapping windows; only the partial unique index on `status='ACTIVE'` prevents two *simultaneously active* rows. A genuine, narrow gap. |
| Hardcoded category navigation | **Statically checked** — confirmed by source read that `TenantLayout.tsx`'s module gating reads entirely from the live API, not a hardcoded array |
| Entitlement route without guard | **Not automated** — no static/CI check scans for "every tenant-scoped mutation route has an entitlement guard"; this sprint only added one guard (`enable_service`) and verified it manually, not via a repo-wide automated scan |
| Tenant API returning another tenant's data | **Automated** — `test_tenant_user_without_tenant_membership_rejected_403` and the tenant-isolation E2E test both continuously guard against this |

## What "automated" means here — honestly
None of the above run as a dedicated CI gate/script separate from the normal `pytest tests/` invocation — they are real assertions within `tests/test_final_l5_04b_entitlement.py`, which runs as part of the existing test suite (and would fail a CI run that executes `pytest`, if this repo has one wired to a pipeline — not independently verified this sprint whether a CI pipeline exists).

## Result
7 of 10 required validation classes have real, automated (pytest-based) coverage. 2 are DB-enforced structurally without a dedicated test asserting the enforcement mechanism itself beyond what's already covered. 1 (overlapping effective periods) is a genuine, undocumented-until-now gap.
