# Test Report — Slice 2F-9

## New backend test file
`tests/test_phase2f9_complaints_provider_authorization.py`
Command: `python -m pytest tests/test_phase2f9_complaints_provider_authorization.py -q`
Result: **84 passed**, 0 failed.

## Existing complaints/rework/refund domain regression
Command: `python -m pytest tests/test_module_l5_02_complaint_sla_job.py tests/test_module_l5_02_complaints_flow.py tests/test_module_l5_24_complaint_notify.py tests/test_sprint25_complaints.py -q`
Result: **52 passed, 1 skipped** (pre-existing skip, unrelated), 0 failed.

## Broader partition (complaints/rework/refund/permission/access-scope + full 2F family)
Command: `python -m pytest tests/ -q -k "phase2f or 2f5 or 2f6 or 2f7 or 2f8 or 2f9 or complain or rework or refund or module_l5_02 or module_l5_24 or sprint25 or access_scope or permission"`
Result: **1367 passed, 1 skipped**, 0 failed (run twice — once before, once after the additional `_get_settlement_proposal` fix — both green).

## Tooling verification
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.complaints.provider_router` → `total_routes: 9`, `unverified_count: 0`, exit 0.

## Frontend
`npx tsc --noEmit -p tsconfig.json` (in `frontend/tenant-portal`) — 0
errors attributable to the changed file
(`app/(tenant)/provider/complaints/[complaint_id]/page.tsx`).

Frontend linting: **not verified** (not "passed") — same pre-existing,
unrelated environment/tooling gap documented in Slices 2F-6B/2F-7/2F-8
(no ESLint v9 config, `next lint`'s CLI argument-parsing fails in this
environment).

## Files touched
- `app/engines/complaints/provider_router.py` — all 9 endpoints
  re-guarded with `require_tenant_owner_mutation`; `tenant_id` threaded
  through to the 5 fixed service calls.
- `app/engines/complaints/rework_service.py` — `_get_rework` (+ 3
  mutation methods + `get_rework`) now accept and enforce an optional
  `tenant_id`.
- `app/engines/complaints/refund_service.py` — `_get_refund` (+
  `provider_review_refund` + `get_refund`) same fix.
- `app/engines/complaints/complaint_service.py` — `create_settlement_proposal`
  now uses `provider_get_complaint` when `tenant_id` is supplied;
  `_get_settlement_proposal` now cross-checks `proposal.complaint_id`.
- `frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx` —
  4 mutation controls now conditionally rendered based on role/access-scope.
- `tests/test_phase2f9_complaints_provider_authorization.py` — new.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`,
  `tenant-mutation-endpoint-inventory.csv` — updated in place.
- 23 files under `docs/workflow-rearchitecture/phase-02a-slice-02f9/`: new.

No other production or test file was modified.
