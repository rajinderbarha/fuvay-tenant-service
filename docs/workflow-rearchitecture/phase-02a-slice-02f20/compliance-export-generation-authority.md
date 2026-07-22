# Compliance Export Generation Authority

## Verified for `generate_export` (the queueing step — the only step that exists)
- **ComplianceRequest belongs to the principal tenant** — TRUE, unchanged
  `metadata_json["tenant_id"]` check, re-verified.
- **Request belongs to the exact data subject** — TRUE, subject fields
  copied from the verified parent request.
- **Request type permits export** — TRUE, unchanged (`"export" in
  req.request_type`).
- **Request is in the legal source state** — TRUE, unchanged (`status in
  ("approved", "completed")`).
- **Export has not already been successfully generated where uniqueness
  is expected** — **NOT ENFORCED**: `generate_export` does not check for
  an existing `ComplianceExport` row for the same `request_id` before
  creating a new one — repeated calls create MULTIPLE `ComplianceExport`
  rows for the same request, all stuck at `"processing"`. See
  `compliance-export-retry-concurrency.md`.
- **Tenant and subject are server derived** — TRUE.
- **Worker receives authoritative identifiers / worker revalidates tenant
  and subject / worker does not trust arbitrary queue payload tenant
  fields** — **N/A**: no worker exists to receive anything (see
  `compliance-export-worker-discovery.md`) — there is no queue payload,
  no worker-side trust boundary to audit, because there is no worker.
- **Export query filters every included dataset by the exact subject and
  tenant / another tenant's or customer's records cannot be included** —
  **N/A / cannot be verified**: since no export-content-generation code
  exists anywhere, there is no dataset query to audit. This requirement
  is UNSATISFIABLE until a worker is built — flagged as
  `PRODUCT_DECISION_REQUIRED` (whether/how to build it) rather than
  claimed closed.

## Provider authorization at the route does not replace worker-side scoping
Confirmed — but since no worker-side scoping exists AT ALL (no worker
exists), this requirement cannot be satisfied by this slice regardless of
how well the route itself is secured. The route-level fix (this slice)
closes the AUTHORIZATION-TO-QUEUE question; it does not and cannot close
the AUTHORIZATION-TO-GENERATE question, because generation does not
happen anywhere in this codebase.
