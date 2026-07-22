# Slice 2F-14 Implementation Summary

> **SUPERSEDED (Slice 2F-14A):** this slice's closure claims (SECURITY_CLOSED, PRIVACY_CLOSED,
> both coverage figures) were not approved. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f14a/documentation-corrections.md` for the
> itemized correction and `docs/workflow-rearchitecture/phase-02a-slice-02f14a/implementation-summary.md`
> for the current status.

## Target

`app.engines.field_ops.staff_router` (`/v1/staff/me/jobs`, 6 routes) and the connected
`FieldOpsService`, plus the directly-connected same-record/same-capability alternates on
`app.engines.field_ops.router` (9 of its 28 routes).

## Pipeline boundary confirmed

`field_ops.Job` is a distinct pipeline from `ServiceJob`/`Booking`/`PartsRequest`/
`quote_checklist` (job-pipeline-boundary.md). No merge, adapter, or cross-pipeline logic was
introduced.

## Defects found and fixed

1. **Tool-visibility gap (not a real vulnerability)**: all 6 `staff_router` routes were already
   protected by a correct pre-existing inline `if u.role not in ("staff","technician")` check,
   invisible to dependency-name-based runtime introspection. Fixed by extracting into a named
   dependency `require_staff_or_technician_only` (`app/dependencies/auth.py`).
2. **Genuine weaker alternate surface**: 7 of `field_ops.router`'s functions
   (`accept_job`, `reject_assignment`, `start_checklist`, `update_checklist_item`,
   `complete_checklist`, `submit_findings`, legacy `update_checklist`) — 5 had zero role check,
   2 had the same tool-invisible inline check. All 7 now use the same named dependency.
3. **Access-scope gap** (Slice-2F13-style): `assign_job`/`update_status` on `field_ops.router`
   were permission-gated but not access-scope-aware. Upgraded to
   `require_tenant_mutation_permission`.
4. **Completion-gate integrity defect**: `update_job_checklist_item` had no status guard,
   allowing mutation of a checklist item after the job's checklist was already finalized. Fixed
   by requiring `job.status == JS.CHECKLIST_STARTED` (required-item-completion-gate.md).

## Not fixed (documented, out of scope)

`JobNote`/`JobMedia` have zero access-control filtering on `field_ops.router`'s notes/media
routes — a real, pre-existing gap, but a distinct capability from this slice's
same-record-same-capability boundary (job-note-privacy.md, evidence-media-boundary.md,
product-decisions-required.md).

## Testing

34 new tests in `tests/test_phase2f14_field_ops_staff_authorization.py`; 2 pre-existing test
files updated for the new gate/dependency; full slice suite 143/143 passing; broad regression
sweep 865+ passing with 3 unrelated live-network-dependent failures.

## Coverage

131→146 protected of 182→210 tenant-facing mutations (headline), 143/213 by direct recount, with
a disclosed pre-existing 3-row discrepancy (global-coverage-update.md).

## Final status

`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` — see approval-gate.md.

Stopped at the Slice 2F-14 approval gate; no second router module begun.
