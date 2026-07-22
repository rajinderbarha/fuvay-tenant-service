# Compliance Export Worker Discovery

## Finding: EXPORT_WORKER_NOT_IMPLEMENTED

Searched exhaustively for: `ComplianceExport` status-update writers,
`BackgroundTasks` usage, Celery/RQ/Arq/Dramatiq task definitions, event-bus
consumers, cron/scheduled jobs, queue names, storage writes, file
generation (ZIP/CSV/JSON/PDF), signed-URL creation, and export-completion
callbacks — across `app/engines/compliance/` and the repository's
worker/job directories.

## What exists
- `app/jobs/compliance_sla.py` — the ONLY background automation touching
  this module. Runs every 15 minutes via `asyncio.create_task` in the app
  lifespan. Does exactly two things:
  1. `run_sla_check()` — flips `sla_status`/`status` on OPEN
     `ComplianceRequest` rows based on `due_at`, notifies `super_admin`
     users.
  2. `run_expire_exports()` — sets `ComplianceExport.status="expired"`
     and clears `download_url` for rows where `expires_at < now()` AND
     `status in ("ready", "downloaded")`.
  **Neither function ever transitions an export INTO `"ready"` state.**
- `ComplianceEnterpriseService.process_request` (an ADMIN-only code path,
  reached only from `admin_router.py`, `require_super_admin`) — for
  `data_export`-type requests, immediately and SYNCHRONOUSLY sets a
  (different, admin-created) `ComplianceExport.status="ready"` with a
  placeholder `download_url = f"/v1/admin/compliance/exports/{export.id}/download"`,
  under a comment `# Mark as ready (actual file generation deferred to
  background task)` — **no such background task exists anywhere in this
  codebase.** No PII is actually aggregated, no file is written, no
  storage call is made.

## What does NOT exist
- No Celery, RQ, Arq, or Dramatiq task of any kind.
- No FastAPI `BackgroundTasks` usage anywhere in `app/engines/compliance/`.
- No file-generation code (no ZIP/CSV/JSON/PDF writer) reachable from
  either the tenant or admin export paths.
- No storage client call (no S3/local-disk write) for compliance exports.
- No signed-URL generation mechanism — `download_url` values observed in
  code are either `None` (tenant-created, `generate_export`) or a
  hardcoded internal API path string (admin-created, `process_request`),
  never an actual generated/signed storage URL.

## Consequence for `generate_export` (the selected route)
`provider_router.generate_export` creates a `ComplianceExport` row with
`status="processing"` and stops. **This row is permanently stuck** —
nothing in the entire codebase will ever advance it to `"ready"`. A
tenant who calls this route receives a success response implying their
export is being processed, but no export will ever actually become
downloadable through the SAME row `generate_export` created. This is
reported honestly, per the mission's explicit instruction, as
`EXPORT_WORKER_NOT_IMPLEMENTED` — not fabricated, not silently ignored.

## Scope discipline
Per this slice's OUT OF SCOPE constraint ("Do not build new object-storage
infrastructure... Do not build a new consent platform... Do not build new
export infrastructure" is implied by the broader "add a new compliance
engine" prohibition), NO worker was built this slice. This finding
directly justifies this slice's final status being
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` rather than a fully closed
status — see `approval-gate.md`.
