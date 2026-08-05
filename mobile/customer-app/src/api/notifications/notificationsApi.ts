import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  notificationListResponseSchema, unreadCountResponseSchema, markAllReadResponseSchema,
  notificationDtoSchema,
} from "../contracts/notifications";

const BASE = "/v1/customer/notifications";

export async function listMyNotifications(
  readStatus: "unread" | undefined, limit: number, offset: number,
) {
  const query = new URLSearchParams();
  if (readStatus) query.set("read_status", readStatus);
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}?${query.toString()}` });
  return parseApiSuccess(res.json, notificationListResponseSchema);
}

export async function getMyUnreadNotificationCount() {
  const res = await authenticatedRequest({ method: "GET", path: `${BASE}/unread-count` });
  return parseApiSuccess(res.json, unreadCountResponseSchema);
}

export async function markMyNotificationRead(notificationId: string) {
  const res = await authenticatedRequest({ method: "POST", path: `${BASE}/${notificationId}/read` });
  return parseApiSuccess(res.json, notificationDtoSchema);
}

export async function markAllMyNotificationsRead() {
  const res = await authenticatedRequest({ method: "POST", path: `${BASE}/mark-all-read` });
  return parseApiSuccess(res.json, markAllReadResponseSchema);
}
