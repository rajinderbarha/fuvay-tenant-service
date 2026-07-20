# Alternate Checklist Route Audit — Slice 2F-13 (Workstream 16)

## Search
Repository-wide grep for every reader/writer of `ServiceChecklistTemplate`
/ `ServiceChecklistItem` and equivalent checklist/completion capabilities.

## Findings

| Route/method | Model | Persona/guard | Mutation? | Reaches same record? | Disposition |
|---|---|---|---|---|---|
| `checklist_router` 6 mutations (this slice) | ServiceChecklistTemplate/Item | tenant_owner via FIELD_OPS_CHECKLIST_MANAGE, now scope-aware + ownership-fixed | yes | yes | CANONICAL_TEMPLATE_WRITE |
| `admin_catalog.bulk_setup_router::get_available_checklist_templates` | ServiceChecklistTemplate | `require_super_admin` (platform-only) | **no (GET read)** | yes (reads all active templates cross-tenant) | ALTERNATE_PROTECTED — platform-admin read, correctly super_admin-gated; intentionally cross-tenant (super_admin is the platform exemption); not a weaker mutation route |
| `booking.service.py` `catalog_item.checklist_template` | catalog item JSONB field (list of step strings) — **NOT** the ServiceChecklistTemplate model | tenant booking flow | reads catalog field to seed job items | NO — distinct concept (a JSONB list on the catalog item, not the template model) | DISTINCT_CAPABILITY / DISCONNECTED from this router's model |
| `field_ops.service.py` / `staff_router` job checklist execution | `JobChecklistItem` (distinct model) | technician/staff job-execution guards | yes (job snapshot) | NO — different model/table | DISTINCT_CAPABILITY — out of scope (job execution surface) |
| quote_checklist (`JobQuote` + FieldOpsService) | JobQuote | customer/staff quote flow | yes | NO — different model | DISTINCT_CAPABILITY (canonical customer quote workflow, preserved) |

## No weaker alternate mutation route reaching the same records
The only routes that MUTATE `ServiceChecklistTemplate`/`ServiceChecklistItem`
are `checklist_router`'s 6 (now fully protected). The only alternate
READER is a `require_super_admin` platform tool (correctly stronger/
platform-only). No weaker live route reaches the same records with a
laxer guard.

## No merge
No distinct checklist/quote/completion model was merged.
