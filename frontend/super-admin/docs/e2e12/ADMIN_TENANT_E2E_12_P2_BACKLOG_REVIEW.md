# E2E-12 P2 Backlog Review

**Date:** 2026-07-10

---

## Known P2 Items from Previous Sprints

### From E2E-08

| ID | Item | File / Location | Status |
|----|------|-----------------|--------|
| P2-01 | Profile category field hardcoded "Air Conditioner Services" | Tenant portal profile page — category display | Open — not fixed in this sprint |
| P2-02 | 5-area limit hardcoded in service areas UI | Tenant portal service areas page | Open — backend limit not surfaced dynamically |
| P2-03 | Holiday exceptions frontend-only (not persisted to backend) | Tenant portal availability page | Open — holiday exception form exists but submission is UI-only |
| P2-04 | Service area permissions hardcoded to `true` | Tenant portal service areas page | Open — permission check not fetched from backend |

### From E2E-10

| ID | Item | File / Location | Status |
|----|------|-----------------|--------|
| P2-05 | Frontend role guards incomplete for tenant job mutations | /(tenant)/jobs/[id] | Open — staff can see some tenant-only mutation buttons |
| P2-06 | No cross-link from job detail Usage Credit Deduction to ledger | /(tenant)/jobs/[id] | Open — deduction shown but no deep link to /(tenant)/finance/usage-credit-ledger |
| P2-07 | Hardcoded hex colors in job detail/execution pages | /(tenant)/service-jobs/[id] and /execution | Open — should use CSS vars |

### From E2E-06C

| ID | Item | File / Location | Status |
|----|------|-----------------|--------|
| P2-08 | Related entity deep links not wired | Admin notification pages — audit log entries | Open — clicking an entity reference does not navigate to the entity detail page |
| P2-09 | Legacy /admin/notification-templates vs /admin/notifications/templates confusion | Both routes have page files | Open — legacy route retained for backward compat; should eventually redirect |

### New from E2E-12 Scan

| ID | Item | File / Location | Status |
|----|------|-----------------|--------|
| P2-10 | "Tenant Payouts" column header in admin settings matches forbidden "Tenant Payout" pattern | app/admin/settings/page.tsx:391 | Open — borderline; backend config field display. Rename to "Payout Config" in future cleanup |

---

## Summary

| Count | Severity | Action |
|-------|----------|--------|
| 10 | P2 | Tracked for future sprint |
| 0 | P0/P1 | None outstanding from this analysis |

No P2 items are blocking the current certification. All are deferred to future cleanup sprints.
