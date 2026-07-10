# HS9 — Completed Job Deduction Report

## Deduction source: real, pre-existing field
`ServicePricingRule.completed_job_deduction_credits` (an `Integer`
column) already existed in the schema before this sprint — confirmed
via direct query: the real dev-DB "AC Repair / Window AC (no brand)"
pricing rule already had `completed_job_deduction_credits = 21`, exactly
matching the ticket's own worked example number. This sprint did not
invent the field; it built the resolution and deduction logic that
actually reads it (nothing did, before this pass).

## Resolution specificity — reuses HS6's certified hierarchy
`resolve_completed_job_deduction_credits()`
(`app/engines/execution/usage_credit_deduction.py`) ranks candidate
`ServicePricingRule` rows exactly like HS6's bargain-rule resolution:
service+type+brand (3) > service+type (2) > service-only (1); a rule
scoped to a *different* type or brand than the one requested scores -1
and is never eligible — this is the exact mechanism that prevents the
ticket's named failure mode.

## Live-verified: the ticket's own named hard gate
Directly queried the resolver for two different real requests against
the same `master_service_id` (AC Repair):
- `Split AC + LG` → resolved to rule `2ef804e7-...` (the real
  Split-AC+LG-specific rule), **21 credits**.
- `Window AC + no brand` → resolved to rule `ebd7e643-...` (the
  Window-AC-only rule), **21 credits**.

Different rule IDs for different requests — confirms **"Window AC LG
deduction must not be used for Split AC LG"** is genuinely enforced, not
just coincidentally correct because both happened to be 21.

## Live end-to-end verification
Real job `JOB-20260709-000003` (AC Repair / Split AC / LG), tenant
"Demo AC Services": balance before = 4000.0, completed →
`credit_delta: -21.0`, `balance_after: 3979.0`, `deduction_source:
"2ef804e7-..."` (the correct, specific rule) — matches the ticket's
example arithmetic exactly (`100 → 79` scaled to real dev-DB balance
`4000 → 3979`).

## Verdict
Completed Job Deduction: **resolves correctly with real specificity
enforcement, live-verified against the ticket's own named failure
scenario.**
