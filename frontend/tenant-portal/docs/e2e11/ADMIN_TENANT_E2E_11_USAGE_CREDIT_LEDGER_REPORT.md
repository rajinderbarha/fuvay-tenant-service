# E2E-11 Usage Credit Ledger Report

## Page: `/finance/usage-credit-ledger`
File: `app/(tenant)/finance/usage-credit-ledger/page.tsx`

## API
- `usageCreditsApi.getBalance()` — real HS9/HS9B endpoint
- `usageCreditsApi.getLedger()` — real HS9/HS9B endpoint

## KPI Cards
1. "Usage Credit Balance" — from `balance.data.usage_credit_balance` ✅
2. "Credits Deducted" — sum of `completed_job_deduction` deltas ✅
3. "Completed Jobs" — count of `completed_job_deduction` entries ✅
4. "Low Credit Status" — derived from `balance.data.low_credit` ✅

## Table Columns
Date | Job ID | Event Type | Credit Change | Balance Before | Balance After | Reason | Request ID

## Event Type Display
- `completed_job_deduction` renders as **"Completed Job Deduction"** ✅
- Other types pass through as-is

## Arithmetic
- `balance_before` + `credit_delta` = `balance_after` per row (rendered from API data)
- `Credits Deducted` = sum of absolute values of negative `credit_delta` entries ✅

## Forbidden Labels: NONE FOUND

## Status: PASS
