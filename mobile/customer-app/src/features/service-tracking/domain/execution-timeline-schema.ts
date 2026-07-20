import { z } from "zod";

/**
 * Mirrors the real, customer-facing response of
 * `GET /v1/customer/service-jobs/{jobId}/tracking`
 * (`app/engines/execution/home_service_router.py`) — see
 * CUSTOMER-L5-13-contract-matrix.md. Deliberately parses only `job.status`
 * and each timeline event's `event_type`/`created_at` — `notes`/
 * `actor_role`/`id`/`job_id` are excluded structurally (via `z.object()`'s
 * default unknown-key-stripping, the same pattern used since
 * CUSTOMER-L5-08 to exclude internal-only fields) because this specific
 * endpoint's own `notes` field (both at the top level and per-event) is
 * confirmed NOT filtered by any `is_customer_visible` flag server-side,
 * unlike `ServiceJobExecutionNote`/`ServiceJobMediaUpload`. This sprint
 * does not render `notes`/`media` at all as a result — see
 * CUSTOMER-L5-13-privacy-and-security-review.md.
 */
const executionEventSchema = z.object({
  event_type: z.string().min(1),
  created_at: z.string().nullable().optional(),
});
export type ValidatedExecutionEvent = z.infer<typeof executionEventSchema>;

const executionJobSchema = z.object({
  status: z.string().min(1),
});

const executionTrackingResponseSchema = z.object({
  job: executionJobSchema,
  timeline: z.array(z.unknown()),
});

export interface ExecutionTrackingResult {
  status: string;
  timeline: ValidatedExecutionEvent[];
  droppedCount: number;
}

/** Drops individually-invalid timeline rows rather than failing the whole screen — the same resilience pattern used throughout this app. */
export function parseExecutionTracking(payload: unknown): ExecutionTrackingResult | null {
  const envelope = executionTrackingResponseSchema.safeParse(payload);
  if (!envelope.success) return null;

  const timeline: ValidatedExecutionEvent[] = [];
  let droppedCount = 0;
  for (const raw of envelope.data.timeline) {
    const parsed = executionEventSchema.safeParse(raw);
    if (parsed.success) timeline.push(parsed.data);
    else droppedCount += 1;
  }
  return { status: envelope.data.job.status, timeline, droppedCount };
}
