# Metadata Tenant Integrity — Writer Audit

## Every writer of `ComplianceRequest.metadata_json`
1. **`ComplianceEnterpriseService.create_request`** (THIS SLICE) — now the
   ONLY writer that CREATES the `tenant_id` key, setting it atomically at
   INSERT time from the caller-supplied `data["metadata_json"]` dict —
   which is itself always server-constructed by the calling router
   (`provider_router.create_my_request` builds it from `u.tenant_id`/
   `u.user_id`, never from raw client JSON fields).
2. **`provider_router.customer_tenant_response`/`staff_tenant_response`**
   — read-modify-write on the `tenant_responses` list key only; NEVER
   touch the `tenant_id`/`related_tenant_id` keys (confirmed by code read
   — both do `{**meta, "tenant_responses": tenant_responses}` style merges
   that only ever ADD to the responses array, never replace the whole
   dict or remove other keys).
3. **No admin route writes `ComplianceRequest.metadata_json` at all** —
   confirmed by grep across `admin_router.py`; admin operates via the
   real `status`/`admin_notes`/`rejection_reason` COLUMNS, never the
   JSONB metadata.
4. **No worker/background job writes `ComplianceRequest.metadata_json`**
   — `app/jobs/compliance_sla.py` only touches `status`/`sla_status`
   columns, never metadata_json.

## Requirements checklist
- **Client input cannot supply tenant scope** — TRUE: no route accepts a
  `tenant_id`/`metadata_json` field from the request body at all; the
  ONLY body fields ever read are `reason`/`response`/
  `confirm_understanding`/`details`/`request_type` (verified across all 6
  route handlers).
- **Client input cannot replace metadata entirely** — TRUE: every writer
  uses a `{**existing, "key": new_value}` merge pattern (this slice's
  `create_request` fix uses a fresh dict only at CREATE time, when no
  prior metadata exists to preserve — there is nothing to "replace"),
  never a blind overwrite of an EXISTING row's metadata_json.
- **Workers preserve tenant scope** — N/A, no worker writes this field at
  all (see above).
- **Admin routes cannot alter tenant scope** — TRUE structurally (admin
  never touches metadata_json).
- **Import/migration code cannot omit it** — N/A, no import/migration
  code exists for this table in this codebase.
- **Malformed values are not accepted** — the WRITE side always
  constructs `metadata_json["tenant_id"]` as `str(u.tenant_id)` (a UUID
  string) — never accepts a malformed value by construction.
- **Tenant scope cannot be deleted** — TRUE: no route or service method
  ever does `del metadata_json["tenant_id"]` or reassigns the dict without
  it; confirmed by code read of all writers.
- **Another tenant cannot be substituted** — TRUE: `tenant_id` is always
  `u.tenant_id`-derived at the ONE writer that sets it (`create_request`),
  never client-suppliable, never touched by any OTHER writer afterward.

## Metadata tampering — directly tested
`test_provider_router_no_longer_does_post_creation_metadata_update`
(this slice's test suite) proves the prior two-step
create-then-separately-patch pattern is gone — confirming there is no
longer a window where an UNSCOPED request row briefly exists that a
concurrent read could observe.
