import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import { ProfileDetailDTO, StaffDocumentDTO, NotificationPreferencesDTO } from "./types";

export function getProfile(signal?: AbortSignal): Promise<ApiResult<ProfileDetailDTO>> {
  return authenticatedRequest<ProfileDetailDTO>(`/v1/staff/me/profile`, { method: "GET", signal });
}

export function addDocument(documentType: string, mediaId: string, expiryDate?: string): Promise<ApiResult<StaffDocumentDTO>> {
  return authenticatedRequest<StaffDocumentDTO>(`/v1/staff/me/profile/documents`, {
    method: "POST", body: { document_type: documentType, media_id: mediaId, expiry_date: expiryDate ?? null },
  });
}

export function getNotificationPreferences(signal?: AbortSignal): Promise<ApiResult<NotificationPreferencesDTO>> {
  return authenticatedRequest<NotificationPreferencesDTO>(`/v1/staff/me/notification-preferences`, { method: "GET", signal });
}

export function updateNotificationPreference(category: string, enabled: boolean): Promise<ApiResult<NotificationPreferencesDTO>> {
  return authenticatedRequest<NotificationPreferencesDTO>(`/v1/staff/me/notification-preferences`, { method: "PUT", body: { category, enabled } });
}
