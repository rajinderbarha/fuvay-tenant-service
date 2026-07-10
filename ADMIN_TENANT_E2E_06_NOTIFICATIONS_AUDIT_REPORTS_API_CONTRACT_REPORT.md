# ADMIN-TENANT-E2E-06 — API Contract Report

## Real API modules (this codebase's actual structure, not the ticket's suggested file layout)
All notification/audit/report API calls live in the single centralized
`frontend/super-admin/lib/api.ts` (this codebase's established
convention throughout every sprint this session — not split into
per-domain files like `admin-notifications.ts`), specifically:
- `sprint27AdminApi` — `listNotifications`, `getUnreadCount`, `markRead`,
  `markAllRead`, `listEvents`, `listOutbox`, `getOutbox`, `retryOutbox`.
- `notifTemplateAdminApi` — `listTemplates`, `getSummary`, `getTemplate`,
  `createTemplate`, `updateTemplate`, `activate`, `deactivate`, and more.
- `adminAnalyticsApi` — `listReports`, `runReport`, `getReportRun`.
- Audit: a direct `apiFetch` call to `/v1/admin/audit-logs` inside
  `audit-logs/page.tsx` (not a separate named API object).

## Rules check
1. Central API client used — **yes**, `apiFetch()` wrapper, consistent
   with every other page in this codebase.
2. Auth token included — **yes**, `apiFetch` attaches the Bearer token
   automatically (same helper verified throughout this session).
3. `request_id` parsed — **yes**, `apiFetch` throws `ServiceOSError`
   with `requestId` on failure, the same pattern used everywhere else.
4. No direct `fetch()` in page components — confirmed for
   notifications/templates/outbox/reports; not individually re-verified
   for `audit-logs/page.tsx`.
5. No fake runtime data — confirmed via full-file grep on all 5 pages
   (see `ADMIN_TENANT_E2E_06_MOCK_DATA_SCAN.md`).
6. Secrets not rendered — no provider secrets/API keys found rendered
   anywhere in the 5 pages' source.

## Verdict
API contract: **consistent with this codebase's established
centralized-client pattern**, real data throughout.
