# Alternate Completion / Finalization Audit

## Routes traced

`start_assessment`, `complete_assessment`, `close_job`, `void_job`, `financial_close`,
`update_status` (both staff_router and field_ops.router copies), plus the service methods they
call (`FieldOpsService.start_assessment/complete_assessment/void_job/update_status`,
`BillingService.close_job_financial/generate_invoice/record_payment/deduct_commission/financial_close`).

## Per-path findings

| Path | Legal source states | Result state | Persona | Access-scope | Tenant | Assignment | Checklist predicate | Financial | Same Job row |
|---|---|---|---|---|---|---|---|---|---|
| `start_assessment` | ARRIVED | ASSESSMENT_STARTED | staff/technician | n/a | n/a | assigned_staff_id==actor | n/a | no | yes |
| `complete_assessment` | ASSESSMENT_STARTED | ASSESSMENT_COMPLETE | staff/technician | n/a | n/a | assigned_staff_id==actor | n/a | no | yes |
| `update_status` -> WORK_COMPLETE | CHECKLIST_COMPLETE (if checklist_required) | WORK_COMPLETE | tenant_owner/staff/technician | scope-aware (2F-14) | `_assert_can_access_job` | `_assert_assigned` | **CHECKLIST_COMPLETE required** | no | yes |
| `close_job` | PAID | CLOSED | tenant_owner/staff/technician (own job) | scope-aware (fixed 2F-14A) | `_get_job_for_billing` | `_get_job_for_billing` | not applicable (billing phase, after WORK_COMPLETE) | yes | yes |
| `financial_close` | SIGNED_OFF/COMPLETED (via generate_invoice) -> PAID -> CLOSED | CLOSED | tenant_owner/staff/technician (own job) | scope-aware (fixed 2F-14A) | `_get_job_for_billing` | `_get_job_for_billing` | not applicable | yes | yes |
| `void_job` | any non-TERMINAL, non-LOCKED status | VOIDED | tenant_owner/super_admin | scope-aware (fixed 2F-14A) | `_get_job_for_assignment` (fixed 2F-14A — was previously UNCHECKED) | n/a | none — voiding is an abandonment path, not a completion path | no | yes |

## Classification

- `start_assessment`/`complete_assessment`: **CANONICAL_JOB_EXECUTION_TRANSITION** (same
  execution class as accept/reject/checklist; now consistently guarded).
- `update_status` -> `WORK_COMPLETE`: **CHECKLIST_GATE_APPLIES** (verified, unchanged, correct).
- `close_job`/`financial_close`: **TENANT_WIDE_PROVIDER_FINALIZATION** /
  **DISTINCT_FINALIZATION_PHASE** — these happen strictly after `WORK_COMPLETE`/`SIGNED_OFF` and
  do not re-open or bypass the checklist gate; they operate on the billing/financial phase of
  the same job, gated by `_get_job_for_billing`'s pre-existing ownership check.
- `void_job`: **CHECKLIST_GATE_NOT_APPLICABLE_BY_POLICY** — voiding is defined as an
  abandonment path available from any non-terminal, non-locked status (including before a
  checklist would ever start); repository evidence (`TERMINAL_STATUSES`/`LOCKED_STATUSES` guard)
  shows this is intentional, not a bypass of the checklist-completion path. The genuine defect
  here was authorization (cross-tenant IDOR), not checklist-gate bypass — fixed separately.

## Live bypass found and fixed

`void_job` was a live, same-Job authorization bypass (missing tenant ownership entirely) — fixed
this slice by reusing `_get_job_for_assignment`. No checklist-completion-gate bypass was found in
any of the routes traced.
