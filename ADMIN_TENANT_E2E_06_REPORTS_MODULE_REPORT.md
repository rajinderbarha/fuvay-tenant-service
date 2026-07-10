# ADMIN-TENANT-E2E-06 — Reports Module Report

## Route: `/admin/reports` (real, 141-line page)

## Bug found and fixed
`GET /v1/admin/reports` returned a **live 500 `INTERNAL_ERROR`** —
`analytics_report_runs` was missing the `updated_at` column its ORM
model requires (the same systemic gap found and fixed repeatedly
throughout this session — migrations 122-129). This meant **the entire
Reports page could never load past its first render** for any admin.
Fixed via migration 131. Live-verified after the fix: `200`, 6 real
report definitions returned (`admin_platform_summary_report`,
`admin_category_performance_report`, `admin_provider_performance_report`,
`admin_financial_report`, `admin_commission_report`, `admin_wallet_report`),
each with real `allowed_filters` and `export_formats: ["csv", "xlsx"]`.

## Live-verified report execution
`POST /v1/admin/reports/run`
`{"report_key": "admin_platform_summary_report", "export_format": "csv"}`
→ `200`, real data: `row_count: 3`, real platform metrics
(`tenants: 1`, `active_tenants: 1`, `total_bookings: 11` — matching this
session's real dev-DB state), real `csv_content` returned inline
(`"metric,value\r\ntenants,1\r\n..."`) for the frontend to blob-download.

## Note on report names (not a violation, documented)
Two of the 6 real report definitions are named "Commission Report" and
"Wallet Report" — these are pre-existing, generic, platform-wide
financial reports from an earlier, unrelated sprint (not built this
session, not Home-Services-specific usage-credit language). Left
untouched per this ticket's own "out of scope: wallet/payout system"
instruction — flagged in the forbidden-label scan for visibility, not
treated as a bug to fix.

## Verdict
Reports Module: **was completely broken (live 500), now fixed and
live-verified** including real report execution and real CSV export
content. Not `NOT_READY_ADMIN_REPORTS_ROUTE_FAILED`.
