# ADMIN-TENANT-E2E-06C: Notification Route Conflict Investigation

## Status: RESOLVED — No Active Conflict

## Investigation

### Current Route Structure (static analysis)

| Route | File | Page Type |
|---|---|---|
| `/admin/notifications` | `app/admin/notifications/page.tsx` | ✅ Real Notification Center (feed) |
| `/admin/notifications/templates` | `app/admin/notifications/templates/page.tsx` | ✅ Notification Templates management |
| `/admin/notification-templates` | `app/admin/notification-templates/page.tsx` | Legacy template page (sprint27 events) |
| `/admin/notification-outbox` | `app/admin/notification-outbox/page.tsx` (assumed) | Outbox/delivery logs |

### E2E-06B Blocker Status

The E2E-06B sprint reported: `/admin/notifications` opens a Templates management page, not a real feed.

**Current state (after investigation):** `/admin/notifications/page.tsx` is a real Notification Center that uses `sprint27AdminApi.listNotifications()`, `sprint27AdminApi.getUnreadCount()`, `sprint27AdminApi.markRead()`, and `sprint27AdminApi.markAllRead()`. The Templates management is correctly separated at `/admin/notifications/templates/`.

**Conclusion:** The route conflict was either fixed between E2E-06B and now, or the E2E-06B report was based on a prior state. The current codebase has the correct separation.

### Bell Target

`AdminLayout.tsx` line 548: `<a href="/admin/notifications" ...>` — bell correctly targets Notification Center.

### Sidebar Links

`AdminLayout.tsx` line 112: `{ id: "notifications", href: "/admin/notifications", label: "Notifications", icon: <Bell ...> }` — sidebar correctly targets Notification Center.

### API Endpoints Used

- Notification feed: `sprint27AdminApi.listNotifications({ read_status, limit })`
- Unread count: `sprint27AdminApi.getUnreadCount()`
- Mark read: `sprint27AdminApi.markRead(id)`
- Mark all read: `sprint27AdminApi.markAllRead()`
- Templates: `notifTemplateAdminApi.*` (separate API module)

## Finding

**No active route conflict.** Both pages exist and are correctly separated.

**One TypeScript bug found and fixed:** `app/admin/notifications/templates/page.tsx` used `../../../` imports (wrong depth) — corrected to `../../../../` imports.
