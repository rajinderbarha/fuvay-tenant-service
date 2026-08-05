/**
 * `GET /v1/customer/notifications`, `GET .../unread-count`,
 * `POST .../{id}/read`, `POST .../mark-all-read` -- confirmed real in
 * `app/engines/platform_notifications/customer_router.py`, backed by the
 * shared `InAppNotification` model (`app/engines/platform_notifications/
 * models.py`). `to_dict()` on that model is already customer-safe -- no
 * `user_id`/`tenant_id`/`outbox_id` ever appear in the payload.
 *
 * Replaces an earlier, unwired stub that guessed field names (`is_read`,
 * `deep_link`) without tracing the router -- the real fields are
 * `read_status` and `action_url`/`source_record_type`/`source_record_id`
 * (In-App Notification Center audit).
 */
import { z } from "zod";

export const notificationDtoSchema = z.object({
  id: z.string(),
  notification_type: z.string(),
  title: z.string(),
  body: z.string(),
  action_url: z.string().nullable(),
  action_label: z.string().nullable(),
  source_record_type: z.string().nullable(),
  source_record_id: z.string().nullable(),
  severity: z.string(),
  read_status: z.string(),
  read_at: z.string().nullable(),
  created_at: z.string(),
}).passthrough();
export type NotificationDto = z.infer<typeof notificationDtoSchema>;

export const notificationListResponseSchema = z.object({
  items: z.array(notificationDtoSchema),
  total: z.number(),
});
export type NotificationListResponse = z.infer<typeof notificationListResponseSchema>;

export const unreadCountResponseSchema = z.object({
  unread_count: z.number(),
});

export const markAllReadResponseSchema = z.object({
  marked_read: z.number(),
});
