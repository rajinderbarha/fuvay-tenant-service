# Slice 2F-20 — Implementation Summary

## Mission
Investigate, classify, protect, and verify the 6 selected mutation routes
in `app.engines.compliance.provider_router`, plus every read/download
route and worker reaching the same `ComplianceRequest`/`ComplianceExport`/
`ConsentRecord` records.

## What was fixed

### 1. `withdraw_consent`'s `tenant_id=None` defect
`ComplianceEnterpriseService.revoke_consent` always hardcoded `tenant_id=None`
in its call to the underlying `withdraw_consent` service method, regardless
of caller — every consent-withdrawal `ConsentRecord` row ever written
through ANY of the three routers (provider, customer, admin) permanently
lost tenant attribution. Fixed: `revoke_consent` now accepts an optional
`tenant_id` parameter; `provider_router.withdraw_consent` passes the
caller's real, server-derived tenant_id (`uuid.UUID(tenant_id_str)`, never
client-supplied). `customer_router`'s and `admin_router`'s call sites are
UNCHANGED and correctly continue to pass no tenant_id — a customer
genuinely has none, and admin acts platform-wide across all tenants; only
the provider (tenant-scoped) call site had a genuine defect.

### 2. Non-atomic tenant-ownership stamping on request creation
`ComplianceEnterpriseService.create_request` silently dropped the
`metadata_json` key from its input `data` dict — the `ComplianceRequest(...)`
constructor call never set it. `provider_router.create_my_request` worked
around this with a SEPARATE post-creation SELECT+UPDATE to inject
`tenant_id` into `metadata_json` after the row already existed — a
non-atomic two-step write (briefly, an unscoped `ComplianceRequest` row
existed between INSERT and the follow-up UPDATE, within the same
transaction but as two distinct statements). Fixed: `create_request` now
accepts and sets `metadata_json` directly in the constructor — a request
row is NEVER persisted without its tenant-ownership metadata already
attached. The router's separate follow-up UPDATE was removed.

### 3. Router dependency: `require_tenant_owner` → `require_tenant_owner_mutation`
All 6 selected mutation routes, PLUS `download_export` (a state-mutating
GET reaching the same `ComplianceExport` record — flagged as a
same-record alternate-shape mutation), were upgraded from the bare-role
`require_tenant_owner` to the EXISTING `require_tenant_owner_mutation`
dependency (`app/core/permissions.py`) — same admitted role set
(`tenant_owner`, `super_admin`), PLUS the missing read-only-`access_scope`
denial. This dependency's own docstring explicitly names
"provider_portal-style mutation endpoint" as its intended use — a direct,
zero-role-set-change fit requiring no new permission. The 4 pure-read
routes in the same file (`list_staff_requests`, `get_staff_request`,
`list_customer_requests`, `get_customer_request`) were deliberately left
unchanged, per this slice's narrow scope.

### 4. Pre-existing, production-breaking validation defect (discovered while testing the above)
`ComplianceEnterpriseService.create_request`'s `VALID_SUBJECT_TYPES`/
`VALID_REQUEST_TYPES` allow-lists never included the literal
`subject_type`/`request_type` strings `provider_router.create_my_request`
has always constructed (`"tenant_business"`/`"tenant_owner"` and
`"business_data_export"`/`"business_profile_erasure"`/`"owner_data_export"`/
`"owner_data_erasure"`/`"staff_data_export"`/`"staff_data_erasure"`) —
meaning `create_my_request` has always raised `VALIDATION_ERROR` and
never actually succeeded in production. This was discovered because a
direct unit test of the (now correctly atomic) `create_request` path
immediately surfaced it. Fixed with the smallest safe correction: added
the 2 missing subject types and 6 missing request types to the existing
allow-lists — no schema change, no new values invented, only correcting
the allow-lists to match the vocabulary the route has used all along.
Without this fix, the tenant-ownership atomicity fix (#2) would be
protecting a route that could never successfully create a request at all.

## What was investigated and found NOT implemented (honestly disclosed)
- **Export-generation worker**: NO worker, Celery task, `BackgroundTasks`
  usage, or any other automation exists ANYWHERE in this codebase that
  transitions a `ComplianceExport` row from `"processing"`/`"pending"` to
  `"ready"`. `provider_router.generate_export` creates the row and stops;
  it stays `"processing"` forever unless an ADMIN separately calls
  `enterprise_service.process_request` for the underlying request — which
  creates a SECOND, independent `ComplianceExport` row rather than
  advancing the tenant's own row. `app/jobs/compliance_sla.py`'s
  `run_expire_exports` only EXPIRES already-`"ready"` exports; it never
  generates one. Reported as `EXPORT_WORKER_NOT_IMPLEMENTED` per the
  mission's own explicit instruction not to fabricate one — see
  `compliance-export-worker-discovery.md`.
- **Duplicate audit-log bug in `download_export`**: calls `_audit(...)`
  twice with the identical action string — a correctness bug, not a
  security gap; documented, not fixed (out of this slice's authorization
  focus).
- **Three independently-maintained, near-duplicate constant sets**
  (`provider_router.TENANT_ALLOWED_REQUEST_TYPES`/`TENANT_WITHDRAWABLE_CONSENT_TYPES`
  vs. `customer_router`'s own sets vs. `enterprise_service.VALID_REQUEST_TYPES`)
  — the minimal fix in #4 above corrects the SPECIFIC values needed for
  the 6 selected routes to function; consolidating all three into one
  shared source of truth is a larger refactor flagged as a product
  decision, not performed this slice.

## Coverage
**200/226 → 206/226** — all 6 selected routes individually reconciled and
confirmed `FULLY_PROTECTED`. See `canonical-coverage-update.md`.

## Tests
27 new tests (`tests/test_phase2f20_compliance_provider_authorization.py`),
all passing. Full compliance regression (573 tests across every existing
compliance/privacy test file) passes unmodified — zero pre-existing test
required any change, confirming the fixes are additive, not
behavior-breaking, for every previously-passing path.

## Final status
**SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED** — see `approval-gate.md`.
