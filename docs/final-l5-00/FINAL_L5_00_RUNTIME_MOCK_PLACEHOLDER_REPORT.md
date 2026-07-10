# FINAL-L5-00 — Runtime Mock / Placeholder Data Report (Parts 14-15)

Scope: `frontend/super-admin`, `frontend/tenant-portal`, `frontend/customer-app` production
source (`app/`, `components/`, `lib/`), excluding `__tests__`, `*.test.*`, `*.spec.*`, `e2e/`.

## Method

Grepped for: `mockData|fakeData|dummyData|sampleData|placeholderData`, `setTimeout` (fake-latency
check), `Math.random` (fake-value check), hardcoded `const mock*/fake*/dummy*/sample*` arrays,
inline `// mock|fake|dummy|hardcoded|TODO mock` comments, and `MOCK_MODE`/`USE_MOCK` flags.

Before flagging, read prior scans to avoid re-reporting resolved issues, notably
`ADMIN_TENANT_E2E_11_MOCK_DATA_SCAN.md`, `ADMIN_TENANT_E2E_11_FORBIDDEN_LABEL_SCAN.md`. Several
findings below turned out to be **comments documenting past fixes**, not live mock code — these
are recorded as ALLOWED/resolved for completeness, not re-flagged as new bugs.

## Findings

### 1. `frontend/tenant-portal/lib/api.ts:1451` + `frontend/tenant-portal/app/login/page.tsx:8,21-30`
- **Application:** tenant-portal
- **Route/page:** `/login` (tenant provider login)
- **Snippet:**
  ```ts
  // lib/api.ts:1450-1451
  // ── Mock flag ────────────────────────────────────────────────
  export const MOCK_MODE = process.env.NEXT_PUBLIC_USE_MOCK === "true";

  // app/login/page.tsx:21-30
  if (MOCK_MODE) {
    localStorage.setItem("serviceos_tenant_token",   "mock_tenant_token");
    localStorage.setItem("serviceos_tenant_id",      "t1");
    localStorage.setItem("serviceos_tenant_name",    "Rahul AC Services");
    localStorage.setItem("serviceos_tenant_vertical","home_services");
    localStorage.setItem("serviceos_tenant_plan",    "growth");
    localStorage.setItem("serviceos_tenant_health",  "74");
    localStorage.setItem("serviceos_user_id",        "u1");
    window.location.href = "/dashboard";
    return;
  }
  ```
- **Classification: NOT_ALLOWED** — a real login page ships a hardcoded fake-tenant bypass path
  gated only by a client-readable `NEXT_PUBLIC_*` env flag. `.env.local` and `.env.local.example`
  both currently set `NEXT_PUBLIC_USE_MOCK=false`, so the path is inert in the shipped config —
  but the code is compiled into the production bundle and would silently fabricate a full session
  ("Rahul AC Services", health 74, plan "growth", tenant id "t1") for anyone who flips that one
  build-time env var, with no server-side check. No equivalent flag/path exists in
  `super-admin/lib/api.ts` or `customer-app` — this is isolated to tenant-portal. Recommend
  removing the mock branch entirely rather than relying on env discipline.

### 2. `frontend/super-admin/lib/api.ts:2605-2607` (comment only, no live code)
- **Application:** super-admin
- **Snippet:** `// ── Mock data for offline / development mode ── / // PROVEN: All mock data matches the real API response shape exactly. / // Remove NEXT_PUBLIC_USE_MOCK=true in production.`
- **Classification: ALLOWED** — this is a stale section-header comment; no `MOCK_MODE` constant,
  no `NEXT_PUBLIC_USE_MOCK` reference, and no mock data actually exists below it in this file
  (verified: `grep MOCK_MODE|USE_MOCK` on super-admin returns 0 hits). The types declared under it
  (`JobHistory`, `StaffMember`, etc.) are real interfaces used by live API methods. Comment is
  misleading/dead but there is no runtime mock behavior to fix. Safe to leave or clean up the
  comment only.

### 3. `frontend/super-admin/components/layout/AdminLayout.tsx:482-486` (resolved, comment documents the fix)
- **Application:** super-admin
- **Route/page:** global top-nav notification bell (all admin pages)
- **Snippet:** comment: `"the notification bell previously had no onClick and a hardcoded, always-visible red dot (fake "unread" indicator regardless of real state). Now fetches the real unread count..."` followed by live code: `sprint27AdminApi.getUnreadCount().then(r => setUnreadCount(r.unread_count))`.
- **Classification: ALLOWED** — already fixed in a prior sprint (ADMIN-TENANT-E2E-06); the bell
  now renders real backend data. No action needed.

### 4. `frontend/tenant-portal/app/(tenant)/finance/package/page.tsx:22-28` (resolved, comment documents the fix)
- **Application:** tenant-portal
- **Route/page:** `/finance/package`
- **Snippet:** comment explains the balance card previously called the stale `tenantSetupApi.getWallet()` endpoint which "showed a hardcoded-looking 0"; it was rewired to `usageCreditsApi.getBalance()` (the live HS9/HS9B endpoint).
- **Classification: ALLOWED** — already fixed (E2E-11 sprint); current code calls the real
  balance endpoint. No action needed.

## Not found (checked, clean)

- `mockData|fakeData|dummyData|sampleData|placeholderData` identifiers: 0 genuine hits in any of
  the 3 apps (`sampleData` hits in super-admin `lib/api.ts` are a real request-body parameter name
  for `notificationTemplatesApi.renderPreview`/`testSend`, not fake data).
- `setTimeout` calls: exhaustively reviewed across all 3 apps — every instance is a toast
  auto-dismiss timer (2000-4000ms) or a search-input debounce (`EnterpriseFilterBar.tsx`,
  `EnterpriseDataGrid.tsx`, 350ms). None simulate API latency or gate a mock response.
- `Math.random()` calls: all 8 instances (super-admin: 6, tenant-portal: 2) generate client-side
  toast/list `id` keys (`Math.random().toString(36).slice(2)`), not fake business data.
- Hardcoded `const mock*/fake*/dummy*/sample*/placeholder*` arrays assigned to component state:
  0 hits in any app.
- customer-app: 0 hits across every pattern searched — `lib/api/` (`client.ts`, `auth.ts`,
  `customer-home-services.ts`) and all `app/`/`components/` files are clean.
- No hardcoded fake KPI/dashboard numbers found in `super-admin/app/admin/dashboard`,
  `tenant-portal/app/(tenant)/dashboard`, or `tenant-portal/app/staff/dashboard` — all values in
  these pages are sourced from `useApi`/API-client calls, not literal arrays.

## Note (unrelated, spotted incidentally)

`frontend/super-admin/app/admin/intelligence/page.tsx.tmp.13128.892018edb538` is a stray editor
temp file (near-duplicate of `page.tsx`) sitting inside the Next.js `app/` route tree. It is not
matched by Next.js routing (wrong extension) so it does not affect runtime, but it is untracked
clutter worth deleting in a cleanup pass. Not a mock-data issue — flagged only for awareness, no
action taken (read-only investigation).

## Summary

- **NOT_ALLOWED:** 1 (tenant-portal `MOCK_MODE` login bypass — items 1 above)
- **ALLOWED (resolved-in-prior-sprint or false positive):** 3
- No mock/fake/placeholder data issues found in customer-app.
