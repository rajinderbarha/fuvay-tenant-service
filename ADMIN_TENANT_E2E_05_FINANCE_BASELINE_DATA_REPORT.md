# ADMIN-TENANT-E2E-05 — Finance Baseline Data Report (real psql evidence)

All queries run directly via `psql.exe` against `serviceos` DB, tenant `34b427a7-b2be-496c-b826-6d51bb181248` (Demo AC Services).

## tenant_billing (authoritative for Home Services usage credits)
```
credit_balance = 3958.00
security_deposit_paid = t, security_deposit_amount = 5000.00
subscription_status = active
```

## usage_credit_ledger (2 real rows)
```
id=cb2ab499... event_type=completed_job_deduction credit_delta=-21.00 balance_before=4000.00 balance_after=3979.00 request_id=req_18c6f14edce6 created_at=2026-07-09 19:50:12
id=bf339134... event_type=completed_job_deduction credit_delta=-21.00 balance_before=3979.00 balance_after=3958.00 request_id=req_f499727faf4f created_at=2026-07-09 22:55:57
```
- Balance arithmetic verified correct: 4000 → 3979 → 3958, matches `tenant_billing.credit_balance` exactly (3958.00).
- No duplicate deduction: `SELECT job_id, event_type, count(*) ... HAVING count(*)>1` returns **0 rows**.
- Schema has a DB-level guard: `UNIQUE (job_id, event_type) WHERE event_type='completed_job_deduction'` (`uq_ucl_job_event_once`) — exactly-once is enforced at the constraint level, not just by application logic.
- Deduction rule confirmed: 21 credits per completed AC Repair / Split AC / LG job (matches E2E-04 finding).

## Freshest completed job (JOB-20260710-000001, service_jobs table)
- `id=688b0206-5621-44ec-9de0-71dd822aad46`, `status=completed`, `tenant_id=34b427a7...`, completed 2026-07-10 06:53.
- **No usage_credit_ledger row exists yet for this job** — confirmed still true (carried-forward gap from E2E-04, the deduction-posting mechanism hasn't fired for this specific job in this dev session). Both older ledger rows reference different (superseded) job IDs.

## Separate, disconnected `tenant_wallets` system (real, distinct table)
```
tenant_wallets: credit_balance=0.0000, lifetime_purchased=1100.0000, lifetime_consumed=1100.0000, low_balance_threshold=NULL
```
This is a **different table** than `tenant_billing`/`usage_credit_ledger`, read by `platform_commerce`/`finance_hub`/`invoice_payment`/`field_ops` engines (real job-closing/commission-deduction gating logic lives here per grep of `field_ops/billing_service.py` and `field_ops/service.py`: "Tenant wallet has insufficient credits to deduct commission/close this job"). For this tenant it shows **0.00**, i.e. a materially different number than the 3958.00 shown on `/admin/finance/usage-credits`. This is a genuine architecture split, not a data-entry error — flagged in full under the API Contract and Forbidden Label reports.

## Verdict: baseline data real, verified via psql, arithmetic correct, no duplicates.
