# ADMIN-TENANT-E2E-06 — Export/Download Report

## Real, live-verified

`POST /v1/admin/reports/run` with `export_format: "csv"` returns real
`csv_content` inline in the response
(`"metric,value\r\ntenants,1\r\nactive_tenants,1\r\ntotal_bookings,11\r\n"`)
— live-verified this pass. The frontend page (`reports/page.tsx`)
converts this to a `Blob`, creates an object URL, and triggers a real
browser download named `${reportKey}_${date}.csv` — confirmed via
source read, not a browser click-through (no browser tool available).

`export_formats: ["csv", "xlsx"]` is present on every report
definition — xlsx export was not live-tested this pass (only csv was
exercised).

## Verdict
Export/Download: **real backend support, live-verified for CSV.** XLSX
not separately tested. No browser-level download-completion
verification performed (tooling gap).
