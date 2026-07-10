# ADMIN-TENANT-E2E-06 — Browser Evidence Report

## No screenshots this pass

No browser automation tool was available (see
`ADMIN_TENANT_E2E_06_BROWSER_E2E_REPORT.md`), so no screenshots exist.
In place of screenshots, the evidence below is real `curl` output
against the real running backend (localhost:8000) using a real admin
JWT (`admin@serviceos.in`), for each route this ticket asks about.

| Route | Action | API call | Result | Errors/request_id |
|---|---|---|---|---|
| `/admin/notifications` | Load | `GET /v1/admin/notifications` | `200`, `{"items":[],"total":0}` | `req_f5d758ec2838` |
| `/admin/notifications` (bell badge) | Load unread count | `GET /v1/admin/notifications/unread-count` | `200`, `{"unread_count":0}` | — |
| `/admin/notification-templates` | Load | `GET /v1/admin/notifications/templates` | `200`, 156 real templates | — |
| `/admin/notification-templates` | Summary | `GET /v1/admin/notifications/templates/summary` | `200`, real aggregate | `req_7f730ffbe0e6` |
| `/admin/notification-outbox` | Load | `GET /v1/admin/notification-outbox?limit=5` | `200`, `{"items":[],"total":0}` | `req_4ae9fc189f61` |
| `/admin/audit-logs` | Load | `GET /v1/admin/audit-logs?limit=5` | `200`, real audit rows | — |
| `/admin/reports` | Load | `GET /v1/admin/reports` | **First attempt: `500 INTERNAL_ERROR`** (`req_c4d606f40e7d`) → fixed (migration 131) → `200`, 6 real report definitions | — |
| `/admin/reports` | Run report | `POST /v1/admin/reports/run` `{"report_key":"admin_platform_summary_report","export_format":"csv"}` | `200`, real CSV content, `row_count: 3` | `req_ab5b53475d4c` |

## Verdict
Real, live evidence gathered via API-level verification for every
real route this ticket covers, including one genuine bug (Reports 500)
caught and fixed with a request_id trail. No visual/screenshot evidence
exists — documented as a tooling gap, not silently omitted.
