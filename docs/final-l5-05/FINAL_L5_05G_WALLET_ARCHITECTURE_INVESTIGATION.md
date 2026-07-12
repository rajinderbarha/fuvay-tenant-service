# FINAL-L5-05G — Tenant Wallet Investigation: Critical Finding, No Code Changes Made

## Summary

The FINAL-L5-05F sprint flagged `/admin/finance/wallets` and `/admin/provider-wallets` as
real, live, permission-gated backend surfaces built on `TenantWallet`/`tenant_wallets`,
and recommended a dedicated remediation sprint to either migrate this onto the
approved Usage Credit model or formally deprecate it. This sprint (FINAL-L5-05G)
performed that investigation. **It found the system is far larger, deeper, and more
load-bearing than the two orphaned admin pages suggested, and concluded that
attempting to decommission it in one session would risk breaking real, working,
revenue-critical functionality.** No backend code was changed this sprint.

## What was found

### 1. `tenant_wallets` / `wallet_transactions` have zero rows in the real database

```
tenant_wallets       -> 0 rows
wallet_transactions  -> 0 rows
tenant_billing       -> 1 row
usage_credit_ledger  -> 1 row
security_deposits    -> 2 rows
```

No tenant-by-tenant reconciliation or data migration is required — there is no
data to reconcile or migrate. This is the one part of the mission that is
genuinely simple and low-risk.

### 2. `TenantWallet`/`WalletTransaction` (`app/engines/platform_commerce/models.py`) is real, actively-wired, load-bearing infrastructure — not dead or purely-forbidden code

`app/engines/platform_commerce/ledger.py` implements a full, real, transactional
financial ledger with row-locking (`SELECT ... FOR UPDATE NOWAIT`):
`get_wallet_locked` (auto-creates a wallet row on first use), `credit_wallet`,
`debit_wallet`, `credit_deposit`, `debit_deposit`, `debit_customer_balance`,
`reconcile_wallet`.

These functions are called from **12 files across the codebase**, including
core, real, currently-working commerce flows:

| Consumer | Real capability that depends on `TenantWallet`/`WalletTransaction` |
|---|---|
| `app/engines/package_commerce/service.py` | Package purchases, credit balance display (`credit_wallet_balance`), refunds |
| `app/engines/invoice_payment/commission_service.py` | Commission debits/credits |
| `app/engines/invoice_payment/wallet_service.py` | `ProviderCreditWalletService` — backs `/v1/admin/provider-wallets` |
| `app/engines/field_ops/billing_service.py` | Legacy field-ops manual credit/debit adjustments |
| `app/engines/finance_hub/service.py` | Security Deposit credit/debit (`credit_deposit`/`debit_deposit` — **same shared ledger.py as wallets**), wallet directory read, package purchase wallet credit |
| `app/engines/tenant_engine/admin_service.py`, `admin_router.py`, `portal_router.py` | `credit_wallet_balance` displayed in tenant admin/portal views |
| `app/engines/tenant_engine/health.py`, `constants.py` | `credit_wallet_health` is a real tenant health-score signal (15% weight) |
| `app/engines/customer_credits/service.py` | References wallet-adjacent manual-credit source tagging |
| `app/engines/platform_commerce/router.py` (mounted in `main.py`, real `/v1/commerce/*` routes) | `POST /tenants/{id}/wallet/credit` (manual credit), `POST .../wallet/deduct` (**job-linked wallet deduction — `engine_deduct_wallet`**), `GET .../wallet/projection` (burn-rate projection) |
| `app/engines/settings_engine/admin_router.py` | Platform settings reference `credit_wallet_only` vs `security_deposit_plus_credit_wallet` as a real, configurable per-tenant billing mode |

**Critically: `finance_hub/service.py`'s Security Deposit credit/debit calls
(`credit_deposit`/`debit_deposit`) use the exact same `ledger.py` module as the
wallet functions.** Security Deposits are a certified, approved, real feature
(2 real rows in the database, actively used in this engagement's finance
pages). This means `platform_commerce/ledger.py` cannot be disabled or removed
wholesale without also breaking Security Deposits — the two concepts share
infrastructure at the code level even though they are separate concepts at the
product level.

### 3. `TxnType` classification suggests this is a tenant-pays-platform billing ledger, not a customer/provider cash-out wallet

