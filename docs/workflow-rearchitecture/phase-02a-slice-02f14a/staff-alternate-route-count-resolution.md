# Staff/Alternate Route Count Resolution

## staff_router: exactly 6 mounted mutations (unchanged)

Confirmed via a fresh run of `scripts/workflow_rearchitecture/inventory_mutation_routes.py
--module app.engines.field_ops.staff_router`: `total_mutation_routes: 6`, all 6
`STAFF_EXECUTION_ROLE_SCOPE_AWARE`. No GET routes, no duplicates, no aliases counted.

## field_ops.router: exactly 28 mounted mutations (unchanged count, guard statuses updated)

Confirmed via a fresh run of the same tool against `app.engines.field_ops.router`:
`total_mutation_routes: 28`.

## The "7 vs 9" discrepancy — resolved, not a contradiction

Slice 2F-14's implementation-summary said "7 alternate functions"; its approval-gate said "9
same-capability alternates." Both numbers were correct descriptions of different subsets that
were conflated without explanation:

- **7** = the routes gated with `require_staff_or_technician_only` specifically
  (`accept_job`, `reject_assignment`, `start_checklist`, `update_checklist_item`,
  `complete_checklist`, `submit_findings`, legacy `update_checklist`).
- **9** = that same 7, plus `assign_job` and `update_status`, which were fixed with a
  *different* dependency (`require_tenant_mutation_permission`) because they are tenant-owner
  operations, not technician self-execution. 7 + 2 = 9.

Both counts are accurate; the 2F-14 documentation simply never stated the distinction. This is
recorded as a documentation defect, not a route-count error — no route was double-counted, and no
GET/duplicate/alias route was ever included in either figure.

## This slice's additional fixes (bringing router's tool-verified-protected count from 9 to 17)

- `start_assessment`, `complete_assessment` — added `require_staff_or_technician_only`
  (2 routes).
- `close_job`, `generate_invoice`, `record_payment`, `deduct_commission`, `financial_close`,
  `void_job` — upgraded to `require_tenant_mutation_permission` (6 routes).

9 (2F-14) + 2 + 6 = 17 of 28 tool-verified-protected on `field_ops.router`. Combined with
staff_router's 6/6, the field_ops-specific total is **23 of 34** tool-verified route-level
guards (plus the JobNote/JobMedia service-level ownership fixes, which are real but not
tool-visible — see jobnote-access-control.md, jobmedia-access-control.md).
