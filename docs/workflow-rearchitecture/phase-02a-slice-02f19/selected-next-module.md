# Selected Next Module — Slice 2F-20

## Module
`app.engines.compliance.provider_router`

## Mounted prefix
`/v1/provider/compliance` (mutation routes) — related reads also under the
same prefix, plus `/v1/provider/compliance/exports/{export_id}/download`
(a state-mutating GET, flagged separately — see below).

## Exact mutation count
**6** — all confirmed mounted, all currently `require_tenant_owner` +
`get_current_user` only (`PERMISSION_ONLY_NOT_SCOPE_AWARE`).

## Exact route list
1. `POST /v1/provider/compliance/consents/{consent_type}/withdraw` (`withdraw_consent`)
2. `POST /v1/provider/compliance/customer-requests/{request_id}/tenant-response` (`customer_tenant_response`)
3. `POST /v1/provider/compliance/requests` (`create_my_request`)
4. `POST /v1/provider/compliance/requests/{request_id}/cancel` (`cancel_my_request`)
5. `POST /v1/provider/compliance/requests/{request_id}/generate-export` (`generate_export`)
6. `POST /v1/provider/compliance/staff-requests/{request_id}/tenant-response` (`staff_tenant_response`)

## Related read routes (not selected-mutation routes, but in-scope for a future implementation slice's audit)
`GET /summary`, `GET /requests`, `GET /requests/{request_id}`,
`GET /exports`, `GET /exports/{export_id}`, `GET /consents`,
`GET /staff-requests`, `GET /staff-requests/{request_id}`,
`GET /customer-requests`, `GET /customer-requests/{request_id}` — most use
`require_technician` (looser than the mutation routes' `require_tenant_owner`);
`GET /exports/{export_id}/download` is a state-mutating GET (flips
`ComplianceExport.status` to `"downloaded"`) using `require_tenant_owner` —
flagged as an "alternate-shape mutation" a future slice must treat as a
seventh mutation-equivalent route, not a pure read.

## Models and tables
`ComplianceRequest` (no real `tenant_id` column — scoped only via
`metadata_json["tenant_id"]`/`["related_tenant_id"]` JSONB keys),
`ComplianceExport` (no `tenant_id`, scoped transitively via `request_id`
FK to `ComplianceRequest`), `ComplianceRequestItem`, `ConsentRecord` (has a
real `tenant_id` column, but `withdraw_consent` never populates it),
`DataDeletionRequest`, `DataPortabilityRequest`, `DataRetentionPolicy`,
`ComplianceAuditLog` (append-only).

## Parent workflow
DPDP Act 2023 data-subject-request lifecycle: tenant's own requests
(`tenant_business`/`tenant_owner` subject_type), tenant staff's requests
(`TENANT_STAFF_SUBJECT_TYPES`), and limited tenant visibility into
customer-initiated requests linked to that tenant's bookings/jobs
(`subject_type == "customer"`).

## Canonical personas
`tenant_owner`, `super_admin` (current); customer-facing mirror
(`customer_router.py`) already correctly uses `require_customer` alone —
confirmed as the model for how a single, correctly-scoped dependency
should look.

## Existing permissions
None of the granular `P`-class permission strings apply here (confirmed
absent in this module) — role-based dependencies are the established
pattern, consistent with every module closed in this initiative so far.

## Existing dependencies available for reuse (no new dependency needed)
`require_tenant_owner_mutation` (`app/core/permissions.py`) — SAME role
set as the currently-used `require_tenant_owner` (`tenant_owner`,
`super_admin`) PLUS the missing read-only-`access_scope` denial. Its own
docstring explicitly recommends it "in place of `require_tenant_owner` on
any provider_portal-style mutation endpoint" — a direct, narrow,
zero-role-set-change upgrade path requiring no product decision about
whether to admit `staff`.

## Tenant and object ownership — the module's core gap
`ComplianceRequest`/`ComplianceExport` have **no real, schema-level
`tenant_id` column** — every existing scope check in this router is an
ad hoc `metadata_json["tenant_id"].astext == tenant_id_str` string
comparison, present on 4 of the 6 routes but ABSENT on `withdraw_consent`
(which hardcodes `tenant_id=None` in the underlying service call,
discarding the caller's actual tenant identity on a written
`ConsentRecord`). This is a genuinely different, deeper class of gap than
every other remaining module (which are all "self-owned by construction"
or simple parent-FK cases).

## State-machine concerns
`ComplianceRequest.status` (submitted → identity_verification_pending →
approved → completed/cancelled, with SLA deadlines);
`ComplianceExport.status` (pending → processing → ready → downloaded).
`cancel_my_request` already validates legal source states
(`status in ("submitted", "identity_verification_pending")`) — this
existing validation must be preserved, not weakened, by any future fix.

## Client-controlled identifiers
`request_id`/`consent_type`/`export_id` path params — already
individually validated against tenant-scoped WHERE clauses on 4 of 6
routes (must be added to the 2 that lack it: `withdraw_consent`, which has
no request_id to scope at all — its fix is about the service-layer
`tenant_id=None` hardcoding, not a missing WHERE clause).

## Financial or delivery side effects
`generate_export` queues a `ComplianceExport` row (`status="processing"`)
— no PII is read or file generated within this router itself; the actual
export-content generation happens in an out-of-router worker/process not
located in this investigation (flagged for the implementation slice to
locate before closing this route fully).

## Alternate routes
None found — `customer_router.py`'s DPDP self-service surface reaches
DISTINCT records (`subject_id == caller`, not tenant-scoped) via a
correctly-scoped `require_customer` dependency; no same-record bypass
exists.

## Frontend/mobile callers
Not investigated this slice (discovery/selection only) — deferred to the
implementation slice per this mission's own scope boundary.

## Product decisions flagged (not resolved this slice)
- Whether `staff` role should be admitted alongside `tenant_owner` for any
  of these 6 capabilities (current `require_tenant_owner` excludes staff;
  `require_tenant_owner_mutation` preserves that exclusion by design —
  broadening to `require_owner_or_office_staff_mutation` would be a
  policy change, not a drop-in fix).
- Export generation rate-limiting/throttling policy.

## Explicit boundaries for the implementation slice
- Do NOT modify `customer_router.py` (correctly scoped already, not part
  of the object-ownership gap).
- Do NOT modify `ConsentRecord`'s or `ComplianceRequest`'s schema (no
  migration permitted per this initiative's standing constraint) — the
  `tenant_id`-column gap must be closed via metadata_json enforcement
  (consistent with the JSONB-key pattern already used by 4 of the 6
  routes), not a schema change, UNLESS a future migration-permitted slice
  is explicitly authorized.
- Do NOT change DPDP SLA deadlines, request-type allowlists, or the
  status state machine's legal transitions — only authorization/ownership.
- Do NOT touch `download_export`'s file-serving mechanism beyond its
  dependency (out of scope unless proven directly connected).

## Why it outranks every other remaining module
Per `remaining-module-risk-scoring.csv`: `compliance` is the sole
`CRITICAL`-severity module — the only one combining regulatory (DPDP)
data sensitivity with a genuine, structural object-ownership gap (missing
schema-level `tenant_id`) AND a confirmed live authorization defect
(`withdraw_consent`'s hardcoded `tenant_id=None`). Every other remaining
module's gap is either a simple role-gate upgrade (self-owned-by-construction
resources) or a financial-but-single-route case (`package_commerce`) with
no comparable structural depth.