```python
class TxnType:
    PURCHASE, COMMISSION, MANUAL_DEDUCT, MANUAL_CREDIT, REFUND,
    WARRANTY_DRAW, RESERVATION_CREATE/RELEASE/FORFEIT/EXPIRED/CONFIRM
```

These transaction types describe tenants paying the platform for packages and
the platform deducting commission — money flowing **into** the platform, not
**out** to providers. This is a materially different concept from the
forbidden terminology's actual target (`Provider Earnings Wallet`,
`Withdrawable Balance`, `Tenant Payout`, `Provider Cash Balance` — money
leaving the platform to a provider). The admin-facing UI labels ("Wallet
Directory", "Available Balance", "Reserved Balance") are a real terminology
violation and should not remain in any *reachable* Admin UI, but the
underlying transaction semantics are not necessarily the forbidden "cash-out"
model this mission's rules were written to eliminate.

### 4. Two independent, parallel tenant-credit systems exist in the codebase

| | `tenant_billing.credit_balance` + `usage_credit_ledger` | `TenantWallet.credit_balance` + `wallet_transactions` |
|---|---|---|
| Model file | `app/engines/tenant_engine/models.py` | `app/engines/platform_commerce/models.py` |
| Real DB rows | 1 | 0 |
| Used by | Home Services job completion (`Completed Job Deduction`, FINAL-L5-05C/D/E) | Package purchases, commissions, field-ops billing, tenant health scoring |
| Foreign key / sync to the other table | **None found** | **None found** |

There is no evidence these two systems are connected, derived from one
another, or that one supersedes the other in code. Both are real, wired, and
callable today.

## Why no code was changed this sprint

Given:
- 12 real backend files depend on `credit_wallet`/`debit_wallet`/`TenantWallet`, including live package-purchase and commission flows this engagement has not independently verified end-to-end this sprint,
- Security Deposits (a certified, working, real feature) share the same `ledger.py` module,
- a third, separately-mounted router (`/v1/commerce/*`) exposes a job-linked wallet deduction endpoint (`engine_deduct_wallet`) whose relationship to the certified `Completed Job Deduction` flow was not established,
- rule 1 ("do not delete `tenant_wallets` data before full classification") and rule 16 ("do not break Completed Job Deduction integrity") from this mission's own non-negotiable rules,

attempting to disable, redirect, or decommission any part of this system in
the remaining time budget would risk a real, hard-to-reverse regression to
package purchases, commission processing, or Security Deposits — functionality
this engagement has previously certified as working. That risk is not
justified by fixing two currently-unreachable admin pages, whose actual
production risk (a real admin discovering and using them) is already low
since they carry no navigation entry point (FINAL-L5-05F).

## What is still true and unchanged

- `/admin/finance/wallets` and `/admin/provider-wallets` remain **unlinked from
  any navigation** (verified in FINAL-L5-05F, re-confirmed this sprint) — this
  remains the correct, protective state.
- No new code path was added, removed, or modified this sprint.
- The full backend regression suite was not required to re-run since no code
  changed; existing FINAL-L5-05E/F baseline (9005 passed, 0 failed) is
  unaffected.

## Recommended next steps (not attempted this sprint)

1. A dedicated architecture-reconciliation sprint with real time allocated to
   trace every one of the 12 consumer files end-to-end (not just grep-level
   inventory), confirm whether package purchases/commissions are exercised in
   any real environment, and get an explicit product/finance decision on
   whether `TenantWallet` should be (a) renamed and kept as the real
   package/commission billing ledger, (b) merged into `tenant_billing`, or
   (c) genuinely retired in favor of migrating package/commission billing onto
   the `tenant_billing`/`usage_credit_ledger` model.
2. Independent of that larger decision, a low-risk, narrowly-scoped follow-up
   *can* safely rename the admin-facing display terminology only ("Wallet
   Directory" → e.g. "Tenant Billing Ledger (Package/Commission)",  "Available
   Balance" → "Package Credit Balance") without touching any transactional
   logic, closing the forbidden-terminology violation in the UI layer while
   the deeper architecture question is resolved separately.
3. Confirm whether `POST /v1/commerce/tenants/{id}/wallet/deduct`
   (`engine_deduct_wallet`) and the certified `Completed Job Deduction` flow
   (`app/engines/execution/usage_credit_deduction.py`) are meant to be the
   same concept, two concepts for two different verticals, or a genuine
   duplicate — this was not resolved this sprint and is a real open question.
