import { OperationDefinition, OperationType } from "./types";

/**
 * Typed operation registry (Phase Z spec section 3). Backend/mobile code
 * classifies an operation by looking up its OperationType here -- never by
 * inspecting the request URL or method. Every operation is one of the four
 * explicit classes; ONLINE_ONLY_MUTATION operations are listed for
 * completeness/documentation but are never constructed as queue items
 * (their screens call the real API directly, no offline path exists for
 * them by design).
 */
export const OPERATION_REGISTRY: Record<OperationType, OperationDefinition> = {
  JOB_ON_THE_WAY: { operation_class: "IDEMPOTENT_MUTATION", label: "On the way", transientRetryable: true },
  JOB_REACHED_SITE: { operation_class: "IDEMPOTENT_MUTATION", label: "Arrived", transientRetryable: true },
  INSPECTION_CHECKLIST_ITEM: { operation_class: "IDEMPOTENT_MUTATION", label: "Inspection checklist item", transientRetryable: true },
  INSPECTION_SUBMIT: { operation_class: "IDEMPOTENT_MUTATION", label: "Inspection completed", transientRetryable: true },
  INSPECTION_PHOTO_UPLOAD: { operation_class: "MEDIA_UPLOAD", label: "Inspection photos", transientRetryable: true },
  ESTIMATE_CREATE: { operation_class: "IDEMPOTENT_MUTATION", label: "Estimate draft", transientRetryable: true },
  ESTIMATE_REVISE: { operation_class: "IDEMPOTENT_MUTATION", label: "Estimate revision", transientRetryable: true },
  PART_REQUEST_CREATE: { operation_class: "IDEMPOTENT_MUTATION", label: "Part request", transientRetryable: true },
  WORK_CHECKLIST_RESPONSE: { operation_class: "IDEMPOTENT_MUTATION", label: "Part installed", transientRetryable: true },
  WORK_START: { operation_class: "IDEMPOTENT_MUTATION", label: "Work started", transientRetryable: true },
  WORK_PAUSE: { operation_class: "IDEMPOTENT_MUTATION", label: "Work paused", transientRetryable: true },
  WORK_RESUME: { operation_class: "IDEMPOTENT_MUTATION", label: "Work resumed", transientRetryable: true },
  WORK_FINISH: { operation_class: "IDEMPOTENT_MUTATION", label: "Work completed", transientRetryable: true },
  COMPLETION_EVIDENCE_UPLOAD: { operation_class: "MEDIA_UPLOAD", label: "Completion photos", transientRetryable: true },
  COMPLETION_PROOF_SUBMIT: { operation_class: "IDEMPOTENT_MUTATION", label: "Completion report", transientRetryable: true },
  SCHEDULE_BLOCKED_TIME_CREATE: { operation_class: "IDEMPOTENT_MUTATION", label: "Schedule exception", transientRetryable: true },
  SCHEDULE_TIME_OFF_CREATE: { operation_class: "IDEMPOTENT_MUTATION", label: "Time off request", transientRetryable: true },
  DOCUMENT_UPLOAD: { operation_class: "MEDIA_UPLOAD", label: "Document upload", transientRetryable: true },
  NOTIFICATION_MARK_READ: { operation_class: "IDEMPOTENT_MUTATION", label: "Notification read", transientRetryable: true },
  NOTIFICATION_MARK_ALL_READ: { operation_class: "IDEMPOTENT_MUTATION", label: "Notifications read", transientRetryable: true },
  SUPPORT_REQUEST_CREATE: { operation_class: "LOCAL_DRAFT", label: "Support request draft", transientRetryable: true },
};

export function classify(operationType: OperationType): OperationDefinition {
  return OPERATION_REGISTRY[operationType];
}

/** Non-retryable backend error codes (spec section 13) -- validation,
 * auth, permission, missing/expired entity, conflict, and business/
 * workflow rejections must never be automatically retried. */
const PERMANENT_ERROR_CODES = new Set([
  "VALIDATION_ERROR", "AUTH_REQUIRED", "ACCESS_TOKEN_EXPIRED", "REFRESH_TOKEN_EXPIRED",
  "CAPABILITY_REQUIRED", "ACTION_NOT_ALLOWED", "ENTITY_NOT_ASSIGNED", "SESSION_NOT_FOUND",
  "CONFLICT", "STALE_ENTITY_VERSION", "STALE_WORKFLOW_VERSION", "QUOTE_NOT_CURRENT",
]);

const TRANSIENT_ERROR_CODES = new Set(["NETWORK_TIMEOUT", "SERVER_UNAVAILABLE", "RATE_LIMITED"]);

export function isTransientFailure(errorCode: string | undefined | null): boolean {
  if (!errorCode) return false;
  return TRANSIENT_ERROR_CODES.has(errorCode);
}

export function isPermanentFailure(errorCode: string | undefined | null): boolean {
  if (!errorCode) return false;
  return PERMANENT_ERROR_CODES.has(errorCode);
}
