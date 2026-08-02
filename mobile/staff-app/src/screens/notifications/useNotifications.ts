import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/notifications/notificationsApi";
import { NotificationFilter, NotificationCategory } from "../../services/notifications/types";
import { AppError } from "../../services/api/types";
import { isOffline } from "../../services/api/networkState";
import { useSession } from "../../navigation/session/SessionProvider";
import { loadQueue, saveQueue } from "../../services/sync/queueStorage";
import { buildQueueItem } from "../../services/sync/syncEngine";

function queryKey(filter: NotificationFilter, category: NotificationCategory | null) {
  return ["notifications", filter, category] as const;
}

/** Notifications inbox + guarded mutations (Phase Q). Reuses the existing
 * canonical staff notification endpoints for read-state mutations; opening
 * the tab never auto-marks anything read (spec section 2). */
export function useNotifications(filter: NotificationFilter, category: NotificationCategory | null) {
  const queryClient = useQueryClient();
  const { accessContext } = useSession();
  const key = queryKey(filter, category);

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await api.getNotifications(filter, category, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const refresh = useCallback(() => queryClient.invalidateQueries({ queryKey: ["notifications"] }), [queryClient]);

  const markRead = useCallback(async (id: string) => {
    // Genuinely offline: queue it (IDEMPOTENT_MUTATION, spec section 3) --
    // the Offline & Sync Center's "Sync all now" replays it with a stable
    // idempotency key once connectivity returns. Never queued while
    // online, since the direct call already succeeds/fails immediately.
    if (isOffline() && accessContext.userId && accessContext.tenantId) {
      const existing = await loadQueue(accessContext.userId, accessContext.tenantId);
      const queued = buildQueueItem({
        operation_type: "NOTIFICATION_MARK_READ", tenant_id: accessContext.tenantId,
        vertical_code: (accessContext.enabledVerticals ?? [])[0] ?? "home_services",
        entity_id: id, title: "Notification read", payload: { id },
      });
      await saveQueue(accessContext.userId, accessContext.tenantId, [...existing, queued]);
      return { ok: true as const };
    }
    const result = await api.markNotificationRead(id);
    if (!result.ok) {
      setMutationError(result.error);
      return { ok: false as const };
    }
    await refresh();
    return { ok: true as const };
  }, [refresh, accessContext.userId, accessContext.tenantId, accessContext.enabledVerticals]);

  const markAllRead = useCallback(async () => {
    if (mutating) return { ok: false as const };
    setMutating(true);
    setMutationError(null);
    try {
      const result = await api.markAllNotificationsRead();
      if (!result.ok) {
        setMutationError(result.error);
        return { ok: false as const };
      }
      await refresh();
      return { ok: true as const };
    } finally {
      setMutating(false);
    }
  }, [mutating, refresh]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating, mutationError,
    markRead, markAllRead,
  };
}
