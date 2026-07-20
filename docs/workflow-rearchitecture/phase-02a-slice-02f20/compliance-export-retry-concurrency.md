# Compliance Export Retry, Duplication and Concurrency

## Classification: **MULTIPLE_EXPORTS_ALLOWED (unintentionally) — CONCURRENCY_DEFECT_CONFIRMED**

## Finding
`generate_export` does NOT check for an existing `ComplianceExport` row
tied to the same `request_id` before creating a new one. Directly traced:
1. Tenant calls `generate_export` for Request X → creates Export A
   (`status="processing"`, stuck forever, see
   `compliance-export-worker-discovery.md`).
2. Tenant calls `generate_export` AGAIN for the same Request X (e.g.
   because Export A never became downloadable, so they retry) → creates
   Export B, a SECOND, independent row for the SAME request, also stuck.
3. If an admin separately processes the SAME underlying request via
   `enterprise_service.process_request` (a completely different,
   admin-only code path), it creates YET ANOTHER, THIRD `ComplianceExport`
   row — synchronously marked `"ready"` with a synthetic `download_url`.

This means a single `ComplianceRequest` can accumulate an unbounded
number of `ComplianceExport` rows, with no relationship or deduplication
between them — the tenant's `generate_export`-created rows and the
admin's `process_request`-created row are entirely independent, and the
tenant's `download_export` route can only ever see rows created via the
tenant path (still tenant-scoped correctly, so no cross-visibility
security issue — this is a DOMAIN-INTEGRITY defect, not a privacy one).

## Directly tested (Workstream 16)
- **Repeated export trigger** — confirmed via code read: no existing-export
  check exists; each call unconditionally constructs and adds a new
  `ComplianceExport` row.
- **Concurrent export trigger** — not independently testable without a
  live database (no locking mechanism is even attempted here, unlike
  `platform_notifications`' `SELECT ... FOR UPDATE` pattern from the prior
  series — this route uses a plain `db.add`, no lock).
- **Retry after failure** — moot, since no export ever reaches a
  `"failed"` state (no worker exists to set it).
- **Trigger after completion** — moot, since no export ever reaches
  `"ready"`/`"completed"` via the tenant path.
- **Cross-subject export substitution** — N/A, `generate_export` always
  copies subject fields from the VERIFIED parent request, never accepts
  them as input.

## Why this is a domain-integrity gap, not a security gap
Every `ComplianceExport` row created via `generate_export`, regardless of
how many accumulate, remains correctly tenant/subject-scoped (this
slice's authorization fixes apply per-CALL, not per-resulting-row-count).
The defect is that the SYSTEM allows an unbounded, un-deduplicated,
permanently-stuck set of export "requests" to accumulate with no
completion path — a data-integrity/UX problem, not a cross-tenant/
cross-subject access problem. This is exactly why this slice's final
status is `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` and not a fully
closed status.

## Not fixed this slice
Per the mission's own instruction ("Do not add a migration unless
separately approved" and the broader OUT OF SCOPE constraints against
building new export/storage infrastructure), no deduplication check, no
locking mechanism, and no worker were added. Adding a simple
"reject if an existing non-terminal export already exists for this
request" check WITHOUT building the worker would not meaningfully close
this gap (it would just prevent duplicate STUCK rows, not fix the
underlying stuck-forever problem) — flagged as `product-decisions-required.md`
item 1 for a future slice that also addresses the worker itself.
