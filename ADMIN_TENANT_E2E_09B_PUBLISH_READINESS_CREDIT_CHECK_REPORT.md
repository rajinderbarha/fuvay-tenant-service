# ADMIN-TENANT-E2E-09B — Publish Readiness Credit Check Report

Confirmed via code read: `_evaluate_provider_bookability` (the real readiness/bookability
computation behind `GET /v1/provider/status`) DOES include a credit-balance check as one of
its critical bookability gates:

```
SELECT credit_balance, security_deposit_paid, security_deposit_amount FROM tenant_billing WHERE tenant_id=:tid
...
if credit_balance > 0: passed.append("usage_credits_available")
else: bookability_blockers.append({code: "INSUFFICIENT_USAGE_CREDITS", ...})
```

This uses `tenant_billing` exclusively — no `tenant_wallets` reference anywhere in this
function. Live call (`GET /v1/provider/status` as Owner) confirms
`"usage_credits_available"`-class blockers are absent for Demo AC Services (balance 3937.00,
`bookability_blockers: []`).

Verdict: implemented and correct — uses `tenant_billing`, not `tenant_wallets`. No gap to
document here.
