import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { NotificationPreferencesDetailDTO } from "./preferencesTypes";

export function getNotificationPreferences(signal?: AbortSignal): Promise<ApiResult<NotificationPreferencesDetailDTO>> {
  return authenticatedRequest<NotificationPreferencesDetailDTO>(`/v1/staff/notification-preferences`, { method: "GET", signal });
}

export function updateEventPreference(code: string, enabled: boolean, version: number): Promise<ApiResult<NotificationPreferencesDetailDTO>> {
  return authenticatedRequest<NotificationPreferencesDetailDTO>(`/v1/staff/notification-preferences`, {
    method: "PATCH", body: { code, enabled, version },
  });
}

export function updateQuietHours(input: {
  enabled: boolean; startLocalTime: string | null; endLocalTime: string | null; version: number;
}): Promise<ApiResult<NotificationPreferencesDetailDTO>> {
  return authenticatedRequest<NotificationPreferencesDetailDTO>(`/v1/staff/notification-preferences`, {
    method: "PATCH",
    body: {
      version: input.version,
      quiet_hours: { enabled: input.enabled, start_local_time: input.startLocalTime, end_local_time: input.endLocalTime },
    },
  });
}
