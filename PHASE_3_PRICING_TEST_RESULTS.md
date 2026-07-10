# Phase 3 — Pricing & Rules Test Results

## Backend test command

```bash
pytest tests/ -q
```

## Backend result

**8001 passed, 37 failed, 1 skipped** (out of 8039 collected).

All 37 failures are the exact same pre-existing, unrelated baseline
confirmed in every prior sprint this session (catalog/pricing-form/
brand-flow frontend-assertion tests predating a concurrent process's
nav-config refactor). **0 new failures.**

New tests added this sprint: `tests/test_phase3_pricing_rules_certification.py`
— **18/18 passed**, covering:
- `completed_job_deduction_credits` field + negative-value rejection
- Resolver returns deduction credits + payment_collection_mode
- Bargain rule model/migration existence
- Bargain evaluation endpoint + below-floor rejection logic
- Bargain floor validation (vs base_price and min_price)
- Provider override model/migration existence
- Provider override min/max enforcement
- Provider override approval workflow endpoints
- Provider override tenant-scoping
- No forbidden cash/wallet/payout labels anywhere in pricing code
- All 22 new `PRICING_*` permission constants exist
- All new endpoints require permission
- All new mutations are audited
- Sidebar "Pricing & Rules" rename + no duplicates
- Both new frontend pages wire real evaluation/approval UI

## Frontend TypeScript result

```bash
npx tsc --noEmit
```

**0 errors** across the entire `frontend/super-admin` build, including the
2 new pages (`/admin/pricing/bargain-rules`, `/admin/pricing/provider-overrides`)
and the `lib/api.ts` additions.

## Frontend lint result

```bash
npx next lint
```

**Broken, pre-existing** (Next.js 16 removed the `next lint` subcommand —
documented in every prior sprint, not caused by this sprint).

## Frontend test result

No JS test runner configured in this repo (consistent finding across every
sprint this session). Python source-inspection tests via `pytest` remain
the established convention.

## Live end-to-end verification (against running backend + real Postgres)

All performed directly via `curl`, not simulated:
- Pricing resolver baseline: `POST /v1/admin/pricing-rules/preview` → `final_customer_estimate: 800.0`, `completed_job_deduction_credits: 21`, `payment_collection_mode: "customer_pays_provider_directly"`.
- Bargain rule created, linked to the AC Repair pricing rule.
- Bargain evaluation: ₹500 rejected, ₹649 rejected, ₹650 accepted, ₹700 accepted, ₹1300 accepted (see bug-fix report for the "no ceiling" design note).
- Provider override: ₹500 rejected (below min 600), ₹900 created + approved, ₹1300 rejected (above max 1200).
- Audit log entries confirmed for `bargain_rule` and `provider_pricing_override` mutations in `master_data_audit_log`.
- Both new frontend pages confirmed 200 (compiled and served) via the Next.js dev server.
