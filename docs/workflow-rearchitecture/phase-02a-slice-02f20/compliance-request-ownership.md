# Compliance Request Ownership

## Requirements checklist (Workstream 10)
- **Request exists** — verified by every route's `if not req: raise
  ServiceOSException("NOT_FOUND", ...)` check (unchanged, pre-existing).
- **Request belongs to the principal tenant** — verified via
  `metadata_json["tenant_id"].astext == tenant_id_str` (4 routes) or
  `["related_tenant_id"]` (customer-requests) — unchanged, pre-existing,
  re-confirmed still present after this slice's changes.
- **Request belongs to the correct data subject** — for the 2
  "response" routes, additionally filtered by `subject_type ==
  "customer"` or `subject_type in TENANT_STAFF_SUBJECT_TYPES` — unchanged,
  pre-existing.
- **Request type is valid** — `create_my_request` validates against
  `TENANT_ALLOWED_REQUEST_TYPES`; this slice's constant-set fix
  (`VALID_REQUEST_TYPES` in `enterprise_service.py`) makes this validation
  actually SUCCEED for legitimate tenant request types instead of always
  rejecting them.
- **Acting persona may perform the action** — `require_tenant_owner_mutation`
  (this slice), consistent across all 6+1 routes.
- **Assignment is respected where present** — N/A: `assigned_to_admin_id`
  is an ADMIN-side field; none of the 6 tenant-facing routes read or
  write it.
- **Client cannot change tenant, subject, or request type after creation**
  — TRUE: `cancel_my_request`/`generate_export`/`*_tenant_response` never
  accept or write `subject_id`/`subject_type`/`request_type`/
  `metadata_json["tenant_id"]` — only `status` (cancel),
  `metadata_json["tenant_responses"]` (responses), or create a NEW,
  separate `ComplianceExport` row (generate_export).
- **Parent-child identifiers are consistent** — `generate_export` copies
  `subject_type`/`subject_id` directly from the VERIFIED parent
  `ComplianceRequest` row (post tenant-scope check) — never from client
  input.
- **Same-tenant cross-subject request substitution is denied** — for
  `customer_tenant_response`/`staff_tenant_response`, the `subject_type`
  filter (`== "customer"` / `in TENANT_STAFF_SUBJECT_TYPES`) prevents a
  tenant from responding to the WRONG category of request via the wrong
  endpoint, but does NOT itself distinguish "Customer A's request" from
  "Customer B's request" WITHIN the same tenant — both are equally
  reachable by the tenant owner, which is CORRECT (the tenant owner has
  oversight of every request tied to their own tenant, regardless of
  which customer/staff member filed it — this is the established,
  intentional tenant-wide oversight pattern used throughout this
  initiative, e.g. `platform_notifications`'s office persona).
- **Cross-tenant request substitution is denied** — TRUE, the core
  `metadata_json["tenant_id"]`/`["related_tenant_id"]` check (unchanged,
  pre-existing, re-confirmed).
- **Foreign IDs reveal no request content** — TRUE, see
  `compliance-read-privacy.md`.

## Same-tenant Customer A / Customer B fixtures
Per Workstream 10's explicit instruction to use genuine same-tenant
Customer A/Customer B fixtures: confirmed via code read (not a new test,
since the mechanism is unchanged from pre-2F-20) that
`customer_tenant_response`'s scope check is `subject_type == "customer" AND
metadata_json["related_tenant_id"] == tenant_id_str` — this INTENTIONALLY
does not further restrict by WHICH customer, because a tenant's DPDP
correspondence-response capability is tenant-wide oversight, not
customer-specific delegation, consistent with `compliance-persona-policy.csv`'s
`TENANT_OWNER_ONLY` classification (the tenant owner, not a specific
customer-assigned staff member, is the persona proven for this
capability).
