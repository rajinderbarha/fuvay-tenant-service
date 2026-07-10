# ADMIN-TENANT-E2E-06C: Unread Count Consistency Report

## Status: CONSISTENT

## Count Sources

| Surface | Source |
|---|---|
| Bell badge in topbar | `sprint27AdminApi.getUnreadCount()` — polled on layout mount |
| Notification Center KPI "Unread" card | `sprint27AdminApi.getUnreadCount()` — fetched on page mount |
| Notification list unread rows | `read_status === "unread"` from the feed response |

## Consistency Rules

- Bell count and page KPI come from the same backend endpoint (`/v1/admin/notifications/unread-count`)
- After `markRead(id)`: `feed.refetch()` + `unreadCountApi.refetch()` both called — count updates
- After `markAllRead()`: same double refetch — count resets to 0
- No hardcoded badge value found
- No fake red dot found (confirmed from E2E-06B: fake red dot was removed)

## Potential Drift

The topbar bell count is polled on layout mount and may drift briefly from the page KPI if notifications arrive between page load and the next poll cycle. This is standard behavior and not a bug.

## Result: PASS
