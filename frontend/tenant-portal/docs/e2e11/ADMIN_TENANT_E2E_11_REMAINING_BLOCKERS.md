# E2E-11 Remaining Blockers

## P0 Blockers (must fix before certification)
NONE

## P1 Blockers (should fix before release)
NONE

## P2 Non-Blocking Notes
- `finance/security-deposit/page.tsx` uses `tenantSetupApi.getWallet()` which returns the provider wallet shape. The `security_deposit` sub-key is extracted from it. This works but the endpoint is slightly repurposed. No bug, low risk.
- `finance/security-deposit/page.tsx` has display fallbacks: `required_amount ?? 5000`, `currency ?? "INR"`. These are reasonable defaults for display only.

## Status: NO BLOCKERS
