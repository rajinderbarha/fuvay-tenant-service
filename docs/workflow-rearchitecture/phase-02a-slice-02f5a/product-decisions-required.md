# Product Decisions Required — Slice 2F-5A

## 1. Should `admin_finance` be granted `FINANCE_PAYOUTS_*`?
Today `FINANCE_PAYOUTS_READ/APPROVE/REJECT/PROCESS/COMPLETE` are granted to
no role except via `super_admin`'s `P.ALL` wildcard. Payout approval and
processing represent real money leaving the platform to providers — the
highest-stakes capability found in either module. Whether the finance
operations team (`admin_finance`) or only `super_admin` should be able to
execute these actions is a genuine authority/business decision, not a
technical one. **Recommendation for the next slice**: resolve this
decision first, then verify the existing guard composition (which already
correctly checks these permissions) works as intended once granted — no
code change to the guard itself should be needed.

## 2. Should `admin_finance` be granted `FINANCE_CLAIMS_*`?
Same reasoning — warranty claim assignment/approval/rejection/settlement
currently reachable only by `super_admin`. Settlement in particular likely
triggers a real payment or credit.

## 3. Should `admin_finance` (or any role) be granted `PACKAGES_*`?
Package catalog definition, activation, and purchase-recording are
currently super_admin-only. Lower real-money stakes than payouts (catalog
definition is not itself a transaction), but still a genuine question of
who should manage the sellable package catalog.

## 4. Should the "legacy" credit-wallet top-up idempotency pattern be hardened?
`admin_topup_wallet` only enforces idempotency if the caller supplies an
explicit key; otherwise it silently generates a fresh one every call
(defeating duplicate-request protection). Whether this needs a stricter,
mandatory-key contract is a product/API-design decision, not resolved
this slice (see `financial-integrity-findings.md`).

## 5. Should `finance_hub`'s internal tenant/object ownership mechanisms be independently re-verified?
This slice confirmed WHO can call these endpoints (permission-bundle
analysis) but did not trace `finance_hub`'s internal service methods'
tenant-scoping/ownership enforcement line-by-line (out of narrow scope).
Recommended as part of the next slice's verification work.
