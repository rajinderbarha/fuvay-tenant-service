# Quote → Job Lifecycle Effect

## Confirmed effects (via `_sync_job_status`, `update(ServiceJob).where(ServiceJob.id == job_id).values(status=...)`)
| Quote event | ServiceJob.status set to |
|---|---|
| `send_to_customer` | `awaiting_customer_quote_approval` |
| `customer_approve` | `quote_approved` |
| `customer_reject` | `quote_rejected` |
| `customer_request_revision` | `quote_revision_requested` |

## Scope correctness
Every `_sync_job_status` call targets `ServiceJob` exclusively (`from app.engines.final_records.models import ServiceJob`) — it never touches `field_ops.Job` or `Booking`. Since quote_checklist's `job_id` is always a `ServiceJob.id` (validated at quote-creation time via `create_quote`'s job lookup), there is no code path where this update could target the wrong pipeline's row (a `field_ops.Job.id` would simply not match any `ServiceJob` row, and the `UPDATE ... WHERE id = job_id` would silently affect zero rows rather than corrupt an unrelated table — SQLAlchemy's `update()` with a `WHERE` clause on a specific model's table cannot cross into a different table).

## Approval cannot skip required Job states
Job-status transitions here are simple field writes (`status=new_status`), not validated against a separate ServiceJob-level state machine within this slice's scope — `final_records`'s own state validation (if any) is out of scope for this slice to audit (it is a different engine). This slice confirms only that quote_checklist's OWN writes are scoped correctly and occur in the correct order relative to quote-level validation.

## Rejection does not complete work; expiry does not fabricate cancellation
`customer_reject` sets `job_status = quote_rejected`, never any "completed" status. No writer ever reaches `QS_EXPIRED` (see `known-limitations.md`), so there is no expiry-triggered Job effect to verify — this is a designed-but-unimplemented capability, not a live path.

## Invalid decisions produce no Job-status change
Every `_sync_job_status` call happens strictly after `_assert_transition` succeeds — an invalid transition raises before this line is ever reached (source-position, unchanged by this slice).

## Repeated decisions do not duplicate status history
`ServiceJobQuoteEvent` rows are only ever written inside the same method body that also performs the one-time status transition (guarded by `_assert_transition`, which raises on a repeat) — a repeated decision never reaches `_log_event` a second time for the same transition (except the intentionally idempotent same-key `customer_approve` short-circuit, which returns early WITHOUT writing a second event or re-syncing Job status).

## No cross-pipeline adapters created
This slice added no code bridging `ServiceJob` status to `field_ops.Job` or `Booking` status — none existed before, none was requested, none was built.
