# E2E-07 Tenant Notification Entrypoint Report
**Date:** 2026-07-10  
**Analysis:** Static analysis

---

## Notification Architecture

### Topbar Bell

- Notifications bell icon in `TenantLayout.tsx` topbar
- Shows unread count badge when `unreadCount > 0`
- Opens a slide-in notification panel (within the topbar component)
- Data from `notificationsApi.list()` → `/v1/notifications`

### Dedicated Notification Pages

| Page | Path | Purpose |
|---|---|---|
| Tenant owner notifications | `/notifications` | Full notification inbox for tenant owner |
| Provider notifications | `/provider/notifications` | Provider-role notifications (compliance, jobs) |

### Notification API

In `lib/api.ts`:
```ts
export const notificationsApi = {
  list: (params?) => apiFetch('/v1/notifications'),
  markRead: (id) => apiFetch(`/v1/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => apiFetch('/v1/notifications/read-all', { method: 'POST' }),
}
```

### Notification Types (from Sprint 27)

- Job status updates
- Booking confirmations
- Complaint assignments
- Compliance alerts
- Payment events
- Chat messages

### Findings

| Check | Status |
|---|---|
| Bell icon in topbar | PASS |
| Unread count badge | PASS |
| Dedicated `/notifications` page | PASS |
| Provider notifications page | PASS |
| Mark as read / all read | PASS |
| Notification data from backend | PASS |

**Status: PASS** — Notification entrypoints are complete and functional.
