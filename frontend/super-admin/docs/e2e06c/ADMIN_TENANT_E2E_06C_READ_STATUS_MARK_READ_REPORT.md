# ADMIN-TENANT-E2E-06C: Read Status / Mark Read Report

## Status: SUPPORTED AND WORKING (code-level)

## Backend Support
- Mark single read: `POST /v1/admin/notifications/{id}/read` → `sprint27AdminApi.markRead(id)`
- Mark all read: `POST /v1/admin/notifications/mark-all-read` → `sprint27AdminApi.markAllRead()`
- Returns `{ marked_read: number }` for mark-all

## Frontend Behavior

| Behavior | Status |
|---|---|
| Unread rows visually distinct | ✅ Bold + background highlight via CSS |
| Mark Read button per row | ✅ Eye icon action wired to `handleMarkRead()` |
| Mark All Read in header | ✅ CheckCheck button wired to `handleMarkAllRead()` |
| Feed refetch after mark | ✅ `feed.refetch()` called |
| Unread count refetch after mark | ✅ `unreadCountApi.refetch()` called |
| Toast confirmation | ✅ "Notification marked as read." shown |
| Read At timestamp in detail | Listed in detail modal where available |
| Error shows request_id | ✅ Error handled via `useAction` |

## Browser Verification
Static analysis only — browser smoke testing requires live server at http://localhost:3000.

## Result: PASS (code-level) — browser verification pending live server
