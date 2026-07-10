# ADMIN-TENANT-E2E-08: Remaining Blockers

**Date:** 2026-07-10

## TypeScript Compilation
```
npx tsc --noEmit
```
**Result: 0 errors, 0 warnings** (no output = clean)

## P0 Blockers (Must Fix Before Release)
NONE

## P1 Blockers (Should Fix Before Release)
NONE

## P2 Non-Blocking Issues

| # | Page | Issue | Impact |
|---|------|-------|--------|
| 1 | profile/page.tsx | Category field hardcoded "Air Conditioner Services" (lines ~739, ~1083) | Shows wrong category for non-AC tenants |
| 2 | profile/page.tsx | Address tab hardcodes "/ 5 areas used" limit | May be wrong for tenants with different plan limits |
| 3 | tenant/setup/availability/page.tsx | Holiday exceptions are local-state only — no backend persistence | Holidays reset on page reload |
| 4 | provider/service-areas/page.tsx | canCreate/canUpdate/canDelete hardcoded `true` | Granular permissions not yet returned by auth/me |
| 5 | All setup pages | No aria-label on icon-only buttons (accessibility) | Screen-reader users may have difficulty |

## Known Architectural Gaps (Not Bugs)
- Holiday backend endpoint not implemented — UI warns user explicitly
- Granular permissions (`tenant.business_profile.update` etc.) not returned by `/v1/auth/me` — frontend defaults to allow
- Breaks within a day must be configured as two separate time ranges (no break field)

## Certification Status
**READY** — 0 P0/P1 blockers. 5 P2 non-blocking items documented above.
