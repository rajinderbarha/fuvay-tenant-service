/**
 * Phase Z — typed operation registry + persisted queue item model.
 * Classification is a property looked up by OperationType, never derived
 * from a URL string (spec section 3's explicit requirement).
 */

export type OperationClass = "LOCAL_DRAFT" | "MEDIA_UPLOAD" | "IDEMPOTENT_MUTATION" | "ONLINE_ONLY_MUTATION";

/**
 * Every technician mutation traced by the Phase Z audit (see completion
 * report for the full per-operation audit table). Job accept, estimate
 * send, customer handover, and direct-payment finalize are intentionally
 * ONLINE_ONLY_MUTATION and are never constructed as queue items -- their
 * screens call the real API directly and are not part of this registry's
 * queueable set.
 */
export type OperationType =
  | "JOB_ON_THE_WAY"
  | "JOB_REACHED_SITE"
  | "INSPECTION_CHECKLIST_ITEM"
  | "INSPECTION_SUBMIT"
  | "INSPECTION_PHOTO_UPLOAD"
  | "ESTIMATE_CREATE"
  | "ESTIMATE_REVISE"
  | "PART_REQUEST_CREATE"
  | "WORK_CHECKLIST_RESPONSE"
  | "WORK_START"
  | "WORK_PAUSE"
  | "WORK_RESUME"
  | "WORK_FINISH"
  | "COMPLETION_EVIDENCE_UPLOAD"
  | "COMPLETION_PROOF_SUBMIT"
  | "SCHEDULE_BLOCKED_TIME_CREATE"
  | "SCHEDULE_TIME_OFF_CREATE"
  | "DOCUMENT_UPLOAD"
  | "NOTIFICATION_MARK_READ"
  | "NOTIFICATION_MARK_ALL_READ"
  | "SUPPORT_REQUEST_CREATE";

export type QueueItemState =
  | "draft"
  | "waiting"
  | "uploading"
  | "submitted"
  | "server_confirmed"
  | "failed"
  | "conflict"
  | "blocked"
  | "cancelled"
  | "authentication_required";

/** Never persist tokens, customer contact/address, passwords, OTP/MFA
 * secrets, raw auth headers, or permanent signed URLs (spec section 5). */
export interface QueueItem {
  local_id: string;
  operation_type: OperationType;
  operation_class: OperationClass;
  /** Bound at enqueue time to `getSessionGeneration()` -- an item enqueued
   * under a previous technician's session is never retried under the next
   * one (spec section 17/18 isolation). */
  session_generation: number;
  tenant_id: string;
  vertical_code: string;
  job_id?: string;
  entity_id?: string;
  local_entity_version?: number;
  server_entity_version?: number;
  idempotency_key: string;
  /** local_ids of items that must reach server_confirmed before this item
   * may execute (spec section 6). */
  dependencies: string[];
  state: QueueItemState;
  attempt_count: number;
  next_attempt_at: string | null;
  created_at: string;
  updated_at: string;
  last_error_code?: string | null;
  /** Safe, human-readable label + job reference only -- never full payload
   * (spec section 4's row requirements + section 21 telemetry redaction). */
  title: string;
  job_reference?: string;
  /** The actual request payload needed to execute this item. Kept
   * separate from the safe display fields above; still local-only (never
   * sent to telemetry), but does contain the real mutation body. */
  payload: Record<string, unknown>;
}

export interface OperationDefinition {
  operation_class: OperationClass;
  label: string;
  /** True only for the narrow set of transient failure codes this
   * operation's automatic retry may act on (spec section 13) -- permanent
   * failures (validation/permission/conflict/etc.) are never retried. */
  transientRetryable: boolean;
}
