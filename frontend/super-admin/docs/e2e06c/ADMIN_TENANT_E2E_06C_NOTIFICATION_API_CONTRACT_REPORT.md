# ADMIN-TENANT-E2E-06C: Notification API Contract Report

## Status: PASS

## API Modules

### `sprint27AdminApi` (in `lib/api.ts`)
Handles the real notification feed:
- `listNotifications({ read_status?, limit? })` → paginated feed
- `getUnreadCount()` → `{ unread_count: number }`
- `markRead(id)` → mark single notification read
- `markAllRead()` → `{ marked_read: number }`

### `notifTemplateAdminApi` (in `lib/api.ts`)
Handles notification templates:
- `listTemplates(params)` → paginated template list
- `sendTest(id, payload)` → send test notification
- `getHistory(id)` → delivery history
- `disable(id)` / `enable(id)` → toggle template
- `copy(id)` → duplicate template

## Contract Rules Compliance

| Rule | Status |
|---|---|
| Central API client used | ✅ Both use `apiFetch` |
| Auth token included | ✅ Via `apiFetch` auth header |
| request_id parsed on errors | ✅ Error states show request_id |
| Notification Center uses feed endpoint | ✅ `listNotifications` |
| Templates page uses templates endpoint | ✅ `notifTemplateAdminApi` |
| Bell count uses unread-count endpoint | ✅ `getUnreadCount()` |
| No direct `fetch()` in page components | ✅ None found |
| No fake runtime notification data | ✅ None found |
| Mutations refetch relevant data | ✅ `feed.refetch()` + `unreadCountApi.refetch()` after mark-read |

## Result: PASS
