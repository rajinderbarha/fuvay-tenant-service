# Technician Persona Decision — Workstream 2

## Method
For each of the 4 capabilities, checked: frontend/mobile callers,
existing technician workflow (ServiceJob execution pipeline, already
closed in Slice 2F-3B), existing tests, permission registry, audit
events, and business rules (Parts/quote-approval precedent).

## Findings

### Recording an on-site payment (`provider_record_payment`)
- **Frontend/mobile callers**: only `frontend/tenant-portal` (web,
  owner+staff) calls `/v1/provider/service-invoices/{id}/record-payment`.
  Zero callers found in `mobile/staff-app` (grep across
  `mobile/staff-app/src` for `service-invoices` or `record-payment`
  returned nothing).
- **Existing technician workflow**: `FIELD_OPS_JOBS_CLOSE`'s permission
  comment ("Record direct customer payment + close own jobs") describes
  a *different* code path — the `field_ops`/`home_service_assignment`
  job-closing pipeline (already closed in Slice 2F-3B), not this
  `invoice_payment` module. No evidence connects that permission's grant
  to *this* endpoint.
- **Decision: TENANT_OWNER_OR_CANONICAL_STAFF** (not `TECHNICIAN_ALLOWED`;
  corrected in Slice 2F-6B — this document previously used the label
  "STAFF_ONLY," which was ambiguous and could be misread as excluding
  tenant_owner. The guard itself was always correct:
  `require_owner_or_office_staff_mutation` admits
  `{super_admin, tenant_owner, staff}`, excluding `technician`).

### Creating an invoice (`staff_create_invoice`)
- Same evidence as above: zero mobile/staff-app callers; only
  tenant-portal web.
- **Decision: TENANT_OWNER_OR_CANONICAL_STAFF.** Same guard.

### Adding an invoice item (`staff_add_invoice_item`)
- Same evidence.
- **Decision: TENANT_OWNER_OR_CANONICAL_STAFF.** Same guard.

### Issuing an invoice (`provider_issue_invoice`)
- Already `TENANT_OWNER_ONLY` since Slice 2F-6 (`FIELD_OPS_INVOICE_GEN`
  granted only to `tenant_owner`). Re-confirmed this slice — no evidence
  found to broaden or narrow this further.
- **Decision: TENANT_OWNER_ONLY** (unchanged).

## Guard used
Created `require_owner_or_office_staff_mutation` in
`app/core/permissions.py` — admits `{super_admin, tenant_owner, staff}`,
denies `technician`, and applies the same read-only `access_scope` denial
as every other `*_mutation` guard in this file. This is a composed
dependency built from canonical roles and the existing access-scope
mechanism, not a new permission or a new role — consistent with "if the
repository cannot safely distinguish staff from technician using an
existing guard, create one small composed dependency."

## Why not `require_staff_or_above_mutation`
That dependency's role set (`{super_admin, tenant_owner, staff,
technician}`) was designed for `ServiceJob` execution/assignment
endpoints (Slice 2F-3B), where a technician acting on their own assigned
job is the norm. `invoice_payment.provider_router` is a different,
web-only back-office tool with no technician-facing client anywhere in
the repository — reusing that guard here would have been "inferring
technician access merely because an existing guard happens to admit it,"
which the mission explicitly warns against.

## What was NOT done
No new permission was granted. No new role was introduced. Tenant-owner
access was not removed from any of the 3 routes.
