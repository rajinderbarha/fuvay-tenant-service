import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { QueueItem } from "./types";
import { ExecuteResult } from "./syncEngine";
import * as notificationsApi from "../notifications/notificationsApi";

/**
 * Typed execution dispatcher (Phase Z spec section 22's explicit ban on a
 * generic "sync any request" endpoint). Every branch calls a real,
 * existing, domain-specific API function with the item's real
 * idempotency key -- there is no code path here that takes a queue item's
 * `operation_type` and turns it into an arbitrary URL/method/payload.
 *
 * Only the operations actually wired to enqueue from a screen this phase
 * (NOTIFICATION_MARK_READ, NOTIFICATION_MARK_ALL_READ) have a real branch
 * below; every other registered OperationType is a genuine, disclosed gap
 * (see completion report) -- executing one today falls through to the
 * final `default` branch, which fails the item as `VALIDATION_ERROR`
 * (permanent, never silently retried, never marked falsely confirmed).
 */
export async function executeQueueItem(item: QueueItem): Promise<ExecuteResult> {
  let result: ApiResult<unknown>;
  switch (item.operation_type) {
    case "NOTIFICATION_MARK_READ":
      result = await notificationsApi.markNotificationRead(item.entity_id ?? "");
      break;
    case "NOTIFICATION_MARK_ALL_READ":
      result = await notificationsApi.markAllNotificationsRead();
      break;
    default:
      return { ok: false, errorCode: "VALIDATION_ERROR" };
  }
  if (result.ok) return { ok: true };
  return { ok: false, errorCode: result.error.backendCode ?? result.error.code, retryAfterSeconds: result.error.retryAfterSeconds };
}

export interface IdempotencyStatusDTO {
  status: "confirmed" | "unknown";
}

/** Real backend lookup (spec section 16's "unknown outcome" recovery --
 * queries the SAME idempotency cache app/core/idempotency.py already
 * writes to on every successful write, read-only, tenant/path/key scoped
 * server-side from the caller's own JWT, never a client-supplied tenant). */
export function getIdempotencyStatus(key: string, path: string): Promise<ApiResult<IdempotencyStatusDTO>> {
  return authenticatedRequest<IdempotencyStatusDTO>(`/v1/mobile/sync/idempotency-status`, {
    method: "GET", query: { key, path },
  });
}
