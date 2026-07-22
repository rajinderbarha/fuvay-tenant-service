# Reference Workflow 3 — Booking Exception Resolution

## Scope
Unified operations workspace covering: provider not assigned, provider rejected, technician unavailable, SLA risk/breach, quote delayed, customer unavailable, cancellation, reschedule, rework, complaint. **Precondition:** this workspace should be built against `ServiceJob` (canonical), not `Booking` (legacy) or field_ops `Job` — see `canonical-pipeline-report.md` #1. Building it against the wrong record risks reproducing the exact fragmentation this whole initiative is meant to fix.

## Workspace contents (Standard Pattern 7), mapped to existing data
- Booking/job summary — `ServiceJob` + `ServiceBooking`
- Customer / Provider / Technician — joined from `User`/`Tenant` via `assigned_staff_id`, `customer_id`
- Current lifecycle status — `ServiceJob.status` (draft/matched/assigned/on_the_way/arrived/inspection/quote_required/in_progress/completed, RUNTIME_VERIFIED)
- Problem explanation — derived (e.g., no match found, provider rejected, SLA countdown breached)
- Matching attempts — `matching_engine` history (RUNTIME_VERIFIED matching logic exists; attempt-history logging specifically UNVERIFIED in this pass)
- Status timeline — status_history table (Level 2/3 tab)
- Communication history — chat thread (pending chat-engine consolidation decision, canonical-pipeline-report.md #11)
- Quote — `quote_checklist` record if present
- Parts — NOT AVAILABLE, no structured parts entity exists (BLOCKED_BY_BACKEND_GAP, see canonical-pipeline-report.md #3) — workspace should show "quote_required" status only, not a fabricated parts sub-panel
- Financial impact — usage credit ledger entries, commission deduction status
- Recommended action — new derived field (see `status-next-action-registry.csv`)
- Allowed resolution actions — permission-gated subset of the list below
- Confirmation — standard confirm-dialog pattern already used elsewhere
- Audit trail — `TenantAuditLog`/status_history

## Actions and their real backend support

| Action | Backend support | Verification |
|---|---|---|
| Retry matching | `matching_engine` re-run | RUNTIME_VERIFIED (matching engine itself works; retry-trigger endpoint not independently confirmed) |
| Expand service area | `TenantServiceArea` edit | SOURCE_VERIFIED |
| Reassign provider/technician | `home_service_assignment` admin/staff routers | SOURCE_VERIFIED |
| Contact customer | Chat (pending canonical-engine decision) | SOURCE_VERIFIED (multiple engines could serve this) |
| Reschedule | `final_records`/execution — delivered L5-29 | RUNTIME_VERIFIED |
| Cancel | Delivered L5-29 (closed CRITICAL gap L5-00-005) | RUNTIME_VERIFIED |
| Request information | Notification send | SOURCE_INFERRED |
| Issue service credit | `customer_credits` — delivered L5-28 | RUNTIME_VERIFIED |
| Deduct provider credit | `invoice_payment` provider wallet | SOURCE_VERIFIED |
| Schedule rework | `complaints.ReworkRequest` | SOURCE_VERIFIED |
| Escalate | `complaints` engine, SLA loop already wired (L5-02) | RUNTIME_VERIFIED |
| Close case | `complaints` resolve/reject, notify wired L5-24 | RUNTIME_VERIFIED |

## Recommendation
Do not implement this workspace until the Phase 14 decision on the booking/job model (Booking vs field_ops Job vs ServiceJob) is finalized — see `workflow-gaps-and-blockers.md`. Building it now against ServiceJob is safe (that's confirmed canonical) but the workspace must not attempt to also surface legacy Booking or field_ops Job records as if they were the same entity.
