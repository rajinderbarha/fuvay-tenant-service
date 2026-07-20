# Provider Quote Authorization

## The defect
Every mutation route in `provider_router.py` (which also defines the `staff_router` and `checklist_router` APIRouters — same file, same module) used only `Depends(get_current_user)` — no permission check, no role check, no mutation-scope check of any kind. Concretely, this meant:
- A `customer` account could call `POST /staff/quotes` and create a quote for any job (subject only to the tenant/job ownership check inside `create_quote`, which uses `str(user.tenant_id)` — for a customer this is typically `None`/falsy, so the call would likely fail downstream, but the AUTHORIZATION layer itself did not deny the customer persona at all).
- A `technician` (who has no quote-administration permission grant anywhere in `ROLE_PERMISSIONS`) could create/edit/delete quote items, send quotes to customers, or cancel quotes for jobs in their OWN tenant.
- A cross-tenant `staff`/`tenant_owner` could do the same for jobs in **their own** tenant (tenant scoping is real, via `user.tenant_id`, but the identity check for WHO may act was completely absent).
- A read-only tenant-scoped account (`access_scope="customer_support_limited"`) had no access-scope denial at all.

## The fix
All 11 mutation routes (`provider_cancel_quote`, `staff_create_quote`, `staff_add_item`, `staff_update_item`, `staff_remove_item`, `staff_send_to_customer`, `staff_mark_revised`, `staff_cancel_quote`, `staff_create_checklist`, `staff_update_checklist_item`, `staff_complete_checklist`) now use `require_owner_or_office_staff_mutation` — an existing dependency (`app/core/permissions.py`, introduced Slice 2F-6A), no new role or permission created.

## Why this dependency, not `require_staff_or_above_mutation`
`require_owner_or_office_staff_mutation` admits `{super_admin, tenant_owner, staff}` and deliberately **excludes technician**, whereas `require_staff_or_above_mutation` would additionally admit technician. Per this slice's mission ("Do not automatically grant quote administration to technicians. Technician quote input is allowed only when proven and assignment-limited"), a frontend/mobile caller search was performed first (see `frontend-mobile-exposure-audit.md`): only `frontend/tenant-portal/lib/api.ts` (a web, staff/office application) calls any `/staff/quotes` or `/staff/checklists` route. No mobile/technician app caller was found. This is exactly the evidence threshold `require_owner_or_office_staff_mutation`'s own docstring establishes for choosing it over the broader dependency ("do not infer technician access merely because an existing guard happens to admit it").

## What remains enforced underneath (unchanged)
- Tenant ownership: `_assert_tenant`/direct `tenant_id` comparison inside every service method (unchanged, pre-existing, re-verified).
- Job ownership at creation: `create_quote`'s `job.tenant_id == tenant_id` check (unchanged, pre-existing).
- Read-only tenant access_scope denial: `require_owner_or_office_staff_mutation`'s own built-in check (same mechanism as every other `*_mutation` dependency in this codebase).
- `super_admin` exemption from the read-only check (same mechanism, unchanged).

## Customer routes cannot reach these
`require_owner_or_office_staff_mutation` explicitly excludes `role == "customer"` — a customer calling any of these 11 routes is denied `PERMISSION_DENIED` before the handler body executes.
