# Admin Tenant Detail — Finance Labels Report

## Approved Labels (in use on the page)

| Label | Location |
|-------|----------|
| Usage Credit Balance | KPI card 1, hero mini card |
| Credits Deducted Lifetime | KPI card 2 |
| Security Deposit Held | KPI card 3 |
| Usage Credit Health | Health Signals (mapped from `credit_wallet_health`) |
| Add Usage Credits | Hero action button, More menu, modal title |
| Usage credits are internal platform credits | Modal confirmation copy |
| Not cash, not withdrawable | Modal copy |
| Completed job deductions | Modal copy |

## Forbidden Labels — Scan Result

The following are confirmed **absent** from the page:

| Forbidden Label | Present? |
|----------------|---------|
| Wallet Balance | ❌ Not found |
| Cash Wallet | ❌ Not found |
| Withdraw | ❌ Not found |
| Withdrawable Balance | ❌ Not found |
| Tenant Payout | ❌ Not found |
| Provider Earnings Wallet | ❌ Not found |
| Escrow | ❌ Not found |
| Platform Collected Service Payment | ❌ Not found |
| Provider Cash Balance | ❌ Not found |
| Credit Wallet Health | ❌ Not found (replaced by "Usage Credit Health") |

## Business Rules Enforced

- Customer pays provider directly on-site — no platform collection
- Usage credits are internal platform credits only
- Usage credits are not cash and not withdrawable
- Security Deposit Held is separate from usage credits
- Completed Job Deduction is a credit deduction, not a cash payout
- No payout/withdraw UI anywhere on the page
