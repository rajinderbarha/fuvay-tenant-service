# Slice 2F-13 Implementation Summary

## Scope
Authorization, tenant-ownership and template-item-integrity closure for
`app.engines.field_ops.checklist_router` — 9 mounted routes (6 mutations
+ 3 reads).

## Architecture finding (load-bearing)
`checklist_router` is a **tenant checklist-TEMPLATE CRUD** router
(prefix `/v1/tenant/checklist-templates`) operating on two models only:
- `ServiceChecklistTemplate` (`service_checklist_templates`) — a
  tenant-owned, catalog-style checklist template keyed to a catalog
  `service_id` (NOT to a job).
- `ServiceChecklistItem` (`service_checklist_items`) — its line items.

It is **template administration**, not per-job checklist execution. The
per-job execution snapshot (`JobChecklistItem`, `job_checklist_items`,
keyed to `job_id`, carrying `requires_photo` evidence flags and driving
job-completion gating) is a **DISTINCT model** mutated by
`field_ops.service.py` / `field_ops.staff_router` — both **out of scope**
("do not begin field_ops.staff_router"). The linked job pipeline is
`field_ops.Job` (its own `jobs` table), **not** ServiceJob — no
Booking/ServiceBooking/Job/ServiceJob adapter exists or was introduced.
Every mission workstream targeting technician execution, provider
verification, customer decisions, evidence/media, and the job-completion
gate is therefore `UNSUPPORTED_CAPABILITY` **in this router** and belongs
to the out-of-scope job-execution surface — reported honestly, not
fabricated.

## Two conclusively-proven defects fixed
1. **Access-scope gap (all 6 mutations)** — routes used
   `require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)`, which enforces the
   permission but not tenant read-only access scope
   (`PERMISSION_ONLY_NOT_SCOPE_AWARE`). A read-only tenant_owner
   (`access_scope='customer_support_limited'`) carrying the permission
   could still mutate templates. **Fixed** by swapping the 6 mutation
   guards to `require_tenant_mutation_permission(P.FIELD_OPS_CHECKLIST_MANAGE)`.
   The 3 read routes keep `require_permission` (read-only users must
   still read). No permission was created — `FIELD_OPS_CHECKLIST_MANAGE`
   is tenant_owner-only by default role grant (+ super_admin via P.ALL).
2. **Cross-tenant IDOR in `ChecklistTemplateService._get_template_for_tenant`**
   — the tenant-ownership check fired **only** when
   `actor_role == "tenant_owner"`. Since a `staff` member can be granted
   `FIELD_OPS_CHECKLIST_MANAGE` via a StaffPermission override, such a
   staff actor skipped the tenant filter entirely and could
   read/update/delete/add-item on **any tenant's** template by ID.
   **Fixed** to enforce tenant ownership for every tenant-scoped actor
   (all roles except super_admin, the intentional platform exemption),
   with the same fail-closed `CHECKLIST_TEMPLATE_NOT_FOUND` (no
   existence leak).

## What changed
1. `app/engines/field_ops/checklist_router.py` — 6 mutation guards →
   `require_tenant_mutation_permission`.
2. `app/engines/field_ops/checklist_template_service.py` —
   `_get_template_for_tenant` ownership check made role-agnostic
   (non-super_admin).
3. New test file
   `tests/test_phase2f13_checklist_template_authorization.py` (17 tests).
4. Global-coverage CSVs updated (6 rows: `PERMISSION_ONLY_...` →
   `TENANT_MUTATION_PERMISSION_SCOPE_AWARE`).

## Already-correct behavior (verified, unmodified)
- Item→template parent cross-check (`_get_item_for_template` rejects an
  item whose `template_id` ≠ the supplied template).
- `create_template`'s duplicate guard (409 on same name+service).
- `delete_template` soft-deletes and explicitly never touches historical
  `job_checklist_items` (snapshot integrity).
- super_admin body-`tenant_id` override on `create_template` (existing
  platform pattern, principal-bound for everyone else).

## What did NOT change
No per-job checklist / completion-gate / evidence / job-lifecycle code;
`field_ops.service.py`, `field_ops.staff_router`, `field_ops.Job`,
`JobChecklistItem`, PartsRequest, quote_checklist, and all prior closures
are unmodified. No permission or role created. No booking-pipeline merge.
`readonly@` and migration 144 untouched.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
see `approval-gate.md`. Tenant mutation coverage **125/182 → 131/182**
(+6, all already in the denominator).
