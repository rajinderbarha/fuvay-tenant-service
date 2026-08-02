import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { NotificationInboxDTO, NotificationFilter, NotificationCategory } from "./types";

export function getNotifications(
  filter: NotificationFilter, category: NotificationCategory | null, signal?: AbortSignal,
): Promise<ApiResult<NotificationInboxDTO>> {
  return authenticatedRequest<NotificationInboxDTO>(`/v1/staff/mobile-notifications`, {
    method: "GET", query: { filter, category: category ?? undefined }, signal,
  });
}

/** Reuses the EXISTING canonical staff notification endpoints directly. */
export function markNotificationRead(id: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/notifications/${id}/read`, { method: "POST", unsafeToRetry: true });
}

export function markAllNotificationsRead(): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/staff/notifications/mark-all-read`, { method: "POST", unsafeToRetry: true });
}

export function getUnreadCount(signal?: AbortSignal): Promise<ApiResult<{ unread_count: number }>> {
  return authenticatedRequest<{ unread_count: number }>(`/v1/staff/notifications/unread-count`, { method: "GET", signal });
}
