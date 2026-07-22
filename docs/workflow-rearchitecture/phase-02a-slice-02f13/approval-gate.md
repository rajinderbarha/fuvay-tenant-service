# Approval Gate — Slice 2F-13

## Status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Architecture finding (load-bearing)
`field_ops.checklist_router` is a **tenant checklist-TEMPLATE CRUD**
router (`ServiceChecklistTemplate` + `ServiceChecklistItem`, keyed to a
catalog `service_id`) — 6 mutations + 3 reads. Per-job checklist
execution (`JobChecklistItem`), technician execution, provider
verification, customer decisions, evidence/media, and the job-completion
gate are a **DISTINCT model** on the out-of-scope
`field_ops.service.py`/`staff_router` surface. The linked job pipeline is
`field_ops.Job`, NOT ServiceJob. Every workstream targeting those
capabilities is honestly reported as `UNSUPPORTED_CAPABILITY` in this
router.

## Reasoning

### SECURITY_CLOSED: YES
- All 6 template mutations now use
  `require_tenant_mutation_permission(P.FIELD_OPS_CHECKLIST_MANAGE)`
  (was `require_permission`, `PERMISSION_ONLY_NOT_SCOPE_AWARE`) — read-only
  tenant scope is denied; wrong personas (technician/customer/guest/staff-
  without-override) denied by the permission; unknown roles fail closed.
  Reads keep `require_permission` (read-only users must read). No
  permission created (`FIELD_OPS_CHECKLIST_MANAGE` is tenant_owner-only by
  default).
- **Cross-tenant IDOR fixed**: `_get_template_for_tenant` enforced
  ownership only for `actor_role == "tenant_owner"`, letting an
  override-granted `staff` reach any tenant's template by ID. Now enforced
  for every tenant-scoped actor (super_admin exempt), fail-closed
  NOT_FOUND.
- **Read IDOR fixed**: the standalone `list_items` route reached the
  service without an ownership check (cross-tenant read of item titles);
  now ownership-checked.
- Item→template parent integrity enforced (`_get_item_for_template`).
- No weaker alternate route reaches the same records (the only alternate
  reader is a `require_super_admin` platform tool). Zero unverified routes
  (6/6). Direct tests pass (19).

### DOMAIN_INTEGRITY_CLOSED: YES
Template soft-delete/edit never touches historical `job_checklist_items`
(copied snapshots — historical integrity preserved). Duplicate template
name rejected (409); duplicate item title allowed (benign). Soft-deleted
rows cannot be re-mutated. Concurrent duplicate-create is a documented
benign risk. No completion-gate/versioning/technician-execution capability
exists here to break; the out-of-scope job gate cannot be bypassed by a
template edit (no propagation).

### PRIVACY_CLOSED: YES
Templates carry no customer PII; all routes require the permission (no
public route); reads are tenant-isolated (with the `list_items` read-IDOR
fix). No media/evidence in this router.

### PRODUCT_POLICY_CLOSED: BLOCKED
Non-security product questions remain: default staff grant of
`FIELD_OPS_CHECKLIST_MANAGE`, template versioning/immutability,
duplicate-create constraint hardening, and the out-of-scope job-execution
surface's own authorization (`field_ops.staff_router`, a future slice).
See `product-decisions-required.md`. None block security/integrity/
privacy.

## Final combined status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Quality gates (68) — summary
All satisfied for this router's scope. Gates targeting capabilities that
do not exist in this router (technician execution, provider verification,
customer decision, completion gate, evidence/media, versioning, bulk/
reorder) are satisfied honestly as `UNSUPPORTED_CAPABILITY` with the
boundary documented (`job-pipeline-boundary.md` and the per-workstream
docs), not fabricated. Evidence across the other 28 files.

## Global coverage
Tenant mutation coverage **125/182 → 131/182** (+6, all already in the
denominator). `global-coverage-update.md`.

## Stop condition honored
Only `checklist_router.py` (6 guard swaps) and `checklist_template_service.py`
(2 ownership fixes) were modified, plus the 2 global CSVs, 1 new test
file, and this slice's docs. No per-job checklist / `field_ops.service.py`
/ `field_ops.staff_router` / `field_ops.Job` / `JobChecklistItem` /
PartsRequest / quote_checklist / prior-closure code was touched. No
permission or role created. No booking-pipeline merge. `readonly@` and
migration 144 untouched. No visual redesign. **Stopping here per
instruction — not beginning `field_ops.staff_router` or any other
module.**
