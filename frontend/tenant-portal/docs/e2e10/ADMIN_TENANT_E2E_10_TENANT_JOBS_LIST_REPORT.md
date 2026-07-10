# ADMIN-TENANT-E2E-10 — Tenant Jobs List Report

## Static Analysis Only

## File: `app/(tenant)/jobs/page.tsx`

## Features Verified
- **Data source**: `jobsApi.list({ limit:"50" })` → `GET /v1/jobs` — live API, no mock data
- **SLA alerts**: `jobsApi.slaAlerts()` → `GET /v1/jobs/sla-alerts` — shown as warning/danger banners above the table
- **Filters**: Status filter (select) + search (job number / customer name / service type) — client-side filter on the fetched page
- **Loading state**: Skeleton rows while loading
- **Empty state**: "No jobs match your filters" message
- **Error state**: Danger banner with error text
- **Row click**: Navigates to `/jobs/{id}`
- **SLA link**: ViewBtn on alert navigates to `/jobs/{job_id}`
- **Status badge**: `<JobStatusBadge>` component
- **Value formatting**: Indian locale `₹{n.toLocaleString("en-IN")}`
- **Columns**: Job, Customer, Service, Status, Staff, Time, Value

## SLA Display
- Alerts rendered above the table with severity-aware color (danger/warning)
- Minutes overdue shown on each alert
- Alert count badge in the header actions

## Design Tokens
- Uses CSS variables throughout: `var(--surface-sunken)`, `var(--border)`, `var(--text-primary)`, `var(--danger-bg)`, `var(--warning-bg)`, `var(--success-text)`, `var(--text-link)`, `var(--text-tertiary)`, etc.
- No hardcoded hex colors

## Issues Found
- None

## Status: PASS
