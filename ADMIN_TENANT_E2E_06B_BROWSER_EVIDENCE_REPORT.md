# ADMIN-TENANT-E2E-06B — Browser Evidence Report

All evidence is real, captured from actual system-Chrome runs this pass,
saved under `frontend/e2e-admin-tenant/evidence/e2e06b/`.

| Route | Action | API call observed | Data shown | Screenshot | Errors/request_id | UI issues | Result |
|---|---|---|---|---|---|---|---|
| topbar bell | Click | `GET /v1/admin/notifications/unread-count` → 200 | badge count 0, no fake dot | `bell-before-click.png`, `bell-after-click-notifications.png` | none | Navigates to Templates page, not a real notification feed (see finding) | PASS (mechanics), FLAGGED (destination content) |
| `/admin/notifications` | Load | `unread-count`, `templates/summary`, `templates?` → all 200 | 158 templates, real KPI cards | `notification-center.png` | none | Page is actually Templates, not Notification Center | FLAGGED |
| `/admin/notification-templates` | Load | `notification-templates` → 200 | real template rows | `templates.png`, `templates-detail.png` | none | thinner duplicate of the above | PASS |
| `/admin/notification-outbox` | Load | `notification-outbox?limit=50&offset=0` → 200 | honest empty state | `outbox.png`, `outbox-detail.png` | none | none | PASS |
| `/admin/audit-logs` | Load | `audit-logs?page=1&page_size=25...` → 200 | real audit records | `audit-logs.png`, `audit-log-detail.png` | none | none | PASS |
| `/admin/reports` | Load | `reports?` → 200 (was 500 pre-E2E-06) | 6 real report definitions | `reports-list.png`, `reports.png` | none | none | PASS |
| `/admin/reports` | Run report | `POST /v1/admin/reports/run` → 200 | `"admin_platform_summary_report: 3 rows (no export requested)"` | `reports-run-result.png` | none | none | PASS |
| `/admin/reports` | CSV export | `POST /v1/admin/reports/run` (export_format=csv) → 200 | real download, 62 bytes, `metric,value / tenants,1 / active_tenants,1` | `csv-export-evidence.png`, file `admin_platform_summary_report_2026-07-10.csv` | none | none | PASS |

## Verdict
Real, literal browser evidence for every route this ticket covers,
including one genuine architectural finding (Notification Center content
mismatch) surfaced only by actually clicking through in a browser —
something the prior curl-only pass (E2E-06) could not have caught.
