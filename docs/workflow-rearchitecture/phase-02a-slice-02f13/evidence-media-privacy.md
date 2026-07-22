# Evidence / Media / Privacy — Slice 2F-13 (Workstream 13/22)

## No evidence/media in this router
`checklist_router` stores **no evidence or media**. The only
"photo/note" concept is the template boolean flags
`ServiceChecklistItem.requires_photo` / `requires_note` — declarations of
what a future job checklist will require, not stored files. There is no
`ChecklistEvidence` model and no upload route here. Actual job photos are
`JobMedia` on the out-of-scope job surface.

## PII / privacy in this router
- `ServiceChecklistTemplate` (`name`, `description`, `service_id`,
  `tenant_id`) and `ServiceChecklistItem` (`title`, `description`, flags)
  contain **no customer/student PII** — they are tenant-authored catalog
  definitions.
- **Tenant isolation on reads (fixed + verified)**: `list_templates`
  filters by principal tenant; `get_template` and `list_items` now both
  enforce `_get_template_for_tenant` (the standalone `list_items`
  cross-tenant read leak was closed this slice). No cross-tenant read of
  another tenant's template names/items remains.
- **No public route**: every route requires `FIELD_OPS_CHECKLIST_MANAGE`
  (tenant_owner/super_admin) — nothing is unauthenticated/public, so no
  public checklist data leak exists.
- **No provider-internal-vs-customer distinction**: there is no customer
  route in this module, so no "internal notes leaking to customer"
  surface exists here.

## Conclusion
Privacy is closed for this router: no PII, no media, no public exposure,
tenant-isolated reads (with the read-IDOR fix). Customer/technician
evidence privacy for the per-job surface is out of scope.
