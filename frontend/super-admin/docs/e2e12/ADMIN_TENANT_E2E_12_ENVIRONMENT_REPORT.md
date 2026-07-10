# E2E-12 Environment Report

**Date:** 2026-07-10  
**Method:** Static analysis (no live browser session)

---

## Portal Paths

| Portal | Path |
|--------|------|
| Admin (super-admin) | `g:\serviceos\frontend\super-admin` |
| Tenant (tenant-portal) | `g:\serviceos\frontend\tenant-portal` |
| Backend | `g:\serviceos\backend` |

---

## TypeScript Compilation

| Portal | Exit Code | Errors |
|--------|-----------|--------|
| super-admin | 0 | None |
| tenant-portal | 0 | None |

Both portals compile clean with `npx tsc --noEmit`.

---

## Framework / Runtime

| Item | Value |
|------|-------|
| Framework | Next.js (App Router) |
| Language | TypeScript |
| OS | Windows 10 Pro 10.0.19045 |
| Date verified | 2026-07-10 |

---

## Notes

- No live dev servers were started during this analysis pass.
- Browser-based smoke testing was not performed in this sprint.
- All findings are based on static source code analysis.
