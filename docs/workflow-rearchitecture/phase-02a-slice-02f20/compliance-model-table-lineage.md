# Compliance Model and Table Lineage

## `ComplianceRequest` (table `compliance_requests`)
- PK: `id` (UUID, inherited `ServiceOSBase` pattern).
- **No conventional `tenant_id` column** — tenant ownership evidence
  classification: **`SERVER_OWNED_METADATA_TENANT`** (this slice's fixes
  make the `metadata_json["tenant_id"]` key server-owned end-to-end — set
  atomically at creation, only ever read/compared, never client-writable).
- `subject_type`/`subject_id`: not null, server-derived at creation from
  the authenticated caller (provider/customer routers) — classification
  **`PRINCIPAL_DERIVED`**.
- `status`: default `"submitted"`, drives the state machine (see
  `compliance-request-state-machine.csv`).
- `assigned_to_admin_id`: nullable UUID, no FK constraint — admin-side
  assignment field, not touched by any of the 6 selected routes.
- `metadata_json`: JSONB, default `dict`, not null — carries
  `tenant_id`/`related_tenant_id`/`actor_user_id`/`tenant_responses`/
  `tenant_action_required` — an ad hoc, unschema'd but now consistently
  server-controlled structure (see `compliance-metadata-tenant-integrity.md`).
- No FK constraints anywhere on this model.
- Indexes: `subject_id`, `status`, `request_type`, `sla_status`, `due_at`
  — **no index on `metadata_json`**, so every tenant-scoped query in
  `provider_router.py` is an unindexed JSONB scan (a performance
  characteristic, not a security gap — flagged in `known-limitations.md`).

## `ComplianceExport` (table `compliance_exports`)
- PK: `id`.
- `request_id`: nullable UUID, `ForeignKey("compliance_requests.id",
  ondelete="SET NULL")` — the ONLY FK on either table this slice touches.
  Tenant ownership evidence classification: **`PARENT_DERIVED_TENANT`**
  (transitively via `request_id → ComplianceRequest.metadata_json["tenant_id"]`).
  Because the FK is `ON DELETE SET NULL`, an export whose parent request
  is deleted becomes permanently un-scopable (correctly denies all access
  going forward via the existing tenant-join check, not a security hole,
  but an orphaning behavior — flagged in `known-limitations.md`).
- `subject_type`/`subject_id`: not null, copied from the parent
  `ComplianceRequest` at export-creation time — classification
  **`PARENT_RECORD_DERIVED`**.
- `status`: default `"pending"` — `generate_export` sets it to
  `"processing"`; nothing else in this codebase ever advances it further
  except the unrelated admin `process_request` path, which creates a
  SEPARATE export row (see `compliance-export-retry-concurrency.md`).
- No `tenant_id` column, direct or indirect beyond the `request_id` FK.

## `ConsentRecord` (table `consent_records`, `app/engines/compliance/models.py`)
- Has BOTH `user_id` (not null) and `tenant_id` (nullable, indexed via
  `ix_cr_tenant`) as real columns — tenant ownership evidence
  classification: **`DIRECT_TENANT_COLUMN`** (this is the one table in
  this module that actually has a proper column; the pre-2F-20 defect was
  that `revoke_consent` never populated it, not that the column didn't
  exist).
- `action`: enum-like string (`GRANTED`/`WITHDRAWN`), no separate request
  linkage — a consent record stands alone, not tied to a
  `ComplianceRequest`.

## `ComplianceAuditLog` (append-only)
- Has `tenant_id` (nullable), `user_id`, `actor_id`, `actor_role`,
  `actor_ip`, `action`, `reference_id`, `legal_basis`, `meta` — this table
  was ALREADY correctly populated with the real tenant_id by every
  `_audit(...)` call in `provider_router.py` (confirmed unchanged,
  pre-2F-20 behavior was already sound here — only `ConsentRecord` and the
  request-creation metadata had the defects this slice fixes).

## `ComplianceRequestItem` (table `compliance_request_items`)
- FK `request_id → compliance_requests.id ON DELETE CASCADE`, not null —
  the one properly-cascading FK in this module. Not touched by any of the
  6 selected routes.

## No tenant object may remain with unadjudicated authority
Every model this module's 6 selected routes touch (`ComplianceRequest`,
`ComplianceExport`, `ConsentRecord`) now has an explicit, adjudicated
tenant-ownership classification above — none remain `MISSING`,
`MALFORMED`, or `CLIENT_CONTROLLED_UNSAFE`.
