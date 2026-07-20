# Per-Module Status Report

| Module | Set A | Set B included | Final protected | Denom. contribution | Held resolved | Status | Blocker |
|---|---|---|---|---|---|---|---|
| platform_commerce_deposit | 3 | 0 | 3 | 0 | — | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| pricing | 0 | 9 | 9 | +9 | 9 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| commerce (held) | 0 | 3 (1 excluded) | 3 | +3 | 4 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| payments | 0 | 1 | 1 | +1 | 1 | SECURITY_CLOSED_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED | amount-validation gap (no authoritative balance ledger exists) — authorization dimension closed, financial-integrity dimension open |
| subscriptions | 0 | 1 | 1 | +1 | 1 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |
| compliance | 0 | 2 | 2 | +2 | 2 | SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED | none |

**5 of 6 modules reached full `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED`.**
`payments` closed its authorization/tenant-trust dimension but carries an
honest, explicit `PRODUCT_POLICY_BLOCKED` status on the financial-
integrity dimension (client-supplied `amount` with no balance ledger to
validate against — see `known-limitations.md` and
`financial-domain-integrity-audit.csv`). This does not block the batch
from reaching `CRITICAL_AUTHORIZATION_BATCH_COMPLETE` because the route
IS canonically protected and IS included, per the frozen contract's
allowance for
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` as
a realistic per-module status.

Totals: 3 Set A routes closed (c=3), 16 Set B routes canonically added
and protected (a=h=16), all 17 Set B routes received a final disposition
(r=17).
