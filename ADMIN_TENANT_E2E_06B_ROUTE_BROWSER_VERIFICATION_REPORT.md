# ADMIN-TENANT-E2E-06B — Route Browser Verification Report

Real routes in this codebase (ticket's assumed paths adjusted to actual
ones, documented in E2E-06 already):

| Ticket route | Actual route | Status | API calls | Sidebar | Header | NaN/undefined |
|---|---|---|---|---|---|---|
| `/admin/notifications` | same | 200 | `unread-count`, `templates/summary`, `templates/audit-logs`, `templates?`, `effective-menu` — all 200 | present | present | none |
| `/admin/notifications/templates` | `/admin/notification-templates` | 200 | `unread-count`, dashboard set, `notification-templates` — all 200 | present | present | none |
| `/admin/notifications/outbox` | `/admin/notification-outbox` | 200 | `unread-count`, dashboard set, `notification-outbox?limit=50&offset=0` — all 200 | present | present | none |
| `/admin/notifications/delivery-logs` | same as outbox (one combined page, no separate delivery-logs route) | n/a | — | — | — | documented gap, not a broken link (not linked anywhere as a separate route) |
| `/admin/audit` | `/admin/audit-logs` | 200 | `audit-logs?page=1&page_size=25&sort_by=created_at&sort_direction=desc` — 200 | present, nav-audit-logs fontWeight=600 (active state correct) | present | none |
| `/admin/reports` | same | 200 | `reports?` — 200, no 500 (previously 500, now fixed) | present | present | none |

## Optional routes re-checked
`/admin/notifications/settings`, `/admin/audit/platform`,
`/admin/audit/tenant`, `/admin/audit/access-transparency`,
`/admin/reports/home-services`, `/admin/reports/finance`,
`/admin/reports/tenants` — **none of these exist**, and none are linked
from the sidebar/topbar (confirmed via `lib/nav-config.ts` — only
`notifications`, `audit-logs`, `reports` top-level entries exist, no
sub-route children for these). Per Part 11's own classification rules,
these are **non-blocking documented gaps** (not linked anywhere), not
broken navigation.

## Real finding this pass (see Part 5/notification-center report)
`/admin/notifications` — the route both the sidebar "Notifications" item
and the topbar bell point to — actually renders a **Notification
Templates management page** (component `NotificationTemplatesPage`,
554 lines), not a feed of real sent/received notifications. This is a
genuine routing/semantic mismatch, not a 404/500 — documented in detail
in `ADMIN_TENANT_E2E_06B_NOTIFICATION_CENTER_BROWSER_REPORT.md`.

## Verdict
All real routes load with real API calls, no crashes, no NaN/undefined,
correct active sidebar state where checked. One semantic mismatch found
(see above) — not a route-level 404/500 failure.
