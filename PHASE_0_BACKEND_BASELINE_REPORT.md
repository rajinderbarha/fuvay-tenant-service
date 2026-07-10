# Phase 0 — Backend Baseline Report

All 18 Part 6 checks performed live against the running backend
(`uvicorn app.main:app`) and real Postgres — not simulated.

| # | Check | Result |
|---|---|---|
| 1 | Super Admin user exists | ✅ `admin@serviceos.in`, role `super_admin`, confirmed via `GET /v1/auth/me` |
| 2 | Roles and permissions exist | ✅ code-based (`app/core/permissions.py`); 6 real roles, `super_admin` short-circuits all permission checks |
| 3 | Platform settings match required values | ✅ all 11 exact matches — see table below |
| 4 | Required engines exist and are enabled | ✅ 39 total, 0 disabled, 0 degraded (`GET /v1/admin/engines/summary`) |
| 5 | Home Services vertical is enabled | ✅ `is_enabled: true` (`GET /v1/admin/verticals`) |
| 6 | Navigation config has no duplicates | ✅ static-verified, `AdminLayout.tsx` — no dup Brands/Pricing items |
| 7 | Home Services catalog exists | ✅ category + 3 service groups + master services all present |
| 8 | AC Repair mapping is correct | ✅ Split AC, Window AC, LG, Samsung, Voltas, Gas Refill, Emergency Visit, AC Not Cooling all mapped |
| 9 | Pricing rule exists | ✅ `rule_code=ac_repair_split_ac_lg_ldh_141001`, `base_price=800` |
| 10 | Pricing resolver returns ₹800 | ✅ **live**: `POST /v1/admin/pricing-rules/preview` → `final_customer_estimate: 800.0` |
| 11 | Starter Home Services package exists | ✅ `included_credit_amount=1000`, `security_deposit_amount=5000` |
| 12 | Demo tenant exists and is not bookable | ✅ `verification_status=pending`, `status=pending_setup` |
| 13 | Demo customer exists | ✅ `customer@serviceos.in` + Ludhiana address |
| 14 | Demo technician exists | ✅ `staff@serviceos.in`, `tenant_id` linked to Demo AC Services |
| 15 | No bookings exist | ✅ `bookings` table count = 0 |
| 16 | No jobs exist | ✅ `jobs` table count = 0 |
| 17 | No usage credit deductions exist | ✅ `wallet_transactions` count = 0 |
| 18 | No customer service credits exist | ✅ `customer_service_credits` count = 0 |

## Platform settings — exact values (Home Services finance model)

```
customer_pays_provider_directly              -> True
payment_collection_enabled                    -> False
tenant_payouts_enabled                        -> False
provider_usage_credits_enabled                -> True
usage_credit_is_cash_wallet                   -> False
usage_credit_is_withdrawable                  -> False
security_deposit_enabled                      -> True
customer_service_credits_enabled              -> True
tenant_package_starts_after_approval          -> True
tenant_included_credits_added_after_approval  -> True
job_credit_deduction_trigger                  -> job_completed
```

**Hard gate PASS**: Home Services finance settings match exactly.

## Pricing resolver — raw response (evidence)

```json
{
  "master_service_id": "a96e625a-60e1-46c0-bde4-ccbb88da50a2",
  "service_name": "AC Repair",
  "job_type": "repair",
  "pricing_model": "fixed",
  "tier": {"name": "Mid", "match_level": "zipcode"},
  "selected_type": "Split AC",
  "selected_brand": "LG",
  "matched_rule_name": "AC Repair - Split AC - LG - Ludhiana 141001",
  "base_price": 800.0,
  "final_customer_estimate": 800.0,
  "message": "Fixed price ₹800."
}
```

## Forbidden-label check

Grepped `service_pricing_rules`, `service_packages`, `tenant_package_assignments`
API responses and the settings/finance payloads produced this sprint — no
occurrences of `Cash Wallet`, `Withdraw`, `Withdrawable Balance`, `Tenant
Payout`, `Provider Earnings Wallet`, or `Escrow`.
