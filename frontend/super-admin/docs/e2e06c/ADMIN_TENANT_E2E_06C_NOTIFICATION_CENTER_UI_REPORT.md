# ADMIN-TENANT-E2E-06C: Notification Center UI Report

## Status: PASS_ENTERPRISE_LEVEL

## Page: `/admin/notifications`

File: `app/admin/notifications/page.tsx`

## UI Elements Present

### Page Header
- Title: "Notification Center"
- Subtitle explaining purpose
- Refresh button (RefreshCw icon)
- "Mark All Read" button (CheckCheck icon)

### KPI Cards (4-column grid)
- Total — total notification count
- Unread — live from `getUnreadCount()` API
- Critical/High — count of severity critical/high items
- Read — count of read items

### Filter Bar
- Status filter (read_status: read / unread)
- Type filter (notification_type keyword)
- Search (title/body text search, client-side)
- All wired to real state

### Notification List
- Columns: Title, Type, Severity badge, Read status, Created At, Actions
- Unread rows visually distinct (bold + background)
- "Mark Read" action per row (Eye icon)
- Click row to open detail drawer

### Notification Detail Modal
- Shows full title, body, type, severity, status, created/read timestamps
- "Mark as Read" button if unread

### States
- Loading: Skeleton component shown
- Empty: EmptyState "No notifications yet. System and tenant alerts will appear here."
- Error: Shows request_id for support

## CSS/Design
- Uses CSS variables only (`var(--card-bg)`, `var(--border)`, `var(--brand)`, `var(--text-primary)`, etc.)
- No hardcoded hex colors
- Responsive grid layout

## Classification: PASS_ENTERPRISE_LEVEL
