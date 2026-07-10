# ADMIN-TENANT-E2E-06 — Notification Bell Report

## Bug confirmed and fixed

`frontend/super-admin/components/layout/AdminLayout.tsx`'s topbar bell
(`TopNav` component) previously:
1. Was a `<button>` with **no `onClick` handler at all** — clicking it did nothing.
2. Rendered a **hardcoded, always-visible red dot** regardless of real
   unread state — a fake indicator, present even with 0 unread
   notifications (confirmed live: `GET /v1/admin/notifications/unread-count`
   returns `0` for the real admin user, yet the old dot always showed).

## Fix
- Changed the bell to a real `<a href="/admin/notifications">` — clicking
  it now navigates to the real Notification Center.
- Added a `sprint27AdminApi.getUnreadCount()` fetch on mount (a real,
  live-verified endpoint, `GET /v1/admin/notifications/unread-count`,
  confirmed returning `{"unread_count": 0}` for the real admin user).
- The badge now only renders when `unreadCount > 0`, and shows the real
  count (capped display at "99+"). Added `aria-label` reflecting the
  real count for accessibility.

## Live-verified
`GET /v1/admin/notifications/unread-count` → `200`,
`{"unread_count": 0}` — confirms the endpoint the fix now calls is real
and working.

## Not verified
No browser session was available this pass to click the bell and watch
navigation actually occur (see `ADMIN_TENANT_E2E_06_BROWSER_E2E_REPORT.md`
for the tooling gap) — verified via source-level fix + TypeScript
compile + direct API call to the exact endpoint the new code calls, not
an actual click-through.

## Verdict
Notification bell: **fixed** — real onClick (navigation), real unread
count, no fake indicator. Not `NOT_READY_ADMIN_NOTIFICATION_BELL_FAILED`.
