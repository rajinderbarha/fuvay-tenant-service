/**
 * Customer Notifications API module.
 *
 * MODULE-L5-11: the customer app had NO notification surface at all — 6 backend
 * endpoints (list / unread-count / mark-read / mark-all-read / preferences
 * GET+PUT) and not one page. So booking updates, complaint responses, settlement
 * offers and credit alerts were delivered but the customer had no way to see them
 * in the app, and no way to manage which channels they arrive on.
 *
 * Real router: app/engines/platform_notifications/customer_router.py
 */
import { apiFetch } from "./client";

export interface CustomerNotification {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  action_url: string | null;
  severity: string;
  read_status: string;
  created_at: string;
}

export interface NotificationList {
  items: CustomerNotification[];
  total: number;
  unread_count: number;
}

export interface NotificationPref {
  id: string;
  event_key: string;
  channel: string;
  is_enabled: boolean;
}

export function listNotifications(readStatus?: string, limit = 30): Promise<NotificationList> {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (readStatus) qs.set("read_status", readStatus);
  return apiFetch<NotificationList>(`/v1/customer/notifications?${qs}`);
}

export function getUnreadCount(): Promise<{ unread_count: number }> {
  return apiFetch<{ unread_count: number }>("/v1/customer/notifications/unread-count");
}

export function markRead(id: string): Promise<CustomerNotification> {
  return apiFetch<CustomerNotification>(`/v1/customer/notifications/${id}/read`, { method: "POST" });
}

export function markAllRead(): Promise<{ marked_read: number }> {
  return apiFetch<{ marked_read: number }>("/v1/customer/notifications/mark-all-read", { method: "POST" });
}

export function getPreferences(): Promise<NotificationPref[]> {
  return apiFetch<NotificationPref[]>("/v1/customer/notifications/preferences");
}

export function updatePreference(event_key: string, channel: string, is_enabled: boolean): Promise<NotificationPref> {
  return apiFetch<NotificationPref>("/v1/customer/notifications/preferences", {
    method: "PUT",
    body: JSON.stringify({ event_key, channel, is_enabled }),
  });
}
