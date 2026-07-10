# ADMIN-TENANT-E2E-06C: Notification Feed API Report

## Status: WIRED — Real API In Use

## API Functions Used by Notification Center

Located in `lib/api.ts` via `sprint27AdminApi`:

| Function | Description |
|---|---|
| `sprint27AdminApi.listNotifications({ read_status, limit })` | Paginated notification feed |
| `sprint27AdminApi.getUnreadCount()` | Returns `{ unread_count: number }` |
| `sprint27AdminApi.markRead(id)` | Mark single notification as read |
| `sprint27AdminApi.markAllRead()` | Returns `{ marked_read: number }` |

## Response Fields Used

From `InAppNotification` type:
- `notification_type`
- `title`
- `body`
- `severity` — `critical | high | medium | low | info`
- `read_status` — `read | unread`
- `created_at`

## Compliance

| Rule | Status |
|---|---|
| Uses central API client (`apiFetch`) | ✅ Yes — via `sprint27AdminApi` |
| Auth token included | ✅ Yes — handled by `apiFetch` |
| request_id parsed on errors | ✅ Yes — ErrorState shows request_id |
| No fake notification data | ✅ None found |
| No hardcoded unread count | ✅ Dynamic from `getUnreadCount()` |
| Loading state | ✅ Skeleton shown while loading |
| Empty state | ✅ "No notifications yet" EmptyState |
| Error state shows request_id | ✅ Yes |

## Backend Endpoint (assumed from sprint 27)

Backend route: `/v1/admin/notifications` (GET) — paginated in-app notification feed.
Backend route: `/v1/admin/notifications/unread-count` (GET)
Backend route: `/v1/admin/notifications/{id}/read` (POST)
Backend route: `/v1/admin/notifications/mark-all-read` (POST)

All backed by sprint 27 notification tables and `sprint27AdminApi` wiring.
