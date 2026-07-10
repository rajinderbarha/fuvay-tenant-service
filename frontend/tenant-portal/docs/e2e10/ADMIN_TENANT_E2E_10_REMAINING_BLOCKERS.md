# ADMIN-TENANT-E2E-10 — Remaining Blockers

## P0 Blockers (Release-Critical)
**None.**

## P1 Blockers (Must Fix Before Certification)
**None.**

## P2 Issues (Style / UX Debt — Non-Blocking)

### 1. Hardcoded Hex in service-jobs/[id]/page.tsx
- Colors `#111`, `#888`, `#333`, `#fef2f2`, `#b91c1c`, `#f9fafb`, `#e5e7eb`, `#6366f1` used in UI
- Should use `var(--text-primary)`, `var(--text-tertiary)`, `var(--danger-bg)`, etc.
- Does not affect functionality or TypeScript compilation
- Pre-existing issue

### 2. Hardcoded Hex in service-jobs/[id]/execution/page.tsx
- Extensive use of hardcoded hex throughout the page
- Colors: `#16a34a`, `#dc2626`, `#6b7280`, `#374151`, `#e5e7eb`, `#9ca3af`, `#f9fafb`, `#f0fdf4`, `#86efac`, `#fef2f2`, `#fca5a5`, `#6366f1`
- Does not affect functionality or TypeScript compilation
- Pre-existing issue

### 3. No Cross-Link from Job Detail Credit Card to Ledger
- The "Usage Credit Deduction" card in `jobs/[id]/page.tsx` does not link to `/finance/usage-credit-ledger`
- Users must navigate to Finance section manually
- UX improvement, not a bug

### 4. Frontend RBAC — No Read-Only Role Guards
- Job action buttons visible to all tenant users regardless of role
- Backend must enforce; no frontend suppression
- Acceptable if tenant user role system is not implemented

## P3 Issues (Low Priority)

### 5. Legacy Explicit TenantLayout in jobs/ Pages
- `jobs/page.tsx` and `jobs/[id]/page.tsx` include `<TenantLayout>` explicitly
- `(tenant)/layout.tsx` also wraps all pages in `TenantLayout`
- Results in double-wrap (pre-Sprint-34K pattern)
- Current behavior: outer shell layout applies first; inner layout re-renders correctly
- Not causing visible errors or TypeScript failures

## TypeScript Status
**0 errors** — confirmed by `npx tsc --noEmit` exit code 0.

## Summary
| Severity | Count |
|----------|-------|
| P0 | 0 |
| P1 | 0 |
| P2 | 4 |
| P3 | 1 |

## Certification Verdict
`READY_ADMIN_TENANT_E2E_10_TENANT_JOBS_TECHNICIAN_COMPLETION_CERTIFIED`
