# E2E-12 API Contract Final Scan

**Date:** 2026-07-10  
**Method:** Static analysis — scan for raw fetch() calls in page components

---

## Scope

Verify that page components use the central API client (`apiFetch` / typed API modules) rather than bypassing it with raw `fetch()`.

---

## Scan Pattern

```
fetch(
```
(`.refetch()` calls from React Query `useQuery` hooks are excluded — those are expected)

---

## Findings

### Admin Portal

| File | Line | Code | Classification |
|------|------|------|----------------|
| `app/admin/customers/page.tsx` | 304 | `fetch(\`${API_BASE}${path}\`, { headers: ... })` | **ACCEPTED** — CSV blob download. `apiFetch` returns JSON; file download requires raw fetch with `.blob()`. |
| `app/admin/bookings/page.tsx` | 364 | `fetch(\`${API_BASE}${path}\`, { headers: ... })` | **ACCEPTED** — CSV blob download. Same reason. |

### Tenant Portal

| File | Line | Code | Classification |
|------|------|------|----------------|
| `app/login/page.tsx` | 49 | `fetch(\`.../v1/tenant/dashboard/runtime\`, { headers: ... })` | **ACCEPTED** — Post-login bootstrap to populate localStorage with vertical/plan/health. Non-critical (try/catch). Not a page data fetch; it's a one-time session setup call. |

---

## Summary

| Portal | Raw fetch() count | Accepted | Violations |
|--------|------------------|----------|------------|
| Admin | 2 | 2 | 0 |
| Tenant | 1 | 1 | 0 |

**Result: PASS — 0 violations**

All raw `fetch()` calls are in accepted use cases (blob download, post-login bootstrap). No page data fetches bypass the central API client.
