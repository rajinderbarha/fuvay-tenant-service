# Compliance Export Storage and Download

## Verified for `download_export` (the one download route reaching `ComplianceExport`)
- **Export record belongs to tenant and subject** — TRUE, unchanged: the
  route joins through `request_id` to the tenant-scoped `ComplianceRequest`
  (`metadata_json["tenant_id"]` check), re-verified.
- **Storage key is server generated / client cannot provide an arbitrary
  storage key or URL** — N/A: `ComplianceExport` has no `storage_key`
  field at all (only `download_url`) — confirmed by model read.
- **File path cannot escape the allowed location** — N/A, same reasoning
  (no file path is ever constructed or served by this route — it returns
  the STORED `download_url` string value as JSON, it does not stream
  file bytes itself).
- **Download requires authorized tenant/provider access** — TRUE, now
  additionally access-scope-aware (`require_tenant_owner_mutation`, this
  slice).
- **Download checks request/export tenant and subject relationships** —
  TRUE, unchanged.
- **Missing and unauthorized exports are externally privacy equivalent**
  — TRUE, same WHERE-clause-based mechanism as request lookups (see
  `compliance-read-privacy.md`).
- **Export status must be ready before download** — TRUE, unchanged
  existing check (`status == "ready"` required, confirmed by code read).
- **Failed/cancelled/expired exports cannot be downloaded** — TRUE for
  `"expired"` (excluded by the `status == "ready"` check); `"failed"`/
  `"cancelled"` statuses are never actually reachable in practice since
  no worker ever sets them (see `compliance-export-worker-discovery.md`)
  — the check itself is correct, just currently only ever sees
  `"processing"` (denied) or the admin-only synthetic `"ready"` (allowed).
- **Private files are not exposed via unrestricted permanent URLs** —
  **CANNOT BE FULLY VERIFIED**: since no real file/storage mechanism
  exists, the `download_url` field observed in practice is either `None`
  (tenant-generated exports, always stuck) or a same-origin internal API
  path string (admin-generated exports) — NEITHER is an actual external
  storage URL, so there is currently no "permanent unrestricted URL" risk
  to close, but this is a consequence of the feature being incomplete,
  not a proven-safe design.
- **Signed URLs, where present, are short-lived and issued only after
  authorization** — N/A, no signed-URL mechanism exists anywhere in this
  codebase for compliance exports.
- **Storage credentials and internal keys are not returned** — TRUE,
  confirmed (no such fields exist on `ComplianceExport` or in the
  response payload).
- **Cross-tenant export IDs are rejected** — TRUE, unchanged.
- **Same-tenant cross-subject export IDs are rejected** — same reasoning
  as `compliance-request-ownership.md`'s finding: tenant-wide oversight is
  the intentional design (a tenant owner sees all exports for requests
  tied to their tenant, not filtered further by which specific customer
  filed the underlying request) — consistent, not a gap.

## Conclusion
Everything THIS SLICE can secure about `download_export` (its
authorization dependency, its tenant/subject scoping) is secured. The
deeper storage/signed-URL/file-privacy questions this workstream asks
about are UNRESOLVABLE because the underlying file-storage mechanism does
not exist — consistent with `compliance-export-worker-discovery.md`'s
finding.
