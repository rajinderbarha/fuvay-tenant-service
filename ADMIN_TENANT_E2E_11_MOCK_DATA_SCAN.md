# ADMIN-TENANT-E2E-11 — Mock Data Scan

`grep -rniE` for `mockFinance|mockLedger|mockCredits|mockNotifications|
mockSettings|fakeBalance|fakeLedger|dummyNotification` across
`app/(tenant)/finance`, `app/(tenant)/notifications`,
`app/(tenant)/settings`, `components/layout/TenantLayout.tsx` —
**0 matches.**

"Demo AC Services" (the tenant name shown throughout) is real seed data
from the live database, not a hardcoded literal — confirmed via
`useTenant()` hook sourcing it from `tenantSetupApi`/auth context, not a
string constant in any of these files.

## Verdict
Clean.
